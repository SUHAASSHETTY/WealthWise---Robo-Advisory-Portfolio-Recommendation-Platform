"""AC-02 — allocation templates: every band's percentages sum to exactly 100.00 (recommendation_spec §2.1, §2.4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.allocation.templates import AllocationSumError, parse_template_set

V1_TEMPLATES = {
    "CONSERVATIVE": {"EQUITY": "20.00", "DEBT": "60.00", "GOLD": "10.00", "CASH": "10.00"},
    "MODERATE": {"EQUITY": "50.00", "DEBT": "35.00", "GOLD": "10.00", "CASH": "5.00"},
    "AGGRESSIVE": {"EQUITY": "75.00", "DEBT": "15.00", "GOLD": "7.50", "CASH": "2.50"},
}


def _with(band: str, asset_class: str, value: object) -> dict[str, dict[str, object]]:
    templates: dict[str, dict[str, object]] = {b: dict(row) for b, row in V1_TEMPLATES.items()}
    templates[band][asset_class] = value
    return templates


@pytest.mark.ac("AC-02")
def test_ac_02_v1_templates_parse_to_exact_decimals_summing_to_100() -> None:
    """AC-02.3 — every v1 band sums to exactly Decimal('100.00')."""
    parsed = parse_template_set(V1_TEMPLATES)

    assert parsed["AGGRESSIVE"]["GOLD"] == Decimal("7.50")
    for band, allocation in parsed.items():
        assert sum(allocation.values()) == Decimal("100.00"), band


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("band", "asset_class", "value", "message"),
    [
        ("MODERATE", "CASH", "4.99", "MODERATE sum=99.99"),
        ("AGGRESSIVE", "GOLD", "7.51", "AGGRESSIVE sum=100.01"),
    ],
)
def test_ac_02_corrupted_template_raises_allocation_sum_error(
    band: str, asset_class: str, value: str, message: str
) -> None:
    """AC-02.4 — a template row that does not sum to 100.00 is rejected."""
    with pytest.raises(AllocationSumError, match=message):
        parse_template_set(_with(band, asset_class, value))


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("value", "message"),
    [("-5.00", "outside"), ("100.01", "outside"), ("7.505", "2 decimal places")],
)
def test_ac_02_each_percentage_must_be_two_dp_within_0_and_100(value: str, message: str) -> None:
    """AC-02.3 — no target_pct is negative, above 100, or finer than 2 dp."""
    with pytest.raises(AllocationSumError, match=message):
        parse_template_set(_with("CONSERVATIVE", "EQUITY", value))


@pytest.mark.ac("AC-02")
def test_ac_02_float_percentage_is_rejected() -> None:
    """NFR-01 — template values must be decimal strings, never floats."""
    with pytest.raises(TypeError):
        parse_template_set(_with("AGGRESSIVE", "GOLD", 7.5))


@pytest.mark.ac("AC-02")
def test_ac_02_empty_band_is_rejected() -> None:
    """AC-02.3 — a band with no allocation rows cannot sum to 100.00."""
    with pytest.raises(AllocationSumError, match="CONSERVATIVE sum=0.00"):
        parse_template_set({**V1_TEMPLATES, "CONSERVATIVE": {}})
