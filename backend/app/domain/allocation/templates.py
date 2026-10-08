"""Allocation templates (recommendation_spec §2.1, §2.4): every band sums to exactly 100.00 (AC-02, NFR-08)."""

from collections.abc import Mapping
from decimal import Decimal

from app.domain.money import CENT, HUNDRED, q2, to_decimal

ZERO = Decimal("0")
PercentInput = str | int | Decimal


class AllocationSumError(ValueError):
    """An allocation violates the exact-100.00 invariant."""


def parse_percentage(band: str, asset_class: str, raw: PercentInput) -> Decimal:
    """A target percentage: decimal (never float), at most 2 dp, within [0.00, 100.00]."""
    value = to_decimal(raw)
    if value != value.quantize(CENT):
        raise AllocationSumError(f"{band} {asset_class}={raw} has more than 2 decimal places")
    if not ZERO <= value <= HUNDRED:
        raise AllocationSumError(f"{band} {asset_class}={raw} is outside [0.00, 100.00]")
    return value


def validate_allocation(band: str, allocation: Mapping[str, Decimal]) -> None:
    """Raise unless the allocation sums to exactly Decimal('100.00')."""
    total = sum(allocation.values(), ZERO)
    if total != HUNDRED:
        raise AllocationSumError(f"{band} sum={q2(total)}, expected exactly 100.00")


def parse_template_set(templates: Mapping[str, Mapping[str, PercentInput]]) -> dict[str, dict[str, Decimal]]:
    """Parse every band of a template definition and enforce the exact-100.00 invariant."""
    parsed: dict[str, dict[str, Decimal]] = {}
    for band, row in templates.items():
        allocation = {asset_class: parse_percentage(band, asset_class, raw) for asset_class, raw in row.items()}
        validate_allocation(band, allocation)
        parsed[band] = allocation
    return parsed
