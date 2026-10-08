"""E2-S1: deterministic risk scoring rules (risk_profile_spec §2, AC-01.2-AC-01.7; AC-10.6 domain half).

Expected values are copied verbatim from risk_profile_spec §5 and specs/stories/E2-S1.md; none are recomputed.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest
from tests.fixtures.answer_sets import (
    ANS_0,
    ANS_11,
    ANS_12,
    ANS_16,
    ANS_20,
    ANS_21,
    ANS_28,
    ANS_CAP24,
    AnswerSet,
    replaced,
    without,
)
from tests.fixtures.policy_definitions import risk_policy_v1, risk_policy_v2_ac_10_1

from app.domain.bands import RiskBand
from app.domain.risk_band_rules import (
    Answer,
    AssessmentEvent,
    AssessmentResult,
    AssessmentValidationError,
    EffectiveBand,
    OverrideEvent,
    apply_caps,
    assess,
    band_for_score,
    effective_band,
    score_answers,
    sorted_by_question_order,
)
from app.domain.template_version_validator import RiskPolicyDefinition, parse_risk_policy

C, M, A = RiskBand.CONSERVATIVE, RiskBand.MODERATE, RiskBand.AGGRESSIVE
T0 = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
T1 = datetime(2026, 1, 15, 9, 5, tzinfo=UTC)


@pytest.fixture(scope="module")
def v1() -> RiskPolicyDefinition:
    return parse_risk_policy(risk_policy_v1())


def _answers(answer_set: AnswerSet) -> list[Answer]:
    return [Answer(q, o) for q, o in answer_set]


@pytest.mark.ac("AC-01")
def test_ac_01_moderate_example_scores_16(v1: RiskPolicyDefinition) -> None:
    """AC-01.2: AGE_30_39, Y7_10, STABLE_SINGLE, M3_6, HOLD, FUNDS_LT_3Y, BALANCED -> 16, MODERATE, no caps."""
    result = assess(v1, _answers(ANS_16))

    assert result == AssessmentResult(total_score=16, computed_band=M, assigned_band=M, applied_caps=())
    assert score_answers(v1, _answers(ANS_16)) == 16


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("answer_set", "total", "band"),
    [
        (ANS_0, 0, C),
        (ANS_11, 11, C),
        (ANS_12, 12, M),
        (ANS_20, 20, M),
        (ANS_21, 21, A),
        (ANS_28, 28, A),
    ],
    ids=["0", "11", "12", "20", "21", "28"],
)
def test_ac_01_band_boundaries(v1: RiskPolicyDefinition, answer_set: AnswerSet, total: int, band: RiskBand) -> None:
    """AC-01.3: totals 0, 11, 12, 20, 21, 28 -> C, C, M, M, A, A; 0 and 11 use EMERGENCY_FUND=NONE (cap no effect)."""
    result = assess(v1, _answers(answer_set))

    assert result.total_score == total
    assert result.computed_band == band
    assert result.assigned_band == band
    assert result.applied_caps == ()


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(("score", "band"), [(0, C), (11, C), (12, M), (20, M), (21, A), (28, A)])
def test_ac_01_band_for_score_is_inclusive_at_both_edges(v1: RiskPolicyDefinition, score: int, band: RiskBand) -> None:
    """AC-01.3: v1 thresholds 0-11 / 12-20 / 21-28 are inclusive on both ends (risk_profile_spec §2.2)."""
    assert band_for_score(v1, score) == band


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize("score", [-1, 29])
def test_ac_01_band_for_score_outside_policy_range_is_rejected(v1: RiskPolicyDefinition, score: int) -> None:
    """AC-01.3: a score outside every band range of the policy has no band (guards a corrupt policy)."""
    with pytest.raises(ValueError, match="no band"):
        band_for_score(v1, score)


@pytest.mark.ac("AC-01")
def test_ac_01_cap_lowers_aggressive_to_moderate(v1: RiskPolicyDefinition) -> None:
    """AC-01.4: max points except EMERGENCY_FUND=NONE (24) -> computed AGGRESSIVE, assigned MODERATE, cap listed."""
    result = assess(v1, _answers(ANS_CAP24))

    assert result.total_score == 24
    assert result.computed_band == RiskBand("AGGRESSIVE")
    assert result.assigned_band == RiskBand("MODERATE")
    assert list(result.applied_caps) == ["NO_EMERGENCY_FUND"]


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(("band", "expected"), [(C, (C, [])), (M, (M, [])), (A, (M, ["NO_EMERGENCY_FUND"]))])
def test_ac_01_apply_caps_lists_a_cap_only_when_it_lowered_the_band(
    v1: RiskPolicyDefinition, band: RiskBand, expected: tuple[RiskBand, list[str]]
) -> None:
    """AC-01.4 / AC-01.3: NO_EMERGENCY_FUND caps at MODERATE; CONSERVATIVE and MODERATE are unchanged and unlisted."""
    assert apply_caps(v1, band, _answers(ANS_0)) == expected


@pytest.mark.ac("AC-01")
def test_ac_01_apply_caps_ignores_caps_whose_option_was_not_selected(v1: RiskPolicyDefinition) -> None:
    """AC-01.3: ANS_28 (EMERGENCY_FUND=GT_12M) stays AGGRESSIVE with no caps."""
    assert apply_caps(v1, A, _answers(ANS_28)) == (A, [])


@pytest.mark.ac("AC-01")
def test_ac_01_scoring_100_times_is_identical(v1: RiskPolicyDefinition) -> None:
    """AC-01.5: the same policy and answers scored 100 times give one distinct result."""
    results = {assess(v1, _answers(ANS_16)) for _ in range(100)}

    assert results == {AssessmentResult(total_score=16, computed_band=M, assigned_band=M, applied_caps=())}


@pytest.mark.ac("AC-01")
def test_ac_01_answer_order_does_not_change_the_result(v1: RiskPolicyDefinition) -> None:
    """AC-01.5: shuffling the submitted answer order yields an equal AssessmentResult."""
    shuffled = _answers(ANS_CAP24)
    random.Random(20260115).shuffle(shuffled)

    assert assess(v1, shuffled) == assess(v1, _answers(ANS_CAP24))
    assert sorted_by_question_order(v1, shuffled) == _answers(ANS_CAP24)


@pytest.mark.ac("AC-01")
@pytest.mark.parametrize(
    ("answer_set", "code"),
    [
        (without(ANS_16, "OBJECTIVE"), "ANSWER_MISSING"),
        (replaced(ANS_16, "AGE", "GT_10Y"), "OPTION_INVALID"),
        ((*ANS_16, ("AGE", "AGE_30_39")), "ANSWER_DUPLICATE"),
        ((*ANS_16, ("SALARY", "AGE_30_39")), "QUESTION_UNKNOWN"),
    ],
    ids=["missing-objective", "age-gt-10y", "age-twice", "salary"],
)
def test_ac_01_invalid_submissions_raise_spec_codes(v1: RiskPolicyDefinition, answer_set: AnswerSet, code: str) -> None:
    """AC-01.6: omit OBJECTIVE -> ANSWER_MISSING; AGE=GT_10Y -> OPTION_INVALID (plus §2.4 DUPLICATE / UNKNOWN)."""
    with pytest.raises(AssessmentValidationError) as raised:
        assess(v1, _answers(answer_set))

    assert raised.value.code == code
    with pytest.raises(AssessmentValidationError):
        score_answers(v1, _answers(answer_set))


@pytest.mark.ac("AC-01")
def test_ac_01_effective_band_is_none_without_events() -> None:
    """AC-01.7 (risk_profile_spec §2.5): no assessments and no overrides -> no effective band."""
    assert effective_band([], []) is None


@pytest.mark.ac("AC-01")
def test_ac_01_effective_band_is_the_newest_assessment() -> None:
    """AC-01.7: after a second assessment, the effective band is the second one's assigned band."""
    first = AssessmentEvent(id="00000000-0000-4000-8000-0000000000a2", created_at=T0, band=C)
    second = AssessmentEvent(id="00000000-0000-4000-8000-0000000000a1", created_at=T1, band=A)

    for ordering in ([first, second], [second, first]):
        assert effective_band(ordering, []) == EffectiveBand(band=A, source="ASSESSMENT", source_id=second.id, as_of=T1)


@pytest.mark.ac("AC-01")
def test_ac_01_effective_band_breaks_equal_timestamps_by_id() -> None:
    """AC-01.7 (§2.5): ordering is by created_at, then id; the greater id wins a timestamp tie."""
    low = AssessmentEvent(id="00000000-0000-4000-8000-0000000000a1", created_at=T0, band=A)
    high = AssessmentEvent(id="00000000-0000-4000-8000-0000000000b1", created_at=T0, band=C)

    assert effective_band([high, low], []) == EffectiveBand(band=C, source="ASSESSMENT", source_id=high.id, as_of=T0)


@pytest.mark.ac("AC-01")
def test_ac_01_effective_band_considers_overrides_as_events() -> None:
    """AC-01.7 (§2.5): the newest event wins whether it is an assessment or an advisor override."""
    assessment = AssessmentEvent(id="00000000-0000-4000-8000-0000000000a1", created_at=T0, band=A)
    override = OverrideEvent(id="00000000-0000-4000-8000-0000000000f1", created_at=T1, band=C)

    assert effective_band([assessment], [override]) == EffectiveBand(
        band=C, source="ADVISOR_OVERRIDE", source_id=override.id, as_of=T1
    )
    assert effective_band([], [override]) is not None


@pytest.mark.ac("AC-10")
def test_ac_10_policy_is_a_parameter_v2_bands_rescore_ans_20(v1: RiskPolicyDefinition) -> None:
    """AC-10.6 (domain half): ANS_20 is MODERATE under v1 (12-20) and AGGRESSIVE under v2 (20-28)."""
    v2 = parse_risk_policy(risk_policy_v2_ac_10_1())

    assert assess(v1, _answers(ANS_20)).assigned_band == RiskBand("MODERATE")
    assert assess(v2, _answers(ANS_20)) == AssessmentResult(
        total_score=20, computed_band=A, assigned_band=A, applied_caps=()
    )
