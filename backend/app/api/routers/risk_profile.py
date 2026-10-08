"""Risk profile — questionnaire, assessments, effective band (risk_profile_spec §4, AC-01). CUSTOMER only.

The customer is always resolved from the token (NFR-04); no route takes a customer_id.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentClock, CurrentCustomerId, CustomerPrincipal, DbSession, require_role
from app.api.routers import API_V1
from app.api.schemas.risk_profile import (
    AssessmentIn,
    AssessmentOut,
    HistoryEntryOut,
    NoRiskProfileOut,
    OptionOut,
    QuestionnaireOut,
    QuestionOut,
    RiskProfileOut,
)
from app.core.security import Role
from app.domain.risk_band_rules import Answer
from app.services import risk_profile_service

router = APIRouter(
    prefix=f"{API_V1}/risk-profile",
    tags=["risk-profile"],
    dependencies=[Depends(require_role(Role.CUSTOMER))],
)


@router.get("/questionnaire", response_model=QuestionnaireOut)
def get_questionnaire(session: DbSession) -> QuestionnaireOut:
    q = risk_profile_service.questionnaire(session)
    questions = [
        QuestionOut(
            code=x.code,
            prompt=x.prompt,
            order=x.order,
            options=[OptionOut(code=o.code, label=o.label) for o in x.options],
        )
        for x in q.questions
    ]
    return QuestionnaireOut(policy_version_id=q.policy_version_id, version_no=q.version_no, questions=questions)


@router.post("/assessments", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def submit_assessment(
    body: AssessmentIn,
    session: DbSession,
    clock: CurrentClock,
    principal: CustomerPrincipal,
    customer_id: CurrentCustomerId,
) -> AssessmentOut:
    answers = [Answer(a.question_code, a.option_code) for a in body.answers]
    r = risk_profile_service.submit_assessment(session, clock, principal, customer_id, body.policy_version_id, answers)
    return AssessmentOut(
        assessment_id=r.assessment_id,
        total_score=r.total_score,
        computed_band=r.computed_band,
        assigned_band=r.assigned_band,
        applied_caps=list(r.applied_caps),
        policy_version_no=r.policy_version_no,
        created_at=r.created_at,
    )


@router.get("", response_model=RiskProfileOut | NoRiskProfileOut)
def get_risk_profile(session: DbSession, customer_id: CurrentCustomerId) -> RiskProfileOut | NoRiskProfileOut:
    effective = risk_profile_service.effective_band(session, customer_id)
    if effective is None:
        return NoRiskProfileOut()
    return RiskProfileOut(
        risk_band=effective.band,
        source=effective.source,
        source_id=effective.source_id,
        as_of=effective.as_of,
    )


@router.get("/history", response_model=list[HistoryEntryOut], response_model_exclude_none=True)
def get_history(session: DbSession, customer_id: CurrentCustomerId) -> list[HistoryEntryOut]:
    return [
        HistoryEntryOut(
            type=e.type,
            id=e.id,
            band=e.band,
            created_at=e.created_at,
            policy_version_no=e.policy_version_no,
            reason_code=e.reason_code,
        )
        for e in risk_profile_service.history(session, customer_id)
    ]
