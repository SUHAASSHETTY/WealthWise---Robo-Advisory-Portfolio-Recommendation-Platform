"""Unit tests for advisor override and manual recommendation rules (advisor_workbench_spec §2, AC-09)."""

from decimal import Decimal

import pytest

from app.domain.advisor_override_rules import (
    AdvisorRuleValidationError,
    OverrideReasonCode,
    validate_manual_recommendation,
    validate_risk_override,
)
from app.domain.bands import RiskBand


@pytest.mark.ac("AC-09")
def test_ac_09_1_validate_valid_risk_override() -> None:
    """AC-09.1: Valid risk override passes validation."""
    validate_risk_override(
        current_band=RiskBand.MODERATE,
        new_band=RiskBand.CONSERVATIVE,
        reason_code=OverrideReasonCode.CLIENT_CIRCUMSTANCES_CHANGED,
        note="Client retiring in 18 months; needs capital stability.",
    )


@pytest.mark.ac("AC-09")
def test_ac_09_3_and_09_4_override_validation_errors() -> None:
    """AC-09.3 / AC-09.4: Same band, invalid reason, and note length validations."""
    # Same band
    with pytest.raises(AdvisorRuleValidationError) as exc1:
        validate_risk_override(
            current_band=RiskBand.MODERATE,
            new_band=RiskBand.MODERATE,
            reason_code=OverrideReasonCode.SUITABILITY_REVIEW,
            note="Valid note exceeding 20 characters long.",
        )
    assert exc1.value.code == "OVERRIDE_SAME_BAND"

    # Invalid note (too short < 20 chars)
    with pytest.raises(AdvisorRuleValidationError) as exc2:
        validate_risk_override(
            current_band=RiskBand.MODERATE,
            new_band=RiskBand.CONSERVATIVE,
            reason_code=OverrideReasonCode.SUITABILITY_REVIEW,
            note="Client asked",  # 12 chars
        )
    assert exc2.value.code == "OVERRIDE_NOTE_INVALID"

    # Invalid reason code
    with pytest.raises(AdvisorRuleValidationError) as exc3:
        validate_risk_override(
            current_band=RiskBand.MODERATE,
            new_band=RiskBand.CONSERVATIVE,
            reason_code="INVALID_REASON",
            note="Valid note exceeding 20 characters long.",
        )
    assert exc3.value.code == "REASON_CODE_INVALID"


@pytest.mark.ac("AC-09")
def test_ac_09_8_validate_manual_recommendation() -> None:
    """AC-09.8: Valid manual recommendation sums to 100.00% across all active classes."""
    active_classes = ["EQUITY", "DEBT", "GOLD", "CASH"]
    valid_alloc = [
        {"asset_class": "EQUITY", "target_pct": Decimal("40.00")},
        {"asset_class": "DEBT", "target_pct": Decimal("40.00")},
        {"asset_class": "GOLD", "target_pct": Decimal("10.00")},
        {"asset_class": "CASH", "target_pct": Decimal("10.00")},
    ]
    validate_manual_recommendation(
        allocation=valid_alloc,
        active_classes=active_classes,
        note="Custom allocation tailored to client tax and liquidity requirements.",
    )

    # Invalid sum (99.99)
    bad_sum_alloc = [
        {"asset_class": "EQUITY", "target_pct": Decimal("39.99")},
        {"asset_class": "DEBT", "target_pct": Decimal("40.00")},
        {"asset_class": "GOLD", "target_pct": Decimal("10.00")},
        {"asset_class": "CASH", "target_pct": Decimal("10.00")},
    ]
    with pytest.raises(AdvisorRuleValidationError) as exc:
        validate_manual_recommendation(
            allocation=bad_sum_alloc,
            active_classes=active_classes,
            note="Custom allocation tailored to client tax and liquidity requirements.",
        )
    assert exc.value.code == "ALLOCATION_SUM_INVALID"

    # Missing class
    missing_alloc = [
        {"asset_class": "EQUITY", "target_pct": Decimal("50.00")},
        {"asset_class": "DEBT", "target_pct": Decimal("50.00")},
    ]
    with pytest.raises(AdvisorRuleValidationError) as exc2:
        validate_manual_recommendation(
            allocation=missing_alloc,
            active_classes=active_classes,
            note="Custom allocation tailored to client tax and liquidity requirements.",
        )
    assert exc2.value.code == "ALLOCATION_CLASSES_INVALID"

    # Percentage out of range
    invalid_pct_alloc = [
        {"asset_class": "EQUITY", "target_pct": Decimal("110.00")},
        {"asset_class": "DEBT", "target_pct": Decimal("-10.00")},
        {"asset_class": "GOLD", "target_pct": Decimal("0.00")},
        {"asset_class": "CASH", "target_pct": Decimal("0.00")},
    ]
    with pytest.raises(AdvisorRuleValidationError) as exc3:
        validate_manual_recommendation(
            allocation=invalid_pct_alloc,
            active_classes=active_classes,
            note="Custom allocation tailored to client tax and liquidity requirements.",
        )
    assert exc3.value.code == "ALLOCATION_PERCENT_INVALID"

    # Note too long / invalid
    with pytest.raises(AdvisorRuleValidationError) as exc4:
        validate_manual_recommendation(
            allocation=valid_alloc,
            active_classes=active_classes,
            note="x" * 1001,
        )
    assert exc4.value.code == "RECOMMENDATION_NOTE_INVALID"

    # Invalid band string in override
    with pytest.raises(AdvisorRuleValidationError) as exc5:
        validate_risk_override(
            current_band="UNKNOWN",
            new_band=RiskBand.CONSERVATIVE,
            reason_code=OverrideReasonCode.SUITABILITY_REVIEW,
            note="Valid note exceeding 20 characters long.",
        )
    assert exc5.value.code == "BAND_INVALID"

    with pytest.raises(AdvisorRuleValidationError) as exc6:
        validate_risk_override(
            current_band=RiskBand.MODERATE,
            new_band="UNKNOWN",
            reason_code=OverrideReasonCode.SUITABILITY_REVIEW,
            note="Valid note exceeding 20 characters long.",
        )
    assert exc6.value.code == "BAND_INVALID"
