"""Reference v1 answer sets (specs/stories/E2-S1.md). Copied verbatim; scores are the story's, never recomputed.

Each set is ordered AGE, HORIZON, INCOME_STABILITY, EMERGENCY_FUND, LOSS_REACTION, EXPERIENCE, OBJECTIVE.
Reused by E2-S2 (HTTP submission), E3-S2 and E3-S3.
"""

from __future__ import annotations

from typing import Any

QUESTION_CODES: tuple[str, ...] = (
    "AGE",
    "HORIZON",
    "INCOME_STABILITY",
    "EMERGENCY_FUND",
    "LOSS_REACTION",
    "EXPERIENCE",
    "OBJECTIVE",
)

AnswerSet = tuple[tuple[str, str], ...]


def _answers(*option_codes: str) -> AnswerSet:
    return tuple(zip(QUESTION_CODES, option_codes, strict=True))


ANS_16 = _answers("AGE_30_39", "Y7_10", "STABLE_SINGLE", "M3_6", "HOLD", "FUNDS_LT_3Y", "BALANCED")
ANS_0 = _answers("AGE_60_PLUS", "LT_3Y", "NO_REGULAR", "NONE", "SELL_ALL", "NONE", "PRESERVE")
ANS_11 = _answers("AGE_18_29", "GT_10Y", "IRREGULAR", "NONE", "SELL_SOME", "DEPOSITS_ONLY", "PRESERVE")
ANS_12 = _answers("AGE_30_39", "Y7_10", "STABLE_SINGLE", "M3_6", "SELL_SOME", "DEPOSITS_ONLY", "PRESERVE")
ANS_20 = _answers("AGE_30_39", "Y7_10", "STABLE_GROWING", "M6_12", "BUY_SOME", "FUNDS_LT_3Y", "GROWTH")
ANS_21 = _answers("AGE_30_39", "Y7_10", "STABLE_GROWING", "M6_12", "BUY_SOME", "FUNDS_LT_3Y", "AGGRESSIVE_GROWTH")
ANS_28 = _answers("AGE_18_29", "GT_10Y", "MULTIPLE_STABLE", "GT_12M", "BUY_MORE", "ACTIVE_GT_7Y", "AGGRESSIVE_GROWTH")
ANS_CAP24 = _answers("AGE_18_29", "GT_10Y", "MULTIPLE_STABLE", "NONE", "BUY_MORE", "ACTIVE_GT_7Y", "AGGRESSIVE_GROWTH")


def without(answers: AnswerSet, question_code: str) -> AnswerSet:
    """The set with one question left unanswered (AC-01.6 ANSWER_MISSING)."""
    return tuple(a for a in answers if a[0] != question_code)


def replaced(answers: AnswerSet, question_code: str, option_code: str) -> AnswerSet:
    """The set with one question's option swapped (AC-01.6 OPTION_INVALID)."""
    return tuple((q, option_code if q == question_code else o) for q, o in answers)


def answers_payload(answers: AnswerSet) -> list[dict[str, str]]:
    """JSON `answers` array for POST /api/v1/risk-profile/assessments."""
    return [{"question_code": q, "option_code": o} for q, o in answers]


def submission(policy_version_id: str, answers: AnswerSet) -> dict[str, Any]:
    """Full POST /api/v1/risk-profile/assessments request body."""
    return {"policy_version_id": policy_version_id, "answers": answers_payload(answers)}
