"""Deterministic risk scoring (risk_profile_spec §2, AC-01): validation, score, band, caps, effective band.

Every number (points, thresholds, caps) comes from the policy passed in; this module holds no copy of v1.
Pure functions only: no I/O, no clock, no logging.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.domain.bands import RiskBand, min_band
from app.domain.template_version_validator import Question, RiskPolicyDefinition

SOURCE_ASSESSMENT = "ASSESSMENT"
SOURCE_ADVISOR_OVERRIDE = "ADVISOR_OVERRIDE"


class AssessmentValidationError(ValueError):
    """A submission violates risk_profile_spec §2.4; `code` is the spec's error code (mapped to 422)."""

    def __init__(self, code: str, message: str, question_code: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.question_code = question_code


@dataclass(frozen=True)
class Answer:
    question_code: str
    option_code: str


@dataclass(frozen=True)
class AssessmentResult:
    total_score: int
    computed_band: RiskBand
    assigned_band: RiskBand
    applied_caps: tuple[str, ...]


@dataclass(frozen=True)
class AssessmentEvent:
    """A stored assessment, reduced to what the effective-band rule needs (band = assigned_band)."""

    id: str
    created_at: datetime
    band: RiskBand


@dataclass(frozen=True)
class OverrideEvent:
    """An advisor override (advisor_workbench); band = new_band."""

    id: str
    created_at: datetime
    band: RiskBand


@dataclass(frozen=True)
class EffectiveBand:
    band: RiskBand
    source: str
    source_id: str
    as_of: datetime


def _validated(policy: RiskPolicyDefinition, answers: Sequence[Answer]) -> dict[str, Answer]:
    """Answers keyed by question code, or AssessmentValidationError for the first §2.4 violation."""
    questions: dict[str, Question] = {q.code: q for q in policy.questions}
    by_question: dict[str, Answer] = {}
    for answer in answers:
        question = questions.get(answer.question_code)
        if question is None:
            raise AssessmentValidationError(
                "QUESTION_UNKNOWN", f"Unknown question {answer.question_code}.", answer.question_code
            )
        if answer.option_code not in {o.code for o in question.options}:
            raise AssessmentValidationError(
                "OPTION_INVALID",
                f"Option {answer.option_code} does not belong to question {question.code}.",
                question.code,
            )
        if question.code in by_question:
            raise AssessmentValidationError(
                "ANSWER_DUPLICATE", f"Question {question.code} answered twice.", question.code
            )
        by_question[question.code] = answer
    for question in policy.questions:
        if question.code not in by_question:
            raise AssessmentValidationError("ANSWER_MISSING", f"Question {question.code} is unanswered.", question.code)
    return by_question


def sorted_by_question_order(policy: RiskPolicyDefinition, answers: Sequence[Answer]) -> list[Answer]:
    """Validated answers in question order (the stored form, risk_profile_spec §3)."""
    by_question = _validated(policy, answers)
    return [by_question[q.code] for q in policy.questions]


def score_answers(policy: RiskPolicyDefinition, answers: Sequence[Answer]) -> int:
    """total_score = Σ points of the selected options (§2.2)."""
    by_question = _validated(policy, answers)
    return sum(
        option.points
        for question in policy.questions
        for option in question.options
        if option.code == by_question[question.code].option_code
    )


def band_for_score(policy: RiskPolicyDefinition, score: int) -> RiskBand:
    """The band whose inclusive [min_score, max_score] range contains the score (§2.2)."""
    for band_range in policy.bands:
        if band_range.min_score <= score <= band_range.max_score:
            return band_range.band
    raise ValueError(f"no band covers score {score}")


def apply_caps(policy: RiskPolicyDefinition, band: RiskBand, answers: Sequence[Answer]) -> tuple[RiskBand, list[str]]:
    """Lower the band to each matching cap's max_band (§2.3); a cap is listed only if it lowered the band."""
    selected = {(a.question_code, a.option_code) for a in answers}
    assigned = band
    applied: list[str] = []
    for cap in policy.caps:
        if (cap.question_code, cap.option_code) not in selected:
            continue
        capped = min_band(assigned, cap.max_band)
        if capped != assigned:
            applied.append(cap.code)
            assigned = capped
    return assigned, applied


def assess(policy: RiskPolicyDefinition, answers: Sequence[Answer]) -> AssessmentResult:
    """Validate, score, band and cap one submission (§2.2-2.4). Caps apply after banding; the score is unchanged."""
    total = score_answers(policy, answers)
    computed = band_for_score(policy, total)
    assigned, applied = apply_caps(policy, computed, answers)
    return AssessmentResult(total, computed, assigned, tuple(applied))


def effective_band(assessments: Sequence[AssessmentEvent], overrides: Sequence[OverrideEvent]) -> EffectiveBand | None:
    """The band of the newest event by (created_at, id) across assessments and overrides (§2.5); None if none."""
    events = [EffectiveBand(e.band, SOURCE_ASSESSMENT, e.id, e.created_at) for e in assessments]
    events += [EffectiveBand(e.band, SOURCE_ADVISOR_OVERRIDE, e.id, e.created_at) for e in overrides]
    if not events:
        return None
    return max(events, key=lambda e: (e.as_of, e.source_id))
