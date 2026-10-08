---
name: goal-progress-tracker
description: Exact WealthWise goal rules — field validation, funding-share cap, goal ordering/primary goal, percent_complete formula and NAV-refresh snapshots (goal_tracker_spec §2, AC-03/AC-08). Read before writing or testing goal code.
---

# Goal Progress Tracker

**Source of truth:** `specs/goal_tracker_spec.md` §2.

## Validation (422 codes)

| Field | Rule | Code |
|---|---|---|
| `name` | Trimmed, 1–80 characters | `GOAL_NAME_INVALID` |
| `goal_type` | `RETIREMENT` \| `EDUCATION` \| `HOME` \| `OTHER` | `GOAL_TYPE_INVALID` |
| `target_amount` | 2 dp string, 0.00 < x ≤ 999999999999.99 | `TARGET_AMOUNT_INVALID` |
| `target_date` | Strictly after the clock's today | `TARGET_DATE_NOT_FUTURE` |
| `priority` | Integer 1–5 | `PRIORITY_INVALID` |
| `funding_share_pct` | 2 dp string, 0.00–100.00 | `FUNDING_SHARE_INVALID` |
| Σ shares across the customer's goals (incl. this one) | ≤ 100.00 | `FUNDING_SHARE_EXCEEDS_100` |

## Ordering and primary goal

Sort by `(priority ASC, target_date ASC, created_at ASC)`. The first goal is the **primary goal**, used by recommendations.

## Progress formula

```
current_goal_value = q2(total_value × funding_share_pct / 100)       # ROUND_HALF_EVEN
percent_complete   = q2(current_goal_value / target_amount × 100)    # ROUND_HALF_EVEN, NOT capped
status             = ACHIEVED if percent_complete >= Decimal("100.00") else IN_PROGRESS
```

`total_value` comes from the customer's holdings at the latest NAV (see the drift-calculator skill).

## Snapshots (append-only `goal_progress_snapshots`)

| Reason | When |
|---|---|
| `NAV_REFRESH` | Every goal, on each new NAV date, in the same transaction as the price load. Idempotent: no new snapshots if the date is already loaded. |
| `GOAL_CREATED` / `GOAL_UPDATED` | On create or update, at the latest loaded NAV date (`409 NAV_NOT_LOADED` if none) |

The latest snapshot by (`created_at`, `id`) is the current progress.

## Signatures (`backend/app/domain/goals/progress.py`)

```python
def validate_goal(goal: GoalInput, other_goals: Sequence[Goal], today: date) -> list[Violation]
def order_goals(goals: Sequence[Goal]) -> list[Goal]
def primary_goal(goals: Sequence[Goal]) -> Goal | None
def goal_progress(total_value: Decimal, goal: Goal) -> GoalProgress
```

## Worked examples (copy verbatim)

Alice, total 100000.00 (AC-08.1):

| Goal | Target | Share | Value | % | Status |
|---|---|---|---|---|---|
| Retirement corpus (P2, 2050-03-31) | 500000.00 | 60.00 | 60000.00 | 12.00 | IN_PROGRESS |
| Daughter's university (P1, 2032-08-31) | 50000.00 | 40.00 | 40000.00 | 80.00 | IN_PROGRESS |

| Case | Expected | AC |
|---|---|---|
| After a refresh to total 106000.00 | Retirement 63600.00 / 12.72; University 42400.00 / 84.80; old snapshots kept | AC-08.2 |
| Target 30000.00, share 40.00 on 100000.00 | 133.33, ACHIEVED | AC-08.3 |
| Target 30000.00, value 10000.00 | 33.33 | AC-08.5 |
| Goals at 100.00 total + new share 0.01 | `FUNDING_SHARE_EXCEEDS_100`; share 0.00 is accepted | AC-03.4 |
| Clock 2026-01-15, target 2026-01-15 | `TARGET_DATE_NOT_FUTURE` | AC-03.3 |
| List order | University (P1) before Retirement (P2) | AC-03.2 |

## Pitfalls

- `percent_complete` is a percentage (ratio × 100) and is not capped at 100.
- Never log goal names, amounts or progress (NFR-03).
