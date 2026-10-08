"""Recommendation use cases (recommendation_spec §2.2, §2.4-2.5, §3-4; AC-02, AC-04; admin_versioning §2.4).

The band comes from risk_profile_service, the template from the ACTIVE published version (pinned on the stored row),
the goal from the caller's own goals, and `as_of_date` from the injected clock. All allocation maths is in
domain.allocation_template_policy. Reads return stored rows, never recomputed. Logs carry IDs and the rule code only.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.domain.allocation.templates import AllocationSumError
from app.domain.allocation_template_policy import recommend
from app.domain.bands import RiskBand
from app.domain.goal import GoalSnapshot
from app.domain.goal_horizon_policy import horizon_months, primary_goal
from app.domain.policy import RecommendationSource
from app.domain.template_version_validator import PolicyInvalid, parse_template_version
from app.repositories import (
    audit_repository,
    customer_repository,
    goal_repository,
    policy_version_repository,
    recommendation_repository,
)
from app.repositories.models import Goal, TemplateVersion
from app.repositories.recommendation_repository import RecommendationRecord
from app.services import risk_profile_service
from app.services.customer_resolver import user_id_for
from app.services.errors import conflict, not_found, unprocessable

logger = logging.getLogger(__name__)

ACTION_CREATED = "RECOMMENDATION_CREATED"
ENTITY_TYPE = "recommendation"


@dataclass(frozen=True)
class RecommendationView:
    id: str
    source: RecommendationSource
    risk_band: RiskBand
    template_version_no: int
    goal_id: str | None
    horizon_months: int | None
    horizon_rule: str
    as_of_date: date
    allocation: tuple[tuple[str, Decimal], ...]
    total_pct: Decimal
    created_at: datetime


def _view(record: RecommendationRecord) -> RecommendationView:
    return RecommendationView(
        id=record.id,
        source=record.source,
        risk_band=record.risk_band,
        template_version_no=record.template_version_no,
        goal_id=record.goal_id,
        horizon_months=record.horizon_months,
        horizon_rule=record.horizon_rule,
        as_of_date=record.as_of_date,
        allocation=record.allocation,
        total_pct=sum((pct for _, pct in record.allocation), Decimal("0")),
        created_at=record.created_at,
    )


def _snapshot(goal: Goal) -> GoalSnapshot:
    return GoalSnapshot(goal.id, goal.priority, goal.target_date, goal.target_amount, goal.created_at)


def _goal(session: Session, customer_id: str, goal_id: str | None) -> GoalSnapshot | None:
    """The named goal (must be the caller's, else 404) or the primary goal; None when the customer has none."""
    if goal_id is not None:
        goal = goal_repository.get_for_customer(session, customer_id, goal_id)
        if goal is None:
            raise not_found("GOAL_NOT_FOUND", "Goal not found.")
        return _snapshot(goal)
    return primary_goal([_snapshot(g) for g in goal_repository.list_for_customer(session, customer_id)])


def _active_template(session: Session) -> TemplateVersion:
    row = policy_version_repository.active_published(session, TemplateVersion)
    if row is None:  # the v1 seed guarantees a published template; its absence is a deployment fault
        raise RuntimeError("no published template version")
    return row


def create_recommendation(
    session: Session, clock: Clock, principal: Principal, customer_id: str, goal_id: str | None
) -> RecommendationView:
    """Compute and store a SYSTEM recommendation with its allocation rows and audit row in one transaction."""
    band = risk_profile_service.effective_band(session, customer_id)
    if band is None:
        raise conflict("RISK_PROFILE_REQUIRED", "Complete the risk questionnaire first.")
    goal = _goal(session, customer_id, goal_id)
    as_of = clock.today()
    months = None if goal is None else horizon_months(as_of, goal.target_date)
    template = _active_template(session)
    asset_classes = customer_repository.active_asset_class_codes(session)
    try:
        result = recommend(band.band, parse_template_version(template.definition, asset_classes), months, asset_classes)
    except PolicyInvalid as exc:
        raise unprocessable("TEMPLATE_INVALID", str(exc), {"violations": exc.violations}) from exc
    except AllocationSumError as exc:
        raise unprocessable("ALLOCATION_SUM_INVALID", str(exc)) from exc
    created_by = user_id_for(session, principal)
    if created_by is None:  # customer_id_for already resolved this principal to a user-backed customer
        raise RuntimeError("customer principal without a user row")
    created_at = clock.now()
    stored = recommendation_repository.add(
        session,
        customer_id=customer_id,
        source=RecommendationSource.SYSTEM,
        risk_band=band.band,
        risk_band_source_id=band.source_id,
        template_version_id=template.id,
        goal_id=None if goal is None else goal.id,
        horizon_months=months,
        horizon_rule=result.horizon_rule,
        as_of_date=as_of,
        created_by=created_by,
        created_at=created_at,
        allocation=result.allocation,
    )
    audit_repository.insert_audit_event(
        session,
        actor_user_id=created_by,
        actor_role=principal.role.value,
        action=ACTION_CREATED,
        entity_type=ENTITY_TYPE,
        entity_id=stored.id,
        details={"template_version_no": template.version_no, "horizon_rule": result.horizon_rule},
    )
    session.commit()
    logger.info(
        "recommendation created",
        extra={"customer_id": customer_id, "entity_id": stored.id, "outcome": result.horizon_rule},
    )
    return RecommendationView(
        id=stored.id,
        source=RecommendationSource.SYSTEM,
        risk_band=band.band,
        template_version_no=template.version_no,
        goal_id=stored.goal_id,
        horizon_months=months,
        horizon_rule=result.horizon_rule,
        as_of_date=as_of,
        allocation=result.allocation,
        total_pct=result.total,
        created_at=created_at,
    )


def latest_for(session: Session, customer_id: str) -> RecommendationView | None:
    """The customer's newest STORED recommendation (pinned template version), or None."""
    record = recommendation_repository.latest_for_customer(session, customer_id)
    return None if record is None else _view(record)


def list_for(session: Session, customer_id: str) -> list[RecommendationView]:
    """The customer's stored recommendations, newest first."""
    return [_view(r) for r in recommendation_repository.list_for_customer(session, customer_id)]
