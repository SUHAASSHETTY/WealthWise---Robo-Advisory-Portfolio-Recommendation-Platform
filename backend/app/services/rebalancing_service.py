"""Rebalancing service: evaluation, proposal lifecycle, acceptance/dismissal (rebalancing_spec §2-4, AC-06, AC-07)."""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.domain.drift_policy import ValuedHolding
from app.domain.rebalancing_policy import propose_rebalance
from app.repositories import (
    asset_class_repository,
    audit_repository,
    customer_repository,
    holding_repository,
    nav_repository,
    policy_version_repository,
    rebalancing_repository,
    recommendation_repository,
)
from app.repositories.models.rebalancing_decision import RebalancingDecision
from app.repositories.models.rebalancing_recommendation import RebalancingLine, RebalancingRecommendation
from app.repositories.models.stub_order import StubOrder
from app.repositories.models.template_version import TemplateVersion
from app.services import holdings_service
from app.services.customer_resolver import user_id_for
from app.services.errors import conflict, not_found, unprocessable

logger = logging.getLogger(__name__)

ACTION_ACCEPTED = "REBALANCE_ACCEPTED"
ACTION_DISMISSED = "REBALANCE_DISMISSED"
ENTITY_TYPE = "rebalancing_recommendation"


@dataclass(frozen=True)
class DecisionView:
    decision: str
    actor_role: str
    created_at: datetime
    reason: str | None = None


@dataclass(frozen=True)
class StubOrderView:
    id: str
    asset_class: str
    side: str
    quantity: Decimal
    trade_value: Decimal
    status: str


@dataclass(frozen=True)
class RebalancingLineView:
    asset_class: str
    current_value: Decimal
    current_pct: Decimal | None
    target_pct: Decimal | None
    drift_pct: Decimal | None
    target_value: Decimal | None
    nav: Decimal
    action: str
    quantity: Decimal | None
    trade_value: Decimal | None


@dataclass(frozen=True)
class RebalancingRecommendationView:
    id: str
    customer_id: str
    nav_date: date
    status: str  # PROPOSED | ACCEPTED | DISMISSED | EXPIRED
    total_value: Decimal
    drift_threshold_pct: Decimal
    post_trade_cash: Decimal
    created_at: datetime
    lines: Sequence[RebalancingLineView]
    decision: DecisionView | None = None


@dataclass(frozen=True)
class RebalancingSummaryView:
    id: str
    status: str
    nav_date: date
    created_at: datetime


@dataclass(frozen=True)
class EvaluationResult:
    created: bool
    breached: bool
    reason: str | None = None
    proposal: RebalancingRecommendationView | None = None


def _status_for(rec: RebalancingRecommendation) -> str:
    if rec.decision is None:
        return "PROPOSED"
    return str(rec.decision.decision)


def _view_for(rec: RebalancingRecommendation) -> RebalancingRecommendationView:
    status = _status_for(rec)
    lines_view = [
        RebalancingLineView(
            asset_class=row.asset_class_code,
            current_value=row.current_value,
            current_pct=row.current_pct,
            target_pct=row.target_pct,
            drift_pct=row.drift_pct,
            target_value=row.target_value,
            nav=row.nav,
            action=row.action,
            quantity=row.quantity,
            trade_value=row.trade_value,
        )
        for row in sorted(rec.lines, key=lambda line: line.id)
    ]
    dec_view = (
        DecisionView(
            decision=rec.decision.decision,
            actor_role=rec.decision.actor_role,
            created_at=rec.decision.created_at,
            reason=rec.decision.reason,
        )
        if rec.decision
        else None
    )
    return RebalancingRecommendationView(
        id=rec.id,
        customer_id=rec.customer_id,
        nav_date=rec.nav_date,
        status=status,
        total_value=rec.total_value,
        drift_threshold_pct=rec.drift_threshold_pct,
        post_trade_cash=rec.post_trade_cash,
        created_at=rec.created_at,
        lines=lines_view,
        decision=dec_view,
    )


def evaluate_customer_rebalancing(
    session: Session,
    clock: Clock,
    customer_id: str,
) -> EvaluationResult:
    """Evaluate rebalancing trigger and return proposal if breached (AC-06)."""
    latest_rec = recommendation_repository.latest_for_customer(session, customer_id)
    if latest_rec is None:
        raise conflict("RECOMMENDATION_REQUIRED", "Customer must have a target recommendation.")

    latest_nav = nav_repository.get_latest_nav_date(session)
    if latest_nav is None:
        raise conflict("NAV_NOT_LOADED", "NAVs must be loaded before evaluating rebalancing.")

    # Get threshold from the template version referenced by the recommendation (AC-10.5 in-flight version)
    template_version = policy_version_repository.get(session, TemplateVersion, latest_rec.template_version_id)
    if template_version is not None:
        defn = template_version.definition
        if isinstance(defn, str):
            defn = json.loads(defn)
        threshold = Decimal(str(defn.get("drift_threshold_pct", "5.00")))
    else:
        threshold = Decimal("5.00")

    holdings_summary = holdings_service.get_holdings(session, customer_id)
    if holdings_summary.total_value == Decimal("0.00"):
        return EvaluationResult(created=False, breached=False, reason="EMPTY_PORTFOLIO", proposal=None)

    # Check if breached (any drift strictly > threshold)
    breached = any(line.drift_pct is not None and line.drift_pct > threshold for line in holdings_summary.lines)
    if not breached:
        return EvaluationResult(created=False, breached=False, reason="WITHIN_THRESHOLD", proposal=None)

    # Check if there is already an open proposal for the current nav_date
    open_prop = rebalancing_repository.get_open_for_customer(session, customer_id)
    if open_prop is not None and open_prop.nav_date == latest_nav:
        return EvaluationResult(created=False, breached=True, proposal=_view_for(open_prop))

    # Build target map and nav map
    target_map = {code: pct for code, pct in latest_rec.allocation}
    nav_map = dict(nav_repository.get_navs_for_date(session, latest_nav))
    nav_map["CASH"] = Decimal("1.0000")

    # Get asset classes display order
    active_classes = asset_class_repository.list_active(session)
    display_order = [ac.code for ac in active_classes]

    valued_holdings = [
        ValuedHolding(
            asset_class=line.asset_class,
            units=line.units,
            nav=line.nav,
            current_value=line.current_value,
        )
        for line in holdings_summary.lines
    ]

    proposal_result = propose_rebalance(
        valued=valued_holdings,
        target=target_map,
        navs=nav_map,
        display_order=display_order,
    )

    now = clock.now()
    rec_obj = RebalancingRecommendation(
        customer_id=customer_id,
        based_on_recommendation_id=latest_rec.id,
        template_version_id=latest_rec.template_version_id,
        nav_date=latest_nav,
        total_value=proposal_result.total_value,
        drift_threshold_pct=threshold,
        post_trade_cash=proposal_result.post_trade_cash,
        created_at=now,
    )
    rec_lines = [
        RebalancingLine(
            rebalancing_recommendation_id=rec_obj.id,
            asset_class_code=line.asset_class,
            current_value=line.current_value,
            current_pct=line.current_pct,
            target_pct=line.target_pct,
            drift_pct=line.drift_pct,
            target_value=line.target_value,
            nav=line.nav,
            action=line.action,
            quantity=line.quantity,
            trade_value=line.trade_value,
        )
        for line in proposal_result.lines
    ]
    rec_obj.lines = rec_lines
    rebalancing_repository.create_recommendation(session, rec_obj, rec_lines)
    session.commit()

    logger.info(
        "rebalancing proposed",
        extra={"customer_id": customer_id, "entity_id": rec_obj.id, "line_count": len(rec_lines)},
    )
    return EvaluationResult(created=True, breached=True, proposal=_view_for(rec_obj))


def get_recommendation(session: Session, customer_id: str, rec_id: str) -> RebalancingRecommendationView:
    """Get single rebalance recommendation scoped to customer (AC-07)."""
    rec = rebalancing_repository.get_recommendation_for_customer(session, customer_id, rec_id)
    if rec is None:
        raise not_found("RECOMMENDATION_NOT_FOUND", "Proposal not found.")
    return _view_for(rec)


def list_recommendations(session: Session, customer_id: str) -> list[RebalancingSummaryView]:
    """List rebalancing recommendations for customer, newest first (AC-07)."""
    recs = rebalancing_repository.list_for_customer(session, customer_id)
    return [
        RebalancingSummaryView(
            id=r.id,
            status=_status_for(r),
            nav_date=r.nav_date,
            created_at=r.created_at,
        )
        for r in recs
    ]


def accept_proposal(
    session: Session,
    clock: Clock,
    principal: Principal,
    customer_id: str,
    rec_id: str,
) -> tuple[str, list[StubOrderView]]:
    """Accept rebalancing proposal, create stub orders, update holdings units, audit (AC-07.2)."""
    rec = rebalancing_repository.get_recommendation_for_customer(session, customer_id, rec_id)
    if rec is None:
        raise not_found("RECOMMENDATION_NOT_FOUND", "Proposal not found.")

    if rec.decision is not None:
        raise conflict("ALREADY_DECIDED", "This proposal has already been decided.")

    # Check KYC
    cust = customer_repository.get_by_id(session, customer_id)
    if cust is None or not cust.kyc_verified:
        raise conflict("KYC_NOT_VERIFIED", "Customer KYC is not verified.")

    # Check stale (proposal nav_date must equal latest nav_date)
    latest_nav = nav_repository.get_latest_nav_date(session)
    if latest_nav is None or rec.nav_date != latest_nav:
        raise conflict("RECOMMENDATION_STALE", "Proposal is based on stale NAV prices.")

    now = clock.now()
    actor_id = user_id_for(session, principal)

    # 1. Decision
    decision = RebalancingDecision(
        rebalancing_recommendation_id=rec.id,
        decision="ACCEPTED",
        reason=None,
        actor_user_id=actor_id,
        actor_role="CUSTOMER",
        created_at=now,
    )
    rebalancing_repository.create_decision(session, decision)

    # 2. Stub orders
    orders: list[StubOrder] = []
    for line in rec.lines:
        if line.action in ("BUY", "SELL") and line.quantity is not None and line.quantity > Decimal("0.0000"):
            order = StubOrder(
                rebalancing_recommendation_id=rec.id,
                asset_class_code=line.asset_class_code,
                side=line.action,
                quantity=line.quantity,
                nav=line.nav,
                trade_value=line.trade_value or Decimal("0.00"),
                status="FILLED_STUB",
                created_at=now,
            )
            orders.append(order)

    rebalancing_repository.create_stub_orders(session, orders)

    # 3. Update holdings units
    holdings_list = holding_repository.list_for_customer(session, customer_id)
    holdings_by_class = {h.asset_class_code: h for h in holdings_list}

    for line in rec.lines:
        h = holdings_by_class.get(line.asset_class_code)
        if h is not None:
            if line.action == "BUY" and line.quantity:
                h.units += line.quantity
                h.updated_at = now
            elif line.action == "SELL" and line.quantity:
                h.units -= line.quantity
                h.updated_at = now
            elif line.action == "SETTLEMENT":
                h.units = rec.post_trade_cash
                h.updated_at = now

    # 4. Audit
    audit_repository.insert_audit_event(
        session,
        actor_user_id=actor_id,
        actor_role=principal.role.value,
        action=ACTION_ACCEPTED,
        entity_type=ENTITY_TYPE,
        entity_id=rec.id,
        details={"order_count": len(orders)},
    )

    session.commit()
    logger.info("rebalance accepted", extra={"customer_id": customer_id, "entity_id": rec.id, "decision": "ACCEPTED"})

    order_views = [
        StubOrderView(
            id=o.id,
            asset_class=o.asset_class_code,
            side=o.side,
            quantity=o.quantity,
            trade_value=o.trade_value,
            status=o.status,
        )
        for o in orders
    ]
    return rec.id, order_views


def dismiss_proposal(
    session: Session,
    clock: Clock,
    principal: Principal,
    customer_id: str,
    rec_id: str,
    reason: str | None = None,
) -> str:
    """Dismiss rebalancing proposal and audit (AC-07.3)."""
    rec = rebalancing_repository.get_recommendation_for_customer(session, customer_id, rec_id)
    if rec is None:
        raise not_found("RECOMMENDATION_NOT_FOUND", "Proposal not found.")

    if rec.decision is not None:
        raise conflict("ALREADY_DECIDED", "This proposal has already been decided.")

    if reason is not None and len(reason.strip()) > 500:
        raise unprocessable("DISMISS_REASON_INVALID", "Dismiss reason must not exceed 500 characters.")

    now = clock.now()
    actor_id = user_id_for(session, principal)

    decision = RebalancingDecision(
        rebalancing_recommendation_id=rec.id,
        decision="DISMISSED",
        reason=reason.strip() if reason else None,
        actor_user_id=actor_id,
        actor_role="CUSTOMER",
        created_at=now,
    )
    rebalancing_repository.create_decision(session, decision)

    audit_repository.insert_audit_event(
        session,
        actor_user_id=actor_id,
        actor_role=principal.role.value,
        action=ACTION_DISMISSED,
        entity_type=ENTITY_TYPE,
        entity_id=rec.id,
        details={},
    )

    session.commit()
    logger.info("rebalance dismissed", extra={"customer_id": customer_id, "entity_id": rec.id, "decision": "DISMISSED"})
    return rec.id
