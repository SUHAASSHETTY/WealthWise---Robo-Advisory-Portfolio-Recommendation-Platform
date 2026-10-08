"""Goals service: CRUD and progress snapshots (goal_tracker_spec §2-4, AC-03, AC-08)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.domain.goal import GoalType
from app.domain.goal_rules import GoalInput, GoalValidationError, order_goals, validate_goal
from app.domain.money import q2
from app.repositories import audit_repository, goal_repository, goal_snapshot_repository, nav_repository
from app.repositories.models.goal import Goal
from app.repositories.models.goal_progress_snapshot import GoalProgressSnapshot
from app.services import holdings_service
from app.services.customer_resolver import user_id_for
from app.services.errors import conflict, not_found, unprocessable

logger = logging.getLogger(__name__)

ACTION_CREATED = "GOAL_CREATED"
ACTION_UPDATED = "GOAL_UPDATED"
ENTITY_TYPE = "goal"


@dataclass(frozen=True)
class GoalProgressView:
    nav_date: date
    current_goal_value: Decimal
    percent_complete: Decimal
    status: str
    reason: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class GoalView:
    id: str
    customer_id: str
    name: str
    goal_type: str
    target_amount: Decimal
    target_date: date
    priority: int
    funding_share_pct: Decimal
    created_at: datetime
    updated_at: datetime
    progress: GoalProgressView | None = None


@dataclass(frozen=True)
class GoalProgressHistoryView:
    latest: GoalProgressView | None
    history: Sequence[GoalProgressView]


def _compute_progress(
    total_value: Decimal, funding_share_pct: Decimal, target_amount: Decimal
) -> tuple[Decimal, Decimal, str]:
    current_goal_value = q2(total_value * funding_share_pct / Decimal("100"))
    if target_amount <= Decimal("0.00"):
        percent_complete = Decimal("0.00")
    else:
        percent_complete = q2(current_goal_value / target_amount * Decimal("100"))
    status = "ACHIEVED" if percent_complete >= Decimal("100.00") else "IN_PROGRESS"
    return current_goal_value, percent_complete, status


def create_goal(
    session: Session,
    clock: Clock,
    principal: Principal,
    customer_id: str,
    name: str,
    goal_type: str,
    target_amount: Decimal,
    target_date: date,
    priority: int,
    funding_share_pct: Decimal,
) -> GoalView:
    """Create a goal, snapshot its progress against latest NAV, and audit (AC-03, AC-08)."""
    existing = goal_repository.list_for_customer(session, customer_id)
    existing_inputs = [
        GoalInput(
            id=g.id,
            name=g.name,
            goal_type=g.goal_type,
            target_amount=g.target_amount,
            target_date=g.target_date,
            priority=g.priority,
            funding_share_pct=g.funding_share_pct,
            created_at=g.created_at,
        )
        for g in existing
    ]
    inp = GoalInput(
        name=name,
        goal_type=goal_type,
        target_amount=target_amount,
        target_date=target_date,
        priority=priority,
        funding_share_pct=funding_share_pct,
    )

    try:
        validate_goal(inp, existing_inputs, today=clock.today())
    except GoalValidationError as exc:
        raise unprocessable(exc.code, exc.message) from exc

    latest_nav = nav_repository.get_latest_nav_date(session)
    if latest_nav is None:
        raise conflict("NAV_NOT_LOADED", "NAVs must be loaded before creating a goal.")

    holdings_summary = holdings_service.get_holdings(session, customer_id)
    total_val = holdings_summary.total_value

    current_val, pct_comp, status = _compute_progress(total_val, funding_share_pct, target_amount)

    now = clock.now()
    goal = Goal(
        customer_id=customer_id,
        name=name.strip(),
        goal_type=GoalType(goal_type),
        target_amount=target_amount,
        target_date=target_date,
        priority=priority,
        funding_share_pct=funding_share_pct,
        created_at=now,
        updated_at=now,
    )
    goal = goal_repository.create(session, goal)

    snap = GoalProgressSnapshot(
        goal_id=goal.id,
        nav_date=latest_nav,
        total_value=total_val,
        funding_share_pct=funding_share_pct,
        current_goal_value=current_val,
        percent_complete=pct_comp,
        status=status,
        reason="GOAL_CREATED",
        created_at=now,
    )
    goal_snapshot_repository.add_snapshots(session, [snap])

    audit_repository.insert_audit_event(
        session,
        actor_user_id=user_id_for(session, principal),
        actor_role=principal.role.value,
        action=ACTION_CREATED,
        entity_type=ENTITY_TYPE,
        entity_id=goal.id,
        details={},
    )
    session.commit()
    logger.info("goal created", extra={"customer_id": customer_id, "entity_id": goal.id})

    prog = GoalProgressView(
        nav_date=snap.nav_date,
        current_goal_value=snap.current_goal_value,
        percent_complete=snap.percent_complete,
        status=snap.status,
        reason=snap.reason,
        created_at=snap.created_at,
    )
    return GoalView(
        id=goal.id,
        customer_id=goal.customer_id,
        name=goal.name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        priority=goal.priority,
        funding_share_pct=goal.funding_share_pct,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        progress=prog,
    )


def list_goals(session: Session, customer_id: str) -> list[GoalView]:
    """List goals for customer in priority order with latest progress (AC-03.2)."""
    goals = goal_repository.list_for_customer(session, customer_id)
    ordered = order_goals(goals)

    views: list[GoalView] = []
    for g in ordered:
        snap = goal_snapshot_repository.get_latest_for_goal(session, g.id)
        prog = (
            GoalProgressView(
                nav_date=snap.nav_date,
                current_goal_value=snap.current_goal_value,
                percent_complete=snap.percent_complete,
                status=snap.status,
                reason=snap.reason,
                created_at=snap.created_at,
            )
            if snap
            else None
        )
        views.append(
            GoalView(
                id=g.id,
                customer_id=g.customer_id,
                name=g.name,
                goal_type=g.goal_type,
                target_amount=g.target_amount,
                target_date=g.target_date,
                priority=g.priority,
                funding_share_pct=g.funding_share_pct,
                created_at=g.created_at,
                updated_at=g.updated_at,
                progress=prog,
            )
        )
    return views


def get_goal(session: Session, customer_id: str, goal_id: str) -> GoalView:
    """Get single goal with progress."""
    g = goal_repository.get_for_customer(session, customer_id, goal_id)
    if g is None:
        raise not_found("GOAL_NOT_FOUND", "Goal not found.")

    snap = goal_snapshot_repository.get_latest_for_goal(session, g.id)
    prog = (
        GoalProgressView(
            nav_date=snap.nav_date,
            current_goal_value=snap.current_goal_value,
            percent_complete=snap.percent_complete,
            status=snap.status,
            reason=snap.reason,
            created_at=snap.created_at,
        )
        if snap
        else None
    )
    return GoalView(
        id=g.id,
        customer_id=g.customer_id,
        name=g.name,
        goal_type=g.goal_type,
        target_amount=g.target_amount,
        target_date=g.target_date,
        priority=g.priority,
        funding_share_pct=g.funding_share_pct,
        created_at=g.created_at,
        updated_at=g.updated_at,
        progress=prog,
    )


def update_goal(
    session: Session,
    clock: Clock,
    principal: Principal,
    customer_id: str,
    goal_id: str,
    name: str,
    goal_type: str,
    target_amount: Decimal,
    target_date: date,
    priority: int,
    funding_share_pct: Decimal,
) -> GoalView:
    """Update goal attributes and snapshot new progress (AC-03)."""
    goal = goal_repository.get_for_customer(session, customer_id, goal_id)
    if goal is None:
        raise not_found("GOAL_NOT_FOUND", "Goal not found.")

    existing = goal_repository.list_for_customer(session, customer_id)
    existing_inputs = [
        GoalInput(
            id=g.id,
            name=g.name,
            goal_type=g.goal_type,
            target_amount=g.target_amount,
            target_date=g.target_date,
            priority=g.priority,
            funding_share_pct=g.funding_share_pct,
            created_at=g.created_at,
        )
        for g in existing
    ]
    inp = GoalInput(
        id=goal_id,
        name=name,
        goal_type=goal_type,
        target_amount=target_amount,
        target_date=target_date,
        priority=priority,
        funding_share_pct=funding_share_pct,
    )

    try:
        validate_goal(inp, existing_inputs, today=clock.today(), updating_goal_id=goal_id)
    except GoalValidationError as exc:
        raise unprocessable(exc.code, exc.message) from exc

    latest_nav = nav_repository.get_latest_nav_date(session)
    if latest_nav is None:
        raise conflict("NAV_NOT_LOADED", "NAVs must be loaded.")

    holdings_summary = holdings_service.get_holdings(session, customer_id)
    total_val = holdings_summary.total_value

    current_val, pct_comp, status = _compute_progress(total_val, funding_share_pct, target_amount)

    now = clock.now()
    goal.name = name.strip()
    goal.goal_type = GoalType(goal_type)
    goal.target_amount = target_amount
    goal.target_date = target_date
    goal.priority = priority
    goal.funding_share_pct = funding_share_pct
    goal.updated_at = now

    snap = GoalProgressSnapshot(
        goal_id=goal.id,
        nav_date=latest_nav,
        total_value=total_val,
        funding_share_pct=funding_share_pct,
        current_goal_value=current_val,
        percent_complete=pct_comp,
        status=status,
        reason="GOAL_UPDATED",
        created_at=now,
    )
    goal_snapshot_repository.add_snapshots(session, [snap])

    audit_repository.insert_audit_event(
        session,
        actor_user_id=user_id_for(session, principal),
        actor_role=principal.role.value,
        action=ACTION_UPDATED,
        entity_type=ENTITY_TYPE,
        entity_id=goal.id,
        details={},
    )
    session.commit()
    logger.info("goal updated", extra={"customer_id": customer_id, "entity_id": goal.id})

    prog = GoalProgressView(
        nav_date=snap.nav_date,
        current_goal_value=snap.current_goal_value,
        percent_complete=snap.percent_complete,
        status=snap.status,
        reason=snap.reason,
        created_at=snap.created_at,
    )
    return GoalView(
        id=goal.id,
        customer_id=goal.customer_id,
        name=goal.name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        priority=goal.priority,
        funding_share_pct=goal.funding_share_pct,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        progress=prog,
    )


def get_goal_progress(session: Session, customer_id: str, goal_id: str) -> GoalProgressHistoryView:
    """Get complete progress snapshot history for a goal (AC-08)."""
    goal = goal_repository.get_for_customer(session, customer_id, goal_id)
    if goal is None:
        raise not_found("GOAL_NOT_FOUND", "Goal not found.")

    snaps = goal_snapshot_repository.list_for_goal(session, goal_id)
    history_views = [
        GoalProgressView(
            nav_date=s.nav_date,
            current_goal_value=s.current_goal_value,
            percent_complete=s.percent_complete,
            status=s.status,
            reason=s.reason,
            created_at=s.created_at,
        )
        for s in snaps
    ]
    latest = history_views[0] if history_views else None
    return GoalProgressHistoryView(latest=latest, history=history_views)
