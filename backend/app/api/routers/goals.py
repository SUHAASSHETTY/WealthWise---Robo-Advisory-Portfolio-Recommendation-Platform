"""Goals API endpoints (goal_tracker_spec §4, AC-03, AC-08)."""

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_role
from app.api.routers import API_V1
from app.api.schemas.decimals import require_decimal_strings
from app.api.schemas.goals import GoalCreateIn, GoalOut, GoalProgressHistoryOut, GoalProgressOut, fmt2
from app.core.clock import Clock
from app.core.security import Principal, Role
from app.services import goals_service
from app.services.customer_resolver import customer_id_for
from app.services.errors import unprocessable

router = APIRouter(prefix=API_V1 + "/goals", tags=["goals"])


def _to_goal_out(v: goals_service.GoalView) -> GoalOut:
    prog_out = (
        GoalProgressOut(
            nav_date=v.progress.nav_date,
            current_goal_value=fmt2(v.progress.current_goal_value) or "0.00",
            percent_complete=fmt2(v.progress.percent_complete) or "0.00",
            status=v.progress.status,
            reason=v.progress.reason,
            created_at=v.progress.created_at,
        )
        if v.progress
        else None
    )
    return GoalOut(
        id=v.id,
        customer_id=v.customer_id,
        name=v.name,
        goal_type=v.goal_type,
        target_amount=fmt2(v.target_amount) or "0.00",
        target_date=v.target_date,
        priority=v.priority,
        funding_share_pct=fmt2(v.funding_share_pct) or "0.00",
        created_at=v.created_at,
        updated_at=v.updated_at,
        progress=prog_out,
    )


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreateIn,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GoalOut:
    """Create a new financial goal (AC-03.1)."""
    require_decimal_strings(payload.model_dump())
    customer_id = customer_id_for(session, principal)

    try:
        tgt_amount = Decimal(payload.target_amount)
    except InvalidOperation as exc:
        raise unprocessable("TARGET_AMOUNT_INVALID", "Target amount must be a valid decimal string.") from exc

    try:
        fund_share = Decimal(payload.funding_share_pct)
    except InvalidOperation as exc:
        raise unprocessable("FUNDING_SHARE_INVALID", "Funding share must be a valid decimal string.") from exc

    view = goals_service.create_goal(
        session=session,
        clock=clock,
        principal=principal,
        customer_id=customer_id,
        name=payload.name,
        goal_type=payload.goal_type,
        target_amount=tgt_amount,
        target_date=payload.target_date,
        priority=payload.priority,
        funding_share_pct=fund_share,
    )
    return _to_goal_out(view)


@router.get("", response_model=list[GoalOut])
def list_goals(
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
) -> list[GoalOut]:
    """List goals for authenticated customer in priority order (AC-03.2)."""
    customer_id = customer_id_for(session, principal)
    views = goals_service.list_goals(session, customer_id)
    return [_to_goal_out(v) for v in views]


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(
    goal_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
) -> GoalOut:
    """Get specific goal with progress (AC-03, AC-08)."""
    customer_id = customer_id_for(session, principal)
    view = goals_service.get_goal(session, customer_id, goal_id)
    return _to_goal_out(view)


@router.put("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: str,
    payload: GoalCreateIn,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GoalOut:
    """Update goal fields and recompute progress (AC-03)."""
    require_decimal_strings(payload.model_dump())
    customer_id = customer_id_for(session, principal)

    try:
        tgt_amount = Decimal(payload.target_amount)
    except InvalidOperation as exc:
        raise unprocessable("TARGET_AMOUNT_INVALID", "Target amount must be a valid decimal string.") from exc

    try:
        fund_share = Decimal(payload.funding_share_pct)
    except InvalidOperation as exc:
        raise unprocessable("FUNDING_SHARE_INVALID", "Funding share must be a valid decimal string.") from exc

    view = goals_service.update_goal(
        session=session,
        clock=clock,
        principal=principal,
        customer_id=customer_id,
        goal_id=goal_id,
        name=payload.name,
        goal_type=payload.goal_type,
        target_amount=tgt_amount,
        target_date=payload.target_date,
        priority=payload.priority,
        funding_share_pct=fund_share,
    )
    return _to_goal_out(view)


@router.get("/{goal_id}/progress", response_model=GoalProgressHistoryOut)
def get_goal_progress_history(
    goal_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER))],
    session: Annotated[Session, Depends(get_db)],
) -> GoalProgressHistoryOut:
    """Get snapshot progress history for a goal, newest first (AC-08)."""
    customer_id = customer_id_for(session, principal)
    res = goals_service.get_goal_progress(session, customer_id, goal_id)

    def _to_prog_out(p: goals_service.GoalProgressView | None) -> GoalProgressOut | None:
        if p is None:
            return None
        return GoalProgressOut(
            nav_date=p.nav_date,
            current_goal_value=fmt2(p.current_goal_value) or "0.00",
            percent_complete=fmt2(p.percent_complete) or "0.00",
            status=p.status,
            reason=p.reason,
            created_at=p.created_at,
        )

    latest_out = _to_prog_out(res.latest)
    history_out = [_to_prog_out(h) for h in res.history if h is not None]
    return GoalProgressHistoryOut(latest=latest_out, history=history_out)  # type: ignore[arg-type]
