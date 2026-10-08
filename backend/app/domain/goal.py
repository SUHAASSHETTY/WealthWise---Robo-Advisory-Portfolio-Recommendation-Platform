"""Goal value object used by horizon and ordering rules (goal_tracker_spec §2.1)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class GoalType(StrEnum):
    RETIREMENT = "RETIREMENT"
    EDUCATION = "EDUCATION"
    HOME = "HOME"
    OTHER = "OTHER"


@dataclass(frozen=True)
class GoalSnapshot:
    id: str
    priority: int
    target_date: date
    target_amount: Decimal
    created_at: datetime
