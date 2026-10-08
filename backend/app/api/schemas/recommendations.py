"""Recommendation request/response models (recommendation_spec §4). Field names match the spec table exactly.

Percentages are serialised as fixed-scale 2 dp JSON strings ("5.00"), never numbers (NFR-01).
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.domain.bands import RiskBand
from app.domain.money import q2


def pct(value: Decimal) -> str:
    """A percentage as a fixed 2 dp string."""
    return f"{q2(value):f}"


class RecommendationIn(BaseModel):
    goal_id: UUID | None = None


class AllocationRowOut(BaseModel):
    asset_class: str
    target_pct: str


class RecommendationOut(BaseModel):
    id: str
    source: str
    risk_band: RiskBand
    template_version_no: int
    goal_id: str | None
    horizon_months: int | None
    horizon_rule: str
    as_of_date: date
    allocation: list[AllocationRowOut]
    total_pct: str
    created_at: datetime
