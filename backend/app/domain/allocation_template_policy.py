"""Band → template allocation with the goal-horizon shift (recommendation_spec §2.1-2.5, AC-02, AC-04).

`recommend` is pure: every percentage comes from the template version passed in (no module-level policy values),
the shift moves `min(rule.shift, alloc[from])` points (or all of them for "ALL"), and the result is re-validated
against the exact-100.00 invariant before it is returned (NFR-08).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.allocation.templates import AllocationSumError, parse_percentage, validate_allocation
from app.domain.bands import RiskBand
from app.domain.goal_horizon_policy import select_rule
from app.domain.template_version_validator import TemplateVersionDefinition

NO_GOAL = "NO_GOAL"


@dataclass(frozen=True)
class RecommendationResult:
    """A target allocation: one (asset_class, target_pct) row per class, in the requested order."""

    band: RiskBand
    allocation: tuple[tuple[str, Decimal], ...]
    horizon_months: int | None
    horizon_rule: str
    total: Decimal


Allocation = RecommendationResult


def recommend(
    band: RiskBand,
    definition: TemplateVersionDefinition,
    horizon_months: int | None,
    asset_class_order: Sequence[str],
) -> RecommendationResult:
    """Apply the horizon rule to the band's template row; raise AllocationSumError if any invariant breaks."""
    alloc = dict(definition.templates[band])
    if sorted(alloc) != sorted(asset_class_order):
        raise AllocationSumError(f"{band.value} asset classes {sorted(alloc)} != active {sorted(asset_class_order)}")

    rule = select_rule(definition.horizon_rules, horizon_months)
    if rule is not None:
        available = alloc[rule.from_class]
        amount = available if rule.shift is None else min(rule.shift, available)
        alloc[rule.from_class] = available - amount
        alloc[rule.to_class] = alloc[rule.to_class] + amount

    rows = tuple((cls, parse_percentage(band.value, cls, alloc[cls])) for cls in asset_class_order)
    validate_allocation(band.value, dict(rows))
    return RecommendationResult(
        band=band,
        allocation=rows,
        horizon_months=horizon_months,
        horizon_rule=NO_GOAL if rule is None else rule.code,
        total=sum((pct for _, pct in rows), Decimal("0")),
    )
