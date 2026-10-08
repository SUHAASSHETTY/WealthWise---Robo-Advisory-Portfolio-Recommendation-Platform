"""Data access for rebalancing recommendations, lines, decisions, and stub orders (rebalancing_spec §3)."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.repositories.models.rebalancing_decision import RebalancingDecision
from app.repositories.models.rebalancing_recommendation import RebalancingLine, RebalancingRecommendation
from app.repositories.models.stub_order import StubOrder


def create_recommendation(
    session: Session,
    rec: RebalancingRecommendation,
    lines: Sequence[RebalancingLine],
) -> RebalancingRecommendation:
    """Insert a new rebalancing recommendation and its lines in one transaction."""
    session.add(rec)
    session.add_all(lines)
    session.flush()
    return rec


def get_recommendation(session: Session, rec_id: str) -> RebalancingRecommendation | None:
    """Get rebalancing recommendation by ID with lines and decision loaded."""
    stmt = (
        select(RebalancingRecommendation)
        .options(
            selectinload(RebalancingRecommendation.lines),
            selectinload(RebalancingRecommendation.decision),
        )
        .where(RebalancingRecommendation.id == rec_id)
    )
    return session.scalars(stmt).first()


def get_recommendation_for_customer(
    session: Session, customer_id: str, rec_id: str
) -> RebalancingRecommendation | None:
    """Get rebalancing recommendation scoped to a customer."""
    stmt = (
        select(RebalancingRecommendation)
        .options(
            selectinload(RebalancingRecommendation.lines),
            selectinload(RebalancingRecommendation.decision),
        )
        .where(RebalancingRecommendation.id == rec_id, RebalancingRecommendation.customer_id == customer_id)
    )
    return session.scalars(stmt).first()


def get_open_for_customer(session: Session, customer_id: str) -> RebalancingRecommendation | None:
    """Get the currently open (undecided) proposal for a customer, if any."""
    stmt = (
        select(RebalancingRecommendation)
        .outerjoin(
            RebalancingDecision,
            RebalancingRecommendation.id == RebalancingDecision.rebalancing_recommendation_id,
        )
        .options(
            selectinload(RebalancingRecommendation.lines),
            selectinload(RebalancingRecommendation.decision),
        )
        .where(
            RebalancingRecommendation.customer_id == customer_id,
            RebalancingDecision.id.is_(None),
        )
        .order_by(RebalancingRecommendation.created_at.desc(), RebalancingRecommendation.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def list_for_customer(session: Session, customer_id: str) -> Sequence[RebalancingRecommendation]:
    """List all rebalancing proposals for a customer, newest first."""
    stmt = (
        select(RebalancingRecommendation)
        .options(
            selectinload(RebalancingRecommendation.lines),
            selectinload(RebalancingRecommendation.decision),
        )
        .where(RebalancingRecommendation.customer_id == customer_id)
        .order_by(RebalancingRecommendation.created_at.desc(), RebalancingRecommendation.id.desc())
    )
    return session.scalars(stmt).all()


def create_decision(session: Session, decision: RebalancingDecision) -> RebalancingDecision:
    """Record a decision (ACCEPTED, DISMISSED, or EXPIRED) for a proposal."""
    session.add(decision)
    session.flush()
    return decision


def get_decision_for_recommendation(session: Session, rebalancing_recommendation_id: str) -> RebalancingDecision | None:
    """Get decision for a recommendation if exists."""
    stmt = select(RebalancingDecision).where(
        RebalancingDecision.rebalancing_recommendation_id == rebalancing_recommendation_id
    )
    return session.scalars(stmt).first()


def create_stub_orders(session: Session, orders: Sequence[StubOrder]) -> Sequence[StubOrder]:
    """Insert stub orders produced upon acceptance."""
    session.add_all(orders)
    session.flush()
    return orders


def list_stub_orders_for_recommendation(session: Session, rebalancing_recommendation_id: str) -> Sequence[StubOrder]:
    """Get stub orders produced for a recommendation."""
    stmt = (
        select(StubOrder)
        .where(StubOrder.rebalancing_recommendation_id == rebalancing_recommendation_id)
        .order_by(StubOrder.created_at.asc(), StubOrder.id.asc())
    )
    return session.scalars(stmt).all()


def expire_all_open_proposals(session: Session, now: datetime) -> list[RebalancingDecision]:
    """Expire all currently undecided proposals across all customers."""
    open_recs_stmt = (
        select(RebalancingRecommendation)
        .outerjoin(
            RebalancingDecision,
            RebalancingRecommendation.id == RebalancingDecision.rebalancing_recommendation_id,
        )
        .where(RebalancingDecision.id.is_(None))
    )
    open_recs = list(session.scalars(open_recs_stmt))
    decisions: list[RebalancingDecision] = []
    for rec in open_recs:
        dec = RebalancingDecision(
            rebalancing_recommendation_id=rec.id,
            decision="EXPIRED",
            reason=None,
            actor_user_id=None,
            actor_role="SYSTEM",
            created_at=now,
        )
        session.add(dec)
        decisions.append(dec)
    if decisions:
        session.flush()
    return decisions
