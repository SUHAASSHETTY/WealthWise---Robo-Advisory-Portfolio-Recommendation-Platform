"""Schemas for Goals API (goal_tracker_spec §4, AC-03, AC-08)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.money import q2


def fmt2(val: Decimal | None) -> str | None:
    if val is None:
        return None
    return f"{q2(val):.2f}"


class GoalCreateIn(BaseModel):
    name: str
    goal_type: str
    target_amount: str
    target_date: date
    priority: int
    funding_share_pct: str


class GoalProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nav_date: date
    current_goal_value: str
    percent_complete: str
    status: str
    reason: str | None = None
    created_at: datetime | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    name: str
    goal_type: str
    target_amount: str
    target_date: date
    priority: int
    funding_share_pct: str
    created_at: datetime
    updated_at: datetime
    progress: GoalProgressOut | None = None


class GoalProgressHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latest: GoalProgressOut | None
    history: list[GoalProgressOut] = Field(default_factory=list)
