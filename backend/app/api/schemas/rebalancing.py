"""Schemas for Rebalancing API (rebalancing_spec §4, AC-06, AC-07)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.money import q2


def fmt2(val: Decimal | None) -> str | None:
    if val is None:
        return None
    return f"{q2(val):.2f}"


def fmt4(val: Decimal | None) -> str | None:
    if val is None:
        return None
    return f"{val:.4f}"


class RebalanceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_class: str
    current_value: str
    current_pct: str | None = None
    target_pct: str | None = None
    drift_pct: str | None = None
    target_value: str | None = None
    nav: str
    action: str
    quantity: str | None = None
    trade_value: str | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: str
    actor_role: str
    created_at: datetime
    reason: str | None = None


class RebalanceProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    nav_date: date
    status: str
    total_value: str
    drift_threshold_pct: str
    post_trade_cash: str
    created_at: datetime
    lines: list[RebalanceLineOut] = Field(default_factory=list)
    decision: DecisionOut | None = None


class RebalanceSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    nav_date: date
    created_at: datetime


class StubOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_class: str
    side: str
    quantity: str
    trade_value: str
    status: str


class AcceptProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    orders: list[StubOrderOut] = Field(default_factory=list)


class DismissIn(BaseModel):
    reason: str | None = None


class DismissProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
