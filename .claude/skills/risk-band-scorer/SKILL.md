---
name: risk-band-scorer
description: Exact WealthWise risk-scoring rules — questionnaire points, score→band thresholds, caps, validation and effective-band derivation (risk_profile_spec §2, AC-01). Read before writing or testing any risk-profile code.
---

# Risk Band Scorer

**Source of truth:** `specs/risk_profile_spec.md` §2. If this skill and the spec ever differ, the spec wins; fix this skill.

## Formula

```
total_score   = Σ points(option selected for each question)        # int, no Decimal needed
computed_band = band b where b.min_score ≤ total_score ≤ b.max_score
assigned_band = min(computed_band, cap.max_band) for every cap whose (question, option) was selected
                (band order: CONSERVATIVE < MODERATE < AGGRESSIVE)
```

All numbers come from the **policy definition** passed in. Domain code never holds a copy of v1.

## Policy v1 (for tests and seed only)

| Question | Options → points |
|---|---|
| `AGE` | `AGE_18_29`=4, `AGE_30_39`=3, `AGE_40_49`=2, `AGE_50_59`=1, `AGE_60_PLUS`=0 |
| `HORIZON` | `LT_3Y`=0, `Y3_5`=1, `Y5_7`=2, `Y7_10`=3, `GT_10Y`=4 |
| `INCOME_STABILITY` | `NO_REGULAR`=0, `IRREGULAR`=1, `STABLE_SINGLE`=2, `STABLE_GROWING`=3, `MULTIPLE_STABLE`=4 |
| `EMERGENCY_FUND` | `NONE`=0, `LT_3M`=1, `M3_6`=2, `M6_12`=3, `GT_12M`=4 |
| `LOSS_REACTION` | `SELL_ALL`=0, `SELL_SOME`=1, `HOLD`=2, `BUY_SOME`=3, `BUY_MORE`=4 |
| `EXPERIENCE` | `NONE`=0, `DEPOSITS_ONLY`=1, `FUNDS_LT_3Y`=2, `FUNDS_STOCKS_3_7Y`=3, `ACTIVE_GT_7Y`=4 |
| `OBJECTIVE` | `PRESERVE`=0, `INCOME`=1, `BALANCED`=2, `GROWTH`=3, `AGGRESSIVE_GROWTH`=4 |

- **Bands:** 0–11 CONSERVATIVE · 12–20 MODERATE · 21–28 AGGRESSIVE.
- **Cap `NO_EMERGENCY_FUND`:** `EMERGENCY_FUND = NONE` → at most MODERATE.

## Signatures (`backend/app/domain/risk_band_rules.py`)

```python
def score_answers(policy: RiskPolicy, answers: Sequence[Answer]) -> int
def band_for_score(policy: RiskPolicy, score: int) -> RiskBand
def apply_caps(policy: RiskPolicy, band: RiskBand, answers: Sequence[Answer]) -> tuple[RiskBand, list[str]]
def assess(policy: RiskPolicy, answers: Sequence[Answer]) -> AssessmentResult
def effective_band(assessments: Sequence[AssessmentEvent], overrides: Sequence[OverrideEvent]) -> EffectiveBand | None
```

## Validation (raise typed domain errors → 422)

| Condition | Code |
|---|---|
| A question is unanswered | `ANSWER_MISSING` |
| A question is answered twice | `ANSWER_DUPLICATE` |
| An unknown question code | `QUESTION_UNKNOWN` |
| An option that doesn't belong to its question | `OPTION_INVALID` |

A stale `policy_version_id` returns `409 POLICY_VERSION_STALE`; the service checks this, not the domain.

## Effective band

The newest event by (`created_at`, `id`) across assessments (`assigned_band`) and overrides (`new_band`). No events → `None`.

## Test vectors (copy verbatim)

| Answers | Total | Computed | Assigned | Caps | AC |
|---|---|---|---|---|---|
| `AGE_30_39, Y7_10, STABLE_SINGLE, M3_6, HOLD, FUNDS_LT_3Y, BALANCED` | 16 | MODERATE | MODERATE | [] | AC-01.2 |
| All 0-point options | 0 | CONSERVATIVE | CONSERVATIVE | [] (cap doesn't lower CONSERVATIVE) | AC-01.3 |
| Totals 11 / 12 / 20 / 21 / 28 (EMERGENCY_FUND ≠ NONE for 21, 28) | — | C / M / M / A / A | same | [] | AC-01.3 |
| All 4-point options except `EMERGENCY_FUND=NONE` | 24 | AGGRESSIVE | MODERATE | `["NO_EMERGENCY_FUND"]` | AC-01.4 |
| Missing `OBJECTIVE` | — | — | — | `ANSWER_MISSING` | AC-01.6 |
| `AGE` answered with `GT_10Y` | — | — | — | `OPTION_INVALID` | AC-01.6 |

Determinism (AC-01.5): score the same answers 100 times and assert that a single distinct result is returned.

## Pitfalls

- Bands are inclusive on both ends; test both edges (11/12, 20/21).
- Apply caps **after** banding; never adjust the score.
- Never log answers, scores or bands (NFR-03).
