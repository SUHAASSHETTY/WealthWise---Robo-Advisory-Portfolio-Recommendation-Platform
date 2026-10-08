"""Risk profile use cases (risk_profile_spec §2.4-2.5, §4; AC-01): questionnaire, submit, effective band, history.

Scoring lives in domain.risk_band_rules; every number comes from the active risk policy version. Logs carry IDs
only — never answers, scores or bands (NFR-03).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.domain import risk_band_rules
from app.domain.bands import RiskBand
from app.domain.risk_band_rules import (
    Answer,
    AssessmentEvent,
    AssessmentResult,
    AssessmentValidationError,
    OverrideEvent,
)
from app.domain.template_version_validator import RiskPolicyDefinition, parse_risk_policy
from app.repositories import (
    audit_repository,
    policy_version_repository,
    risk_assessment_repository,
    risk_override_repository,
)
from app.repositories.models import RiskPolicyVersion
from app.services.customer_resolver import user_id_for
from app.services.errors import conflict, unprocessable

logger = logging.getLogger(__name__)

ACTION_SUBMITTED = "RISK_ASSESSMENT_SUBMITTED"
ENTITY_TYPE = "risk_assessment"


@dataclass(frozen=True)
class OptionView:
    code: str
    label: str


@dataclass(frozen=True)
class QuestionView:
    """A question as shown to customers: no points (risk_profile_spec §4)."""

    code: str
    prompt: str
    order: int
    options: tuple[OptionView, ...]


@dataclass(frozen=True)
class Questionnaire:
    policy_version_id: str
    version_no: int
    questions: tuple[QuestionView, ...]


@dataclass(frozen=True)
class SubmittedAssessment:
    assessment_id: str
    total_score: int
    computed_band: RiskBand
    assigned_band: RiskBand
    applied_caps: tuple[str, ...]
    policy_version_no: int
    created_at: datetime


@dataclass(frozen=True)
class EffectiveBand:
    """The customer's effective risk band (§2.5); consumed by the recommendation service."""

    band: RiskBand
    source: str
    source_id: str
    as_of: datetime
    policy_version_no: int
    reason_code: str | None = None


@dataclass(frozen=True)
class HistoryEntry:
    type: str
    id: str
    band: RiskBand
    created_at: datetime
    policy_version_no: int | None = None
    reason_code: str | None = None


def _active_policy(session: Session) -> tuple[RiskPolicyVersion, RiskPolicyDefinition]:
    row = policy_version_repository.active_published(session, RiskPolicyVersion)
    if row is None:  # the v1 seed guarantees a published policy; its absence is a deployment fault
        raise RuntimeError("no published risk policy version")
    return row, parse_risk_policy(row.definition)


def questionnaire(session: Session) -> Questionnaire:
    """The active policy's questions and option labels, with points and thresholds stripped."""
    row, policy = _active_policy(session)
    questions = tuple(
        QuestionView(q.code, q.prompt, q.order, tuple(OptionView(o.code, o.label) for o in q.options))
        for q in policy.questions
    )
    return Questionnaire(row.id, row.version_no, questions)


def _reject(customer_id: str, code: str) -> None:
    logger.info("risk assessment rejected", extra={"customer_id": customer_id, "error_code": code})


def _score(
    policy: RiskPolicyDefinition, customer_id: str, answers: Sequence[Answer]
) -> tuple[AssessmentResult, list[Answer]]:
    """Domain scoring plus the stored answer order; §2.4 violations become 422 with the spec code."""
    try:
        return risk_band_rules.assess(policy, answers), risk_band_rules.sorted_by_question_order(policy, answers)
    except AssessmentValidationError as exc:
        _reject(customer_id, exc.code)
        raise unprocessable(exc.code, exc.message, {"question_code": exc.question_code}) from exc


def submit_assessment(
    session: Session,
    clock: Clock,
    principal: Principal,
    customer_id: str,
    policy_version_id: str,
    answers: Sequence[Answer],
) -> SubmittedAssessment:
    """Score against the active policy and store the assessment plus its audit row in one transaction."""
    row, policy = _active_policy(session)
    if policy_version_id != row.id:
        _reject(customer_id, "POLICY_VERSION_STALE")
        raise conflict("POLICY_VERSION_STALE", "The risk questionnaire has changed; fetch it again.")
    result, ordered = _score(policy, customer_id, answers)
    stored = risk_assessment_repository.add(
        session,
        customer_id=customer_id,
        risk_policy_version_id=row.id,
        answers=[{"question_code": a.question_code, "option_code": a.option_code} for a in ordered],
        total_score=result.total_score,
        computed_band=result.computed_band,
        assigned_band=result.assigned_band,
        applied_caps=list(result.applied_caps),
        created_at=clock.now(),
    )
    audit_repository.insert_audit_event(
        session,
        actor_user_id=user_id_for(session, principal),
        actor_role=principal.role.value,
        action=ACTION_SUBMITTED,
        entity_type=ENTITY_TYPE,
        entity_id=stored.id,
        details={"policy_version_no": row.version_no},
    )
    session.commit()
    logger.info("risk assessment submitted", extra={"customer_id": customer_id, "entity_id": stored.id})
    r = result
    return SubmittedAssessment(
        stored.id, r.total_score, r.computed_band, r.assigned_band, r.applied_caps, row.version_no, stored.created_at
    )


def _utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; every stored timestamp is UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def effective_band(session: Session, customer_id: str) -> EffectiveBand | None:
    """The customer's effective risk band (§2.5) across assessments and advisor overrides, or None."""
    records = risk_assessment_repository.list_for_customer(session, customer_id)
    overrides = risk_override_repository.list_for_customer(session, customer_id)

    assess_events = [AssessmentEvent(r.id, _utc(r.created_at), r.assigned_band) for r in records]
    override_events = [OverrideEvent(o.id, _utc(o.created_at), RiskBand(o.new_band)) for o in overrides]

    newest = risk_band_rules.effective_band(assess_events, override_events)
    if newest is None:
        return None

    reason_code = None
    if newest.source == risk_band_rules.SOURCE_ASSESSMENT:
        version_no = next(r.policy_version_no for r in records if r.id == newest.source_id)
    else:
        # Override inherits policy version of the latest assessment at or before override
        version_no = records[0].policy_version_no if records else 1
        override_match = next((o for o in overrides if o.id == newest.source_id), None)
        if override_match is not None:
            reason_code = override_match.reason_code

    return EffectiveBand(newest.band, newest.source, newest.source_id, newest.as_of, version_no, reason_code)


def history(session: Session, customer_id: str) -> list[HistoryEntry]:
    """The customer's assessments and advisor overrides, newest first (§4)."""
    assessments = risk_assessment_repository.list_for_customer(session, customer_id)
    overrides = risk_override_repository.list_for_customer(session, customer_id)

    entries: list[HistoryEntry] = []
    for a in assessments:
        entries.append(
            HistoryEntry(
                type=risk_band_rules.SOURCE_ASSESSMENT,
                id=a.id,
                band=a.assigned_band,
                created_at=_utc(a.created_at),
                policy_version_no=a.policy_version_no,
            )
        )
    for o in overrides:
        entries.append(
            HistoryEntry(
                type=risk_band_rules.SOURCE_ADVISOR_OVERRIDE,
                id=o.id,
                band=RiskBand(o.new_band),
                created_at=_utc(o.created_at),
                reason_code=o.reason_code,
            )
        )

    entries.sort(key=lambda e: (e.created_at, e.id), reverse=True)
    return entries
