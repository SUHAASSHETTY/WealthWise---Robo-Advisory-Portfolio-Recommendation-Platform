"""Schemas for holdings and drift responses (holdings_spec §4)."""

from datetime import date
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


class HoldingLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_class: str
    units: str
    nav: str
    current_value: str
    current_pct: str | None = None
    target_pct: str | None = None
    drift_pct: str | None = None
    breached: bool | None = None


class HoldingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nav_date: date
    total_value: str
    has_target: bool
    recommendation_id: str | None = None
    template_version_no: int | None = None
    drift_threshold_pct: str | None = None
    portfolio_breached: bool
    lines: list[HoldingLineResponse] = Field(default_factory=list)
