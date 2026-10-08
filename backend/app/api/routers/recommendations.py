"""Recommendations (recommendation_spec §4, AC-02, AC-04). CUSTOMER only.

The customer is always resolved from the token (NFR-04); no route takes a customer_id. GET routes return stored rows.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentClock, CurrentCustomerId, CustomerPrincipal, DbSession, require_role
from app.api.routers import API_V1
from app.api.schemas.recommendations import AllocationRowOut, RecommendationIn, RecommendationOut, pct
from app.core.security import Role
from app.services import recommendation_service
from app.services.errors import not_found
from app.services.recommendation_service import RecommendationView

router = APIRouter(
    prefix=f"{API_V1}/recommendations",
    tags=["recommendations"],
    dependencies=[Depends(require_role(Role.CUSTOMER))],
)


def _out(view: RecommendationView) -> RecommendationOut:
    return RecommendationOut(
        id=view.id,
        source=view.source.value,
        risk_band=view.risk_band,
        template_version_no=view.template_version_no,
        goal_id=view.goal_id,
        horizon_months=view.horizon_months,
        horizon_rule=view.horizon_rule,
        as_of_date=view.as_of_date,
        allocation=[AllocationRowOut(asset_class=code, target_pct=pct(value)) for code, value in view.allocation],
        total_pct=pct(view.total_pct),
        created_at=view.created_at,
    )


@router.post("", response_model=RecommendationOut, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    session: DbSession,
    clock: CurrentClock,
    principal: CustomerPrincipal,
    customer_id: CurrentCustomerId,
    body: RecommendationIn | None = None,
) -> RecommendationOut:
    goal_id = None if body is None or body.goal_id is None else str(body.goal_id)
    view = recommendation_service.create_recommendation(session, clock, principal, customer_id, goal_id)
    return _out(view)


@router.get("/latest", response_model=RecommendationOut)
def get_latest(session: DbSession, customer_id: CurrentCustomerId) -> RecommendationOut:
    view = recommendation_service.latest_for(session, customer_id)
    if view is None:
        raise not_found("RECOMMENDATION_NOT_FOUND", "No recommendation yet.")
    return _out(view)


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(session: DbSession, customer_id: CurrentCustomerId) -> list[RecommendationOut]:
    return [_out(v) for v in recommendation_service.list_for(session, customer_id)]
