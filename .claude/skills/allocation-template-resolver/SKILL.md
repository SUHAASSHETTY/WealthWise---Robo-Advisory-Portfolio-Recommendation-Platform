---
name: allocation-template-resolver
description: Exact WealthWise allocation rules — band→template lookup, goal-horizon month counting and adjustment, primary-goal selection, and the exact-100 invariant (recommendation_spec §2, AC-02/AC-04). Read before writing or testing recommendation or template code.
---

# Allocation Template Resolver

**Source of truth:** `specs/recommendation_spec.md` §2 and `specs/admin_versioning_spec.md` §2.3.

## Decimal rules

- Percentages are `Decimal` at 2 dp, built from the **string** values in the template JSON (`Decimal("7.50")`), never from float.
- There is no rounding step: shifts are 2 dp values, so every result is already exact at 2 dp.
- **Invariant:** `sum(allocation.values()) == Decimal("100.00")`, and every value is ≥ `Decimal("0.00")`. Otherwise raise `AllocationSumError`.

## Formula

```
months = (y2 - y1)*12 + (m2 - m1) - (1 if d2 < d1 else 0)    # as_of=(y1,m1,d1), target=(y2,m2,d2)
months = 0 if target_date <= as_of_date

rule   = the horizon rule with min_months <= months <= max_months (max None = ∞); NO_GOAL if no goal
alloc  = copy(template[band])
amount = alloc[rule.from] if rule.shift == "ALL" else min(Decimal(rule.shift), alloc[rule.from])
alloc[rule.from] -= amount ; alloc[rule.to] += amount
assert sum(alloc) == 100.00
```

**Goal selection:** use the `goal_id` if given (it must be the caller's). Otherwise take the primary goal: lowest `priority`, then earliest `target_date`, then earliest `created_at`. No goals → `NO_GOAL`.

## Template v1 (tests and seed only)

| Band | EQUITY | DEBT | GOLD | CASH |
|---|---|---|---|---|
| CONSERVATIVE | 20.00 | 60.00 | 10.00 | 10.00 |
| MODERATE | 50.00 | 35.00 | 10.00 | 5.00 |
| AGGRESSIVE | 75.00 | 15.00 | 7.50 | 2.50 |

| Rule | Months | Shift |
|---|---|---|
| `H_84_PLUS` | ≥ 84 | none |
| `H_60_83` | 60–83 | 10.00 EQUITY→DEBT |
| `H_36_59` | 36–59 | 20.00 EQUITY→DEBT |
| `H_12_35` | 12–35 | 30.00 EQUITY→DEBT |
| `H_0_11` | 0–11 | ALL EQUITY→CASH |

## Signatures (`backend/app/domain/allocation_template_policy.py`, `goal_horizon_policy.py`)

```python
def horizon_months(as_of: date, target: date) -> int
def select_rule(rules: Sequence[HorizonRule], months: int | None) -> HorizonRule | NoGoalRule
def apply_horizon(alloc: Mapping[str, Decimal], rule: HorizonRule) -> dict[str, Decimal]
def recommend(band: RiskBand, template: TemplateVersion, months: int | None) -> Recommendation
```

## Worked examples (copy verbatim; AC-04.2)

| Band | Months | Rule | EQUITY | DEBT | GOLD | CASH |
|---|---|---|---|---|---|---|
| MODERATE | 120 | H_84_PLUS | 50.00 | 35.00 | 10.00 | 5.00 |
| MODERATE | 48 | H_36_59 | 30.00 | 55.00 | 10.00 | 5.00 |
| AGGRESSIVE | 24 | H_12_35 | 45.00 | 45.00 | 7.50 | 2.50 |
| CONSERVATIVE | 24 | H_12_35 (capped at 20.00) | 0.00 | 80.00 | 10.00 | 10.00 |
| AGGRESSIVE | 6 | H_0_11 | 0.00 | 15.00 | 7.50 | 77.50 |

**Month counting (AC-04.5):** with `as_of = 2026-01-31`, a target of 2026-02-28 gives 0 months, 2027-01-31 gives 12, and 2025-12-01 gives 0.

**Primary goal (AC-04.3):** with the clock at 2026-01-15, goals A (priority 2, 2040-01-01) and B (priority 1, 2028-06-30) select B, giving 29 months and `H_12_35`.

**Sum grid (AC-02.3):** every band × months in {0, 1, 11, 12, 35, 36, 59, 60, 83, 84, 240} sums to exactly 100.00.

## Pitfalls

- Boundary months: 11/12, 35/36, 59/60 and 83/84 change the rule. Test both sides.
- `max(0, …)` is wrong for past targets; the spec defines `months = 0` when `target ≤ as_of`.
- Don't hard-code v1 in production modules. The `allocation-sum-invariant-check` hook checks seed and template files.
