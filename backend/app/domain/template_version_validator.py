"""Publish validation for template and risk-policy version definitions (admin_versioning_spec §2.2-2.3, AC-10.4).

`validate_*` return every violation (for the 422 response); `parse_*` return typed, Decimal-exact definitions
or raise PolicyInvalid. Decimal values must arrive as strings (NFR-01).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.allocation.templates import AllocationSumError, parse_percentage, validate_allocation
from app.domain.bands import BAND_ORDER, RiskBand

FIFTY = Decimal("50")
ZERO = Decimal("0")


class PolicyInvalid(ValueError):
    def __init__(self, violations: list[str]) -> None:
        super().__init__("; ".join(violations))
        self.violations = violations


@dataclass(frozen=True)
class HorizonRule:
    code: str
    min_months: int
    max_months: int | None
    shift: Decimal | None  # None means "ALL"
    from_class: str
    to_class: str


@dataclass(frozen=True)
class TemplateVersionDefinition:
    templates: dict[RiskBand, dict[str, Decimal]]
    horizon_rules: tuple[HorizonRule, ...]
    drift_threshold_pct: Decimal


@dataclass(frozen=True)
class Option:
    code: str
    label: str
    points: int


@dataclass(frozen=True)
class Question:
    code: str
    order: int
    prompt: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class BandRange:
    band: RiskBand
    min_score: int
    max_score: int


@dataclass(frozen=True)
class Cap:
    code: str
    question_code: str
    option_code: str
    max_band: RiskBand


@dataclass(frozen=True)
class RiskPolicyDefinition:
    questions: tuple[Question, ...]
    bands: tuple[BandRange, ...]
    caps: tuple[Cap, ...]

    @property
    def max_score(self) -> int:
        return sum(max(o.points for o in q.options) for q in self.questions)


def _decimal_string(value: object, where: str, problems: list[str]) -> Decimal | None:
    if not isinstance(value, str):
        problems.append(f"{where} must be a decimal string, got {type(value).__name__}")
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        problems.append(f"{where}={value!r} is not a decimal")
        return None


# ---------------------------------------------------------------- templates


def _template_rows(templates: object, asset_classes: Sequence[str], problems: list[str]) -> None:
    if not isinstance(templates, Mapping):
        problems.append("templates must be an object keyed by band")
        return
    for band in BAND_ORDER:
        row = templates.get(band.value)
        if not isinstance(row, Mapping):
            problems.append(f"templates.{band.value} missing")
            continue
        if sorted(row) != sorted(asset_classes):
            problems.append(f"{band.value} asset classes {sorted(row)} != active {sorted(asset_classes)}")
        values = {cls: _decimal_string(v, f"{band.value} {cls}", problems) for cls, v in row.items()}
        if any(v is None for v in values.values()):
            continue
        try:
            allocation = {cls: parse_percentage(band.value, cls, str(v)) for cls, v in values.items()}
            validate_allocation(band.value, allocation)
        except AllocationSumError as exc:
            problems.append(str(exc))


def _horizon_rule(raw: Mapping[str, Any], asset_classes: Sequence[str], problems: list[str]) -> None:
    code = raw.get("code", "?")
    if raw.get("from") == raw.get("to"):
        problems.append(f"horizon rule {code}: from and to must differ")
    for key in ("from", "to"):
        if raw.get(key) not in asset_classes:
            problems.append(f"horizon rule {code}: {key}={raw.get(key)!r} is not an active asset class")
    if raw.get("shift") != "ALL":
        shift = _decimal_string(raw.get("shift"), f"horizon rule {code} shift", problems)
        if shift is not None and not ZERO <= shift <= Decimal("100"):
            problems.append(f"horizon rule {code}: shift={shift} outside [0.00, 100.00]")


def _horizon_coverage(rules: Sequence[Mapping[str, Any]], problems: list[str]) -> None:
    spans = sorted((int(r.get("min_months", -1)), r.get("max_months")) for r in rules)
    expected_start = 0
    for start, end in spans:
        if start != expected_start:
            problems.append(f"horizon rules are not contiguous from 0: gap or overlap at month {expected_start}")
            return
        if end is None:
            if (start, end) != spans[-1]:
                problems.append("horizon rules: only the last range may be open-ended")
            return
        expected_start = int(end) + 1
    problems.append("horizon rules are not contiguous: no open-ended final range covering [n, ∞)")


def validate_template_version(definition: Mapping[str, Any], asset_classes: Sequence[str]) -> list[str]:
    problems: list[str] = []
    _template_rows(definition.get("templates"), asset_classes, problems)
    rules = definition.get("horizon_rules")
    if not isinstance(rules, list) or not rules:
        problems.append("horizon_rules must be a non-empty list")
    else:
        for rule in rules:
            _horizon_rule(rule, asset_classes, problems)
        _horizon_coverage(rules, problems)
    threshold = _decimal_string(definition.get("drift_threshold_pct"), "drift_threshold_pct", problems)
    if threshold is not None and not ZERO < threshold <= FIFTY:
        problems.append(f"drift_threshold_pct={threshold} outside (0.00, 50.00]")
    return problems


def parse_template_version(definition: Mapping[str, Any], asset_classes: Sequence[str]) -> TemplateVersionDefinition:
    problems = validate_template_version(definition, asset_classes)
    if problems:
        raise PolicyInvalid(problems)
    templates = {band: {c: Decimal(v) for c, v in definition["templates"][band.value].items()} for band in BAND_ORDER}
    rules = tuple(
        HorizonRule(
            code=r["code"],
            min_months=int(r["min_months"]),
            max_months=None if r["max_months"] is None else int(r["max_months"]),
            shift=None if r["shift"] == "ALL" else Decimal(r["shift"]),
            from_class=r["from"],
            to_class=r["to"],
        )
        for r in sorted(definition["horizon_rules"], key=lambda r: -int(r["min_months"]))
    )
    return TemplateVersionDefinition(templates, rules, Decimal(definition["drift_threshold_pct"]))


# ---------------------------------------------------------------- risk policies


def _questions(raw: object, problems: list[str]) -> list[Mapping[str, Any]]:
    questions = raw if isinstance(raw, list) else []
    if len(questions) < 6:
        problems.append(f"risk policy needs at least 6 questions, got {len(questions)}")
    codes = [q.get("code") for q in questions]
    for code in {c for c in codes if codes.count(c) > 1}:
        problems.append(f"duplicate question code {code}")
    if sorted(q.get("order", 0) for q in questions) != list(range(1, len(questions) + 1)):
        problems.append("question orders must be 1..n")
    for q in questions:
        options = q.get("options") or []
        if not 2 <= len(options) <= 6:
            problems.append(f"question {q.get('code')} needs 2-6 options, got {len(options)}")
        opt_codes = [o.get("code") for o in options]
        if len(set(opt_codes)) != len(opt_codes):
            problems.append(f"question {q.get('code')} has duplicate option codes")
        for o in options:
            points = o.get("points")
            if isinstance(points, bool) or not isinstance(points, int) or not 0 <= points <= 10:
                problems.append(f"question {q.get('code')} option {o.get('code')}: points must be an integer 0-10")
    return questions


def _max_achievable(questions: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for q in questions:
        points = [o.get("points") for o in q.get("options") or [] if isinstance(o.get("points"), int)]
        total += max(points, default=0)
    return total


def _bands(raw: object, max_score: int, problems: list[str]) -> None:
    bands = raw if isinstance(raw, list) else []
    if [b.get("band") for b in bands] != [b.value for b in BAND_ORDER]:
        problems.append("bands must be exactly CONSERVATIVE, MODERATE, AGGRESSIVE in that order")
        return
    expected = 0
    for b in bands:
        if b.get("min_score") != expected or int(b.get("max_score", -1)) < int(b.get("min_score", 0)):
            problems.append(f"band ranges must be contiguous without gaps or overlaps (at {b.get('band')})")
            return
        expected = int(b["max_score"]) + 1
    if expected - 1 != max_score:
        problems.append(f"AGGRESSIVE max_score must equal the maximum achievable score {max_score}")


def _caps(raw: object, questions: Sequence[Mapping[str, Any]], problems: list[str]) -> None:
    options = {q.get("code"): {o.get("code") for o in q.get("options") or []} for q in questions}
    for cap in raw if isinstance(raw, list) else []:
        valid_band = cap.get("max_band") in {b.value for b in BAND_ORDER}
        if cap.get("option_code") not in options.get(cap.get("question_code"), set()) or not valid_band:
            problems.append(f"cap {cap.get('code')} must reference an existing question, option and band")


def validate_risk_policy(definition: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    questions = _questions(definition.get("questions"), problems)
    _bands(definition.get("bands"), _max_achievable(questions), problems)
    _caps(definition.get("caps"), questions, problems)
    return problems


def parse_risk_policy(definition: Mapping[str, Any]) -> RiskPolicyDefinition:
    problems = validate_risk_policy(definition)
    if problems:
        raise PolicyInvalid(problems)
    questions = tuple(
        Question(
            q["code"],
            int(q["order"]),
            q["prompt"],
            tuple(Option(o["code"], o["label"], o["points"]) for o in q["options"]),
        )
        for q in sorted(definition["questions"], key=lambda q: int(q["order"]))
    )
    bands = tuple(BandRange(RiskBand(b["band"]), int(b["min_score"]), int(b["max_score"])) for b in definition["bands"])
    caps = tuple(
        Cap(c["code"], c["question_code"], c["option_code"], RiskBand(c["max_band"])) for c in definition["caps"]
    )
    return RiskPolicyDefinition(questions, bands, caps)
