"""Advisor workbench API endpoints (advisor_workbench_spec §4, AC-09)."""

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.api.schemas.advisor import (
    AdvisorCustomerOut,
    AdvisorCustomerPortfolioOut,
    AuditEventOut,
    CustomerInfoOut,
    ManualRecommendationIn,
    RiskOverrideIn,
    RiskOverrideOut,
    RiskProfileSummaryOut,
)
from app.api.schemas.decimals import require_decimal_strings
from app.api.schemas.goals import GoalOut, GoalProgressOut
from app.api.schemas.holdings import HoldingLineResponse, HoldingsResponse
from app.api.schemas.rebalancing import fmt2, fmt4
from app.api.schemas.recommendations import RecommendationOut
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import advisor_service
from app.services.customer_resolver import user_id_for
from app.services.errors import unprocessable

router = APIRouter(prefix=API_V1 + "/advisor", tags=["advisor"])


def _advisor_user_id(session: Session, principal: Principal) -> str:
    uid = user_id_for(session, principal)
    if uid is None:
        raise RuntimeError("advisor principal without a user row")
    return uid


@router.get("/customers", response_model=list[AdvisorCustomerOut])
def list_assigned_customers(
    principal: Annotated[Principal, Depends(require_role(Role.ADVISOR))],
    session: Annotated[Session, Depends(get_db)],
) -> list[AdvisorCustomerOut]:
    """List all customers assigned to the advisor with portfolio and drift status (AC-09)."""
    advisor_user_id = _advisor_user_id(session, principal)
    views = advisor_service.list_assigned_customers(session, advisor_user_id)
    return [
        AdvisorCustomerOut(
            customer_id=v.customer_id,
            display_name=v.display_name,
            effective_band=v.effective_band,
            band_source=v.band_source,
            portfolio_breached=v.portfolio_breached,
            open_rebalance_id=v.open_rebalance_id,
        )
        for v in views
    ]


@router.get("/customers/{customer_id}/portfolio", response_model=AdvisorCustomerPortfolioOut)
def get_customer_portfolio(
    customer_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.ADVISOR))],
    session: Annotated[Session, Depends(get_db)],
) -> AdvisorCustomerPortfolioOut:
    """Get complete portfolio overview for an assigned customer (AC-09)."""
    advisor_user_id = _advisor_user_id(session, principal)
    v = advisor_service.get_customer_portfolio(session, advisor_user_id, customer_id)

    goals_out = [
        GoalOut(
            id=g.id,
            customer_id=g.customer_id,
            name=g.name,
            goal_type=g.goal_type,
            target_amount=fmt2(g.target_amount) or "0.00",
            target_date=g.target_date,
            priority=g.priority,
            funding_share_pct=fmt2(g.funding_share_pct) or "0.00",
            created_at=g.created_at,
            updated_at=g.updated_at,
            progress=(
                GoalProgressOut(
                    nav_date=g.progress.nav_date,
                    current_goal_value=fmt2(g.progress.current_goal_value) or "0.00",
                    percent_complete=fmt2(g.progress.percent_complete) or "0.00",
                    status=g.progress.status,
                    reason=g.progress.reason,
                    created_at=g.progress.created_at,
                )
                if g.progress
                else None
            ),
        )
        for g in v.goals
    ]

    h_lines = [
        HoldingLineResponse(
            asset_class=hl.asset_class,
            units=fmt4(hl.units) or "0.0000",
            nav=fmt4(hl.nav) or "0.0000",
            current_value=fmt2(hl.current_value) or "0.00",
            current_pct=fmt2(hl.current_pct),
            target_pct=fmt2(hl.target_pct),
            drift_pct=fmt2(hl.drift_pct),
            breached=hl.breached,
        )
        for hl in v.holdings.lines
    ]

    holdings_out = HoldingsResponse(
        nav_date=v.holdings.nav_date,
        total_value=fmt2(v.holdings.total_value) or "0.00",
        has_target=v.holdings.has_target,
        recommendation_id=v.holdings.recommendation_id,
        template_version_no=v.holdings.template_version_no,
        drift_threshold_pct=fmt2(v.holdings.drift_threshold_pct),
        portfolio_breached=v.holdings.portfolio_breached,
        lines=h_lines,
    )

    from app.api.routers.recommendations import _out as _rec_out

    rec_out = _rec_out(v.latest_recommendation) if v.latest_recommendation else None

    from app.api.routers.rebalancing import _to_proposal_out

    open_rebal_out = _to_proposal_out(v.open_rebalance) if v.open_rebalance else None

    return AdvisorCustomerPortfolioViewOut(
        customer=CustomerInfoOut(
            id=v.customer.id, display_name=v.customer.display_name, kyc_verified=v.customer.kyc_verified
        ),
        risk_profile=RiskProfileSummaryOut(
            band=v.risk_profile.band, source=v.risk_profile.source, as_of=v.risk_profile.as_of
        ),
        goals=goals_out,
        holdings=holdings_out,
        latest_recommendation=rec_out,
        open_rebalance=open_rebal_out,
    )


class AdvisorCustomerPortfolioViewOut(AdvisorCustomerPortfolioOut):
    pass


@router.post(
    "/customers/{customer_id}/risk-overrides",
    response_model=RiskOverrideOut,
    status_code=status.HTTP_201_CREATED,
)
def override_risk_band(
    customer_id: str,
    payload: RiskOverrideIn,
    principal: Annotated[Principal, Depends(require_role(Role.ADVISOR))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> RiskOverrideOut:
    """Override customer risk band with reason and note (AC-09.1)."""
    advisor_user_id = _advisor_user_id(session, principal)
    v = advisor_service.override_risk_band(
        session=session,
        clock=clock,
        principal=principal,
        advisor_user_id=advisor_user_id,
        customer_id=customer_id,
        new_band=payload.new_band,
        reason_code=payload.reason_code,
        note=payload.note,
    )
    return RiskOverrideOut(
        override_id=v.override_id,
        previous_band=v.previous_band,
        new_band=v.new_band,
        reason_code=v.reason_code,
        actor_user_id=v.actor_user_id,
        created_at=v.created_at,
    )


@router.post(
    "/customers/{customer_id}/manual-recommendations",
    response_model=RecommendationOut,
    status_code=status.HTTP_201_CREATED,
)
def log_manual_recommendation(
    customer_id: str,
    payload: ManualRecommendationIn,
    principal: Annotated[Principal, Depends(require_role(Role.ADVISOR))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> RecommendationOut:
    """Log manual allocation recommendation for customer (AC-09.8)."""
    require_decimal_strings(payload.model_dump())
    advisor_user_id = _advisor_user_id(session, principal)

    alloc_items: list[advisor_service.ManualAllocationItem] = []
    for item in payload.allocation:
        try:
            val = Decimal(item.target_pct)
        except InvalidOperation as exc:
            raise unprocessable("ALLOCATION_PERCENTAGE_INVALID", "Target pct must be a valid decimal string.") from exc
        alloc_items.append(advisor_service.ManualAllocationItem(asset_class=item.asset_class, target_pct=val))

    rec_view = advisor_service.create_manual_recommendation(
        session=session,
        clock=clock,
        principal=principal,
        advisor_user_id=advisor_user_id,
        customer_id=customer_id,
        allocations=alloc_items,
        note=payload.note,
    )

    from app.api.routers.recommendations import _out as _rec_out

    return _rec_out(rec_view)


@router.get("/customers/{customer_id}/audit", response_model=list[AuditEventOut])
def get_customer_audit(
    customer_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.ADVISOR))],
    session: Annotated[Session, Depends(get_db)],
) -> list[AuditEventOut]:
    """Get audit trail for customer without sensitive notes (AC-09.2)."""
    advisor_user_id = _advisor_user_id(session, principal)
    views = advisor_service.get_customer_audit(session, advisor_user_id, customer_id)
    return [
        AuditEventOut(
            occurred_at=v.occurred_at,
            action=v.action,
            actor_role=v.actor_role,
            actor_user_id=v.actor_user_id,
            entity_type=v.entity_type,
            entity_id=v.entity_id,
            details=v.details,
        )
        for v in views
    ]
