"""AC-02 / AC-04 — band → template, horizon shift and the exact-100.00 invariant (recommendation_spec §2.1-2.5)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.fixtures.policy_definitions import ASSET_CLASSES, template_v1

from app.domain.allocation.templates import AllocationSumError
from app.domain.allocation_template_policy import Allocation, RecommendationResult, recommend
from app.domain.bands import BAND_ORDER, RiskBand
from app.domain.template_version_validator import TemplateVersionDefinition, parse_template_version

SWEEP_MONTHS = (0, 1, 11, 12, 35, 36, 59, 60, 83, 84, 240)


def _v1() -> TemplateVersionDefinition:
    return parse_template_version(template_v1(), ASSET_CLASSES)


def _expected(values: tuple[str, str, str, str]) -> tuple[tuple[str, Decimal], ...]:
    return tuple(zip(ASSET_CLASSES, (Decimal(v) for v in values), strict=True))


# ---------------------------------------------------------------- AC-02.1 / AC-02.2: v1 rows, no goal


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("band", "expected"),
    [
        (RiskBand.CONSERVATIVE, ("20.00", "60.00", "10.00", "10.00")),
        (RiskBand.MODERATE, ("50.00", "35.00", "10.00", "5.00")),
        (RiskBand.AGGRESSIVE, ("75.00", "15.00", "7.50", "2.50")),
    ],
)
def test_ac_02_no_goal_returns_v1_template_row(band: RiskBand, expected: tuple[str, str, str, str]) -> None:
    """AC-02.1 / AC-02.2 — with no goal each band gets its §2.1 v1 row exactly, rule NO_GOAL, total 100.00."""
    result = recommend(band, _v1(), None, ASSET_CLASSES)

    assert result.band == band
    assert result.allocation == _expected(expected)
    assert result.horizon_rule == "NO_GOAL"
    assert result.horizon_months is None
    assert result.total == Decimal("100.00")


# ---------------------------------------------------------------- AC-02.3: sum invariant sweep


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize("band", BAND_ORDER)
@pytest.mark.parametrize("months", [*SWEEP_MONTHS, None])
def test_ac_02_every_band_and_horizon_sums_to_exactly_100(band: RiskBand, months: int | None) -> None:
    """AC-02.3 — every band × months {0,1,11,12,35,36,59,60,83,84,240}: one row per class, none < 0, Σ == 100.00."""
    result = recommend(band, _v1(), months, ASSET_CLASSES)

    assert [cls for cls, _ in result.allocation] == list(ASSET_CLASSES)
    for _, pct in result.allocation:
        assert pct >= Decimal("0.00")
        assert pct == pct.quantize(Decimal("0.01"))
    assert sum((pct for _, pct in result.allocation), Decimal("0")) == Decimal("100.00")
    assert result.total == Decimal("100.00")


# ---------------------------------------------------------------- AC-02.4: invariant guard


def _moderate_99_99() -> TemplateVersionDefinition:
    v1 = _v1()
    templates = {band: dict(row) for band, row in v1.templates.items()}
    templates[RiskBand.MODERATE]["CASH"] = Decimal("4.99")
    return TemplateVersionDefinition(templates, v1.horizon_rules, v1.drift_threshold_pct)


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize("months", [None, 48])
def test_ac_02_template_row_summing_to_99_99_raises_allocation_sum_error(months: int | None) -> None:
    """AC-02.4 — a MODERATE row summing to 99.99 raises AllocationSumError (nothing returned to persist)."""
    with pytest.raises(AllocationSumError, match="MODERATE sum=99.99"):
        recommend(RiskBand.MODERATE, _moderate_99_99(), months, ASSET_CLASSES)


@pytest.mark.ac("AC-02")
def test_ac_02_template_row_missing_an_asset_class_raises_allocation_sum_error() -> None:
    """AC-02.4 — §2.4: exactly one row per asset class; a row missing CASH is rejected."""
    v1 = _v1()
    templates = {band: dict(row) for band, row in v1.templates.items()}
    del templates[RiskBand.MODERATE]["CASH"]
    templates[RiskBand.MODERATE]["DEBT"] = Decimal("40.00")
    definition = TemplateVersionDefinition(templates, v1.horizon_rules, v1.drift_threshold_pct)

    with pytest.raises(AllocationSumError, match="MODERATE asset classes"):
        recommend(RiskBand.MODERATE, definition, None, ASSET_CLASSES)


@pytest.mark.ac("AC-02")
def test_ac_02_template_value_with_more_than_two_decimals_raises_allocation_sum_error() -> None:
    """AC-02.4 — §2.4: each target_pct has 2 dp; 4.995 is rejected even though the row sums to 100.00."""
    v1 = _v1()
    templates = {band: dict(row) for band, row in v1.templates.items()}
    templates[RiskBand.MODERATE]["CASH"] = Decimal("4.995")
    templates[RiskBand.MODERATE]["GOLD"] = Decimal("10.005")
    definition = TemplateVersionDefinition(templates, v1.horizon_rules, v1.drift_threshold_pct)

    with pytest.raises(AllocationSumError, match="more than 2 decimal places"):
        recommend(RiskBand.MODERATE, definition, None, ASSET_CLASSES)


# ---------------------------------------------------------------- AC-04.1 / AC-04.2: worked examples


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize(
    ("band", "months", "rule", "expected"),
    [
        (RiskBand.MODERATE, 120, "H_84_PLUS", ("50.00", "35.00", "10.00", "5.00")),
        (RiskBand.MODERATE, 48, "H_36_59", ("30.00", "55.00", "10.00", "5.00")),
        (RiskBand.AGGRESSIVE, 24, "H_12_35", ("45.00", "45.00", "7.50", "2.50")),
        (RiskBand.CONSERVATIVE, 24, "H_12_35", ("0.00", "80.00", "10.00", "10.00")),
        (RiskBand.AGGRESSIVE, 6, "H_0_11", ("0.00", "15.00", "7.50", "77.50")),
    ],
)
def test_ac_04_worked_examples(band: RiskBand, months: int, rule: str, expected: tuple[str, str, str, str]) -> None:
    """AC-04.2 — recommendation_spec §2.3 rows reproduced exactly (incl. CONSERVATIVE/24 shift capped at 20.00)."""
    result = recommend(band, _v1(), months, ASSET_CLASSES)

    assert result.allocation == _expected(expected)
    assert result.horizon_rule == rule
    assert result.horizon_months == months
    assert result.total == Decimal("100.00")


@pytest.mark.ac("AC-04")
def test_ac_04_moderate_48_month_goal_moves_20_points_equity_to_debt() -> None:
    """AC-04.1 — MODERATE, clock 2026-01-15, goal 2030-01-15 (48 months) → 30/55/10/5, H_36_59."""
    result = recommend(RiskBand.MODERATE, _v1(), 48, ASSET_CLASSES)

    assert dict(result.allocation) == {
        "EQUITY": Decimal("30.00"),
        "DEBT": Decimal("55.00"),
        "GOLD": Decimal("10.00"),
        "CASH": Decimal("5.00"),
    }
    assert result.horizon_rule == "H_36_59"


@pytest.mark.ac("AC-04")
def test_ac_04_primary_goal_29_months_moderate() -> None:
    """AC-04.3 — primary goal B at 29 months → H_12_35; MODERATE 50-30 → 20/65/10/5."""
    result = recommend(RiskBand.MODERATE, _v1(), 29, ASSET_CLASSES)

    assert result.allocation == _expected(("20.00", "65.00", "10.00", "5.00"))
    assert result.horizon_rule == "H_12_35"


@pytest.mark.ac("AC-04")
def test_ac_04_allocation_follows_requested_asset_class_order() -> None:
    """AC-04.2 — allocation rows come back in the active asset-class order given by the caller."""
    order = ("CASH", "GOLD", "DEBT", "EQUITY")

    result = recommend(RiskBand.MODERATE, _v1(), 48, order)

    assert result.allocation == (
        ("CASH", Decimal("5.00")),
        ("GOLD", Decimal("10.00")),
        ("DEBT", Decimal("55.00")),
        ("EQUITY", Decimal("30.00")),
    )


# ---------------------------------------------------------------- AC-04.4: determinism


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize("band", BAND_ORDER)
@pytest.mark.parametrize("months", [None, 6, 24, 48, 120])
def test_ac_04_recommend_is_deterministic(band: RiskBand, months: int | None) -> None:
    """AC-04.4 — same band, template version and horizon → equal results, repeated; inputs not mutated."""
    definition = _v1()
    before = {b: dict(row) for b, row in definition.templates.items()}

    results = [recommend(band, definition, months, ASSET_CLASSES) for _ in range(50)]

    assert all(r == results[0] for r in results)
    assert all(repr(r) == repr(results[0]) for r in results)
    assert recommend(band, _v1(), months, ASSET_CLASSES) == results[0]
    assert definition.templates == before


@pytest.mark.ac("AC-04")
def test_ac_04_result_is_an_immutable_value_object() -> None:
    """AC-04.4 — the result is a frozen value object; Allocation is its public alias."""
    result = recommend(RiskBand.MODERATE, _v1(), None, ASSET_CLASSES)

    assert Allocation is RecommendationResult
    with pytest.raises(AttributeError):
        result.horizon_rule = "H_0_11"  # type: ignore[misc]
