"""Advisor domain rules: risk band override & manual recommendation validation (advisor_workbench_spec §2, AC-09)."""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import StrEnum

from app.domain.bands import RiskBand


class OverrideReasonCode(StrEnum):
    CLIENT_CIRCUMSTANCES_CHANGED = "CLIENT_CIRCUMSTANCES_CHANGED"
    QUESTIONNAIRE_MISUNDERSTOOD = "QUESTIONNAIRE_MISUNDERSTOOD"
    SUITABILITY_REVIEW = "SUITABILITY_REVIEW"
    OTHER = "OTHER"


class AdvisorRuleValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_risk_override(
    current_band: RiskBand | str,
    new_band: RiskBand | str,
    reason_code: OverrideReasonCode | str,
    note: str,
) -> None:
    """Validate advisor risk band override fields (AC-09.1–09.4)."""
    try:
        parsed_new_band = RiskBand(new_band)
    except ValueError:
        raise AdvisorRuleValidationError("BAND_INVALID", f"Invalid risk band: {new_band}") from None

    try:
        parsed_current_band = RiskBand(current_band)
    except ValueError:
        raise AdvisorRuleValidationError("BAND_INVALID", f"Invalid current risk band: {current_band}") from None

    if parsed_new_band == parsed_current_band:
        raise AdvisorRuleValidationError(
            "OVERRIDE_SAME_BAND", "New band must be different from current effective band."
        )

    try:
        OverrideReasonCode(reason_code)
    except ValueError:
        raise AdvisorRuleValidationError("REASON_CODE_INVALID", f"Invalid reason code: {reason_code}") from None

    trimmed_note = note.strip() if note else ""
    if len(trimmed_note) < 20 or len(trimmed_note) > 1000:
        raise AdvisorRuleValidationError(
            "OVERRIDE_NOTE_INVALID", "Override note must be between 20 and 1000 characters."
        )


def validate_manual_recommendation(
    allocation: Sequence[Mapping[str, object]],
    active_classes: Sequence[str],
    note: str,
) -> None:
    """Validate advisor manual recommendation allocation and note (AC-09.8)."""
    trimmed_note = note.strip() if note else ""
    if len(trimmed_note) < 20 or len(trimmed_note) > 1000:
        raise AdvisorRuleValidationError(
            "RECOMMENDATION_NOTE_INVALID", "Recommendation note must be between 20 and 1000 characters."
        )

    alloc_classes = [str(item["asset_class"]) for item in allocation]
    if sorted(alloc_classes) != sorted(active_classes) or len(alloc_classes) != len(set(alloc_classes)):
        raise AdvisorRuleValidationError(
            "ALLOCATION_CLASSES_INVALID", "Allocation must specify every active asset class exactly once."
        )

    total_sum = Decimal("0.00")
    for item in allocation:
        pct = Decimal(str(item["target_pct"]))
        if pct < Decimal("0.00") or pct > Decimal("100.00"):
            raise AdvisorRuleValidationError(
                "ALLOCATION_PERCENT_INVALID", f"Target percentage {pct} must be between 0.00 and 100.00."
            )
        total_sum += pct

    if total_sum != Decimal("100.00"):
        raise AdvisorRuleValidationError(
            "ALLOCATION_SUM_INVALID", f"Allocation percentages must sum to exactly 100.00% (got {total_sum}%)."
        )
