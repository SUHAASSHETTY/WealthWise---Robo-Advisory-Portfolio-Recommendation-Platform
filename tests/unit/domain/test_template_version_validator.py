"""AC-10.1 / AC-10.4 — publish validation of template and risk-policy definitions (admin_versioning_spec §2.2-2.3)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from tests.fixtures.policy_definitions import (
    ASSET_CLASSES,
    V1_POINTS,
    risk_policy_v1,
    risk_policy_v2_ac_10_1,
    template_v1,
    template_with,
)

from app.domain.bands import RiskBand, min_band
from app.domain.template_version_validator import (
    PolicyInvalid,
    parse_risk_policy,
    parse_template_version,
    validate_risk_policy,
    validate_template_version,
)


@pytest.mark.ac("AC-10")
def test_ac_10_v1_template_is_valid_and_parses_to_exact_decimals() -> None:
    """AC-10.1 — the seeded v1 template passes publish validation."""
    assert validate_template_version(template_v1(), ASSET_CLASSES) == []
    parsed = parse_template_version(template_v1(), ASSET_CLASSES)

    assert parsed.templates[RiskBand.AGGRESSIVE]["GOLD"] == Decimal("7.50")
    assert parsed.drift_threshold_pct == Decimal("5.00")
    assert [rule.code for rule in parsed.horizon_rules][0] == "H_84_PLUS"
    assert parsed.horizon_rules[-1].shift is None  # "ALL"


@pytest.mark.ac("AC-10")
def test_ac_10_aggressive_row_summing_to_100_01_names_band_and_sum() -> None:
    """AC-10.4 — publish validation names AGGRESSIVE and sum=100.01."""
    violations = validate_template_version(template_with("AGGRESSIVE", "GOLD", "7.51"), ASSET_CLASSES)

    assert any("AGGRESSIVE" in v and "sum=100.01" in v for v in violations), violations
    with pytest.raises(PolicyInvalid) as excinfo:
        parse_template_version(template_with("AGGRESSIVE", "GOLD", "7.51"), ASSET_CLASSES)
    assert excinfo.value.violations == violations


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda d: d["templates"].pop("MODERATE"), "MODERATE missing"),
        (lambda d: d["templates"]["CONSERVATIVE"].pop("CASH"), "CONSERVATIVE asset classes"),
        (lambda d: d.__setitem__("drift_threshold_pct", "0.00"), "drift_threshold_pct"),
        (lambda d: d.__setitem__("drift_threshold_pct", "50.01"), "drift_threshold_pct"),
        (lambda d: d.__setitem__("drift_threshold_pct", 5.0), "decimal string"),
        (lambda d: d["templates"]["MODERATE"].__setitem__("EQUITY", 50.0), "decimal string"),
        (lambda d: d["horizon_rules"].pop(2), "contiguous"),
        (lambda d: d["horizon_rules"][1].__setitem__("to", "EQUITY"), "from and to"),
        (lambda d: d["horizon_rules"][1].__setitem__("shift", "100.01"), "shift"),
    ],
)
def test_ac_10_template_publish_rules(mutate: Any, expected: str) -> None:
    """AC-10.4 — every template publish rule of admin_versioning §2.3 is enforced."""
    definition = template_v1()
    mutate(definition)

    violations = validate_template_version(definition, ASSET_CLASSES)

    assert any(expected in v for v in violations), violations


@pytest.mark.ac("AC-10")
def test_ac_10_v1_risk_policy_is_valid_with_spec_points() -> None:
    """AC-10.1 — the seeded v1 risk policy passes validation; points match risk_profile §2.1."""
    assert validate_risk_policy(risk_policy_v1()) == []
    parsed = parse_risk_policy(risk_policy_v1())

    assert [q.code for q in parsed.questions] == list(V1_POINTS)
    assert {q.code: {o.code: o.points for o in q.options} for q in parsed.questions} == V1_POINTS
    assert parsed.max_score == 28
    assert [(b.band, b.min_score, b.max_score) for b in parsed.bands] == [
        (RiskBand.CONSERVATIVE, 0, 11),
        (RiskBand.MODERATE, 12, 20),
        (RiskBand.AGGRESSIVE, 21, 28),
    ]
    assert parsed.caps[0].max_band == RiskBand.MODERATE


@pytest.mark.ac("AC-10")
def test_ac_10_v2_risk_policy_with_moved_thresholds_is_valid() -> None:
    """AC-10.1 — v2 (MODERATE 12-19, AGGRESSIVE 20-28) is publishable."""
    assert validate_risk_policy(risk_policy_v2_ac_10_1()) == []


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda d: d.__setitem__("questions", d["questions"][:5]), "at least 6 questions"),
        (lambda d: d["questions"][1].__setitem__("code", "AGE"), "duplicate question code"),
        (lambda d: d["questions"][0]["options"][0].__setitem__("points", 11), "points"),
        (lambda d: d["questions"][0].__setitem__("options", d["questions"][0]["options"][:1]), "2-6 options"),
        (lambda d: d["bands"][1].__setitem__("min_score", 13), "contiguous"),
        (lambda d: d["bands"][2].__setitem__("max_score", 27), "maximum achievable score 28"),
        (lambda d: d["caps"][0].__setitem__("option_code", "NOPE"), "cap NO_EMERGENCY_FUND"),
    ],
)
def test_ac_10_risk_policy_publish_rules(mutate: Any, expected: str) -> None:
    """AC-10.4 analogue for risk policies — admin_versioning §2.2 publish validation."""
    definition = risk_policy_v1()
    mutate(definition)

    violations = validate_risk_policy(definition)

    assert any(expected in v for v in violations), violations


def test_band_order_and_min_band() -> None:
    assert min_band(RiskBand.AGGRESSIVE, RiskBand.MODERATE) == RiskBand.MODERATE
    assert min_band(RiskBand.CONSERVATIVE, RiskBand.MODERATE) == RiskBand.CONSERVATIVE
    assert sorted([RiskBand.AGGRESSIVE, RiskBand.CONSERVATIVE, RiskBand.MODERATE]) == [
        RiskBand.CONSERVATIVE,
        RiskBand.MODERATE,
        RiskBand.AGGRESSIVE,
    ]
