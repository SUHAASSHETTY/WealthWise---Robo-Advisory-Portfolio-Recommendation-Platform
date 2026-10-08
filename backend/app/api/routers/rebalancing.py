"""Rebalancing API endpoints (rebalancing_spec §4, AC-06, AC-07)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.api.schemas.rebalancing import (
    AcceptProposalOut,
    DecisionOut,
    DismissIn,
    DismissProposalOut,
    RebalanceLineOut,
    RebalanceProposalOut,
    RebalanceSummaryOut,
    StubOrderOut,
    fmt2,
    fmt4,
)
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import rebalancing_service
from app.services.customer_resolver import customer_id_for

router = APIRouter(prefix=API_V1 + "/rebalancing", tags=["rebalancing"])


def _to_proposal_out(rec: rebalancing_service.RebalancingRecommendationView) -> RebalanceProposalOut:
    lines = [
        RebalanceLineOut(
            asset_class=line.asset_class,
            current_value=fmt2(line.current_value) or "0.00",
            current_pct=fmt2(line.current_pct),
            target_pct=fmt2(line.target_pct),
            drift_pct=fmt2(line.drift_pct),
            target_value=fmt2(line.target_value),
            nav=fmt4(line.nav) or "0.0000",
            action=line.action,
            quantity=fmt4(line.quantity),
            trade_value=fmt2(line.trade_value),
        )
        for line in rec.lines
    ]
    dec = (
        DecisionOut(
            decision=rec.decision.decision,
            actor_role=rec.decision.actor_role,
            created_at=rec.decision.created_at,
            reason=rec.decision.reason,
        )
        if rec.decision
        else None
    )
    return RebalanceProposalOut(
        id=rec.id,
        customer_id=rec.customer_id,
        nav_date=rec.nav_date,
        status=rec.status,
        total_value=fmt2(rec.total_value) or "0.00",
        drift_threshold_pct=fmt2(rec.drift_threshold_pct) or "0.00",
        post_trade_cash=fmt2(rec.post_trade_cash) or "0.00",
        created_at=rec.created_at,
        lines=lines,
        decision=dec,
    )


@router.post("/evaluate")
def evaluate_rebalancing(
    response: Response,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, Any]:
    """Evaluate rebalancing trigger, returning proposal or within threshold status (AC-06)."""
    customer_id = customer_id_for(session, principal)
    result = rebalancing_service.evaluate_customer_rebalancing(session, clock, customer_id)

    if not result.breached or result.proposal is None:
        response.status_code = status.HTTP_200_OK
        return {"breached": False, "reason": result.reason}

    proposal_out = _to_proposal_out(result.proposal)
    if result.created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return proposal_out.model_dump(mode="json")


@router.get("/recommendations", response_model=list[RebalanceSummaryOut])
def list_rebalancing_recommendations(
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
) -> list[RebalanceSummaryOut]:
    """List all rebalancing proposals for customer, newest first (AC-07)."""
    customer_id = customer_id_for(session, principal)
    views = rebalancing_service.list_recommendations(session, customer_id)
    return [
        RebalanceSummaryOut(
            id=v.id,
            status=v.status,
            nav_date=v.nav_date,
            created_at=v.created_at,
        )
        for v in views
    ]


@router.get("/recommendations/{rec_id}", response_model=RebalanceProposalOut)
def get_rebalancing_recommendation(
    rec_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
) -> RebalanceProposalOut:
    """Get single rebalance proposal by ID (AC-07.1)."""
    customer_id = customer_id_for(session, principal)
    view = rebalancing_service.get_recommendation(session, customer_id, rec_id)
    return _to_proposal_out(view)


@router.post("/recommendations/{rec_id}/accept", response_model=AcceptProposalOut)
def accept_rebalancing_recommendation(
    rec_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AcceptProposalOut:
    """Accept rebalancing proposal and produce stub orders (AC-07.2)."""
    customer_id = customer_id_for(session, principal)
    proposal_id, orders = rebalancing_service.accept_proposal(session, clock, principal, customer_id, rec_id)
    order_outs = [
        StubOrderOut(
            id=o.id,
            asset_class=o.asset_class,
            side=o.side,
            quantity=fmt4(o.quantity) or "0.0000",
            trade_value=fmt2(o.trade_value) or "0.00",
            status=o.status,
        )
        for o in orders
    ]
    return AcceptProposalOut(id=proposal_id, status="ACCEPTED", orders=order_outs)


@router.post("/recommendations/{rec_id}/dismiss", response_model=DismissProposalOut)
def dismiss_rebalancing_recommendation(
    rec_id: str,
    payload: DismissIn | None,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> DismissProposalOut:
    """Dismiss rebalancing proposal (AC-07.3)."""
    customer_id = customer_id_for(session, principal)
    reason = payload.reason if payload else None
    proposal_id = rebalancing_service.dismiss_proposal(session, clock, principal, customer_id, rec_id, reason=reason)
    return DismissProposalOut(id=proposal_id, status="DISMISSED")
