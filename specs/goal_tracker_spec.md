# Goal Tracker Spec

**Owns:** AC-03, AC-08 · **Related:** recommendation (goal horizon), holdings (portfolio value), admin_versioning (NAV refresh) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

Customers set financial goals (retirement, education, home or other), each with a target amount, target date and priority. Each goal is funded by a declared share of the portfolio. Progress is recomputed and snapshotted every time daily NAVs are refreshed.

## 2. Domain rules

### 2.1 Goal fields and validation

| Field | Rule | Error (422) |
|---|---|---|
| `name` | Trimmed, 1–80 characters | `GOAL_NAME_INVALID` |
| `goal_type` | `RETIREMENT` \| `EDUCATION` \| `HOME` \| `OTHER` | `GOAL_TYPE_INVALID` |
| `target_amount` | Decimal string, 2 dp, > 0.00 and ≤ 999999999999.99 | `TARGET_AMOUNT_INVALID` |
| `target_date` | ISO date strictly after the clock's today | `TARGET_DATE_NOT_FUTURE` |
| `priority` | Integer 1–5 (1 = highest) | `PRIORITY_INVALID` |
| `funding_share_pct` | Decimal string, 2 dp, 0.00–100.00 | `FUNDING_SHARE_INVALID` |
| Σ `funding_share_pct` over the customer's goals | ≤ 100.00, including the goal being created or updated | `FUNDING_SHARE_EXCEEDS_100` |

- A customer may have multiple goals, and duplicate priorities are allowed.
- **List order:** `priority` ascending, then `target_date` ascending, then `created_at` ascending. The first goal in this order is the **primary goal** used by the recommendation spec.
- Goals are mutable (`PUT`); their progress snapshots are not.

### 2.2 Progress formula

With the customer's portfolio `total_value` at the latest NAV (holdings §2.1):

```
current_goal_value = quantize_2dp(total_value × funding_share_pct / 100)          # ROUND_HALF_EVEN
percent_complete   = quantize_2dp(current_goal_value / target_amount × 100)        # ROUND_HALF_EVEN
status             = ACHIEVED if percent_complete ≥ 100.00 else IN_PROGRESS
```

- `percent_complete` is the brief's ratio `current_goal_value / target_amount`, expressed as a percentage.
- It is **not capped** at 100.00.

### 2.3 Snapshots

A `goal_progress_snapshots` row is inserted:
- for every goal of every customer on each **NAV refresh** (`reason = NAV_REFRESH`), in the same transaction as the price load;
- when a goal is **created** (`reason = GOAL_CREATED`) or **updated** (`reason = GOAL_UPDATED`), using the latest loaded NAV date.

The latest snapshot (by `created_at`, then `id`) is the goal's current progress.

### 2.4 Worked example (normative; seed customer Alice, total_value 100000.00)

| Goal | Type | Target | Target date | Priority | Share | Value | % complete | Status |
|---|---|---|---|---|---|---|---|---|
| Retirement corpus | RETIREMENT | 500000.00 | 2050-03-31 | 2 | 60.00 | 60000.00 | 12.00 | IN_PROGRESS |
| Daughter's university | EDUCATION | 50000.00 | 2032-08-31 | 1 | 40.00 | 40000.00 | 80.00 | IN_PROGRESS |

After a NAV refresh that takes `total_value` to 106000.00 (holdings AC-05.3):
- **Retirement:** 63600.00 → 12.72%.
- **University:** 42400.00 → 84.80%.

### 2.5 Domain functions (pure, `backend/app/domain/goals/`)

- `validate_goal(goal, other_goals, today) -> list[Violation]`
- `order_goals(goals) -> list[Goal]`
- `primary_goal(goals) -> Goal | None`
- `goal_progress(total_value, goal) -> GoalProgress`

## 3. Data model

**`goals`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `customer_id` | UUID FK | |
| `name` | text | |
| `goal_type` | enum | |
| `target_amount` | DecimalText(2) | |
| `target_date` | DATE | |
| `priority` | INT | |
| `funding_share_pct` | DecimalText(2) | |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

**`goal_progress_snapshots`** (append-only)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `goal_id` | UUID FK | |
| `nav_date` | DATE | |
| `total_value` | DecimalText(2) | |
| `funding_share_pct` | DecimalText(2) | |
| `current_goal_value` | DecimalText(2) | |
| `percent_complete` | DecimalText(2) | |
| `status` | enum | |
| `reason` | enum | `NAV_REFRESH` \| `GOAL_CREATED` \| `GOAL_UPDATED` |
| `created_at` | timestamp | |

## 4. API contract (role: CUSTOMER)

| Method & path | Request | Success | Errors |
|---|---|---|---|
| `POST /api/v1/goals` | `{name, goal_type, target_amount:"50000.00", target_date:"2032-08-31", priority:1, funding_share_pct:"40.00"}` | `201 {id, …fields, progress:{nav_date, current_goal_value, percent_complete, status}}` | 401, 403, 409 `NAV_NOT_LOADED`, 422 (§2.1) |
| `GET /api/v1/goals` | — | `200 [goal + progress]` in list order (§2.1) | 401, 403 |
| `GET /api/v1/goals/{goal_id}` | — | `200 goal + progress` | 404 |
| `PUT /api/v1/goals/{goal_id}` | Same body as POST | `200 goal + new progress` | 404, 422 |
| `GET /api/v1/goals/{goal_id}/progress` | — | `200 {latest:{…}, history:[{nav_date, current_goal_value, percent_complete, status, reason, created_at}]}`, newest first | 404 |

Audit events: `GOAL_CREATED`, `GOAL_UPDATED`. Logs carry the goal ID and customer ID only, never names, amounts or percentages.

## 5. Acceptance criteria

**AC-03**: A customer can create financial goals with target_amount, target_date and priority, and multiple goals per customer are supported.

- **AC-03.1 Create.**
  - **Given** Alice is signed in, the clock is 2026-01-15, and NAVs are loaded
  - **When** she posts the "Daughter's university" goal from §2.4
  - **Then** the response is `201` with the same `target_amount`, `target_date`, `priority` and `funding_share_pct` as decimal strings, plus a progress block.
- **AC-03.2 Multiple goals.**
  - **Given** Alice has created both goals from §2.4
  - **When** she calls `GET /api/v1/goals`
  - **Then** 2 goals are returned, ordered University (priority 1) then Retirement (priority 2).
- **AC-03.3 Validation.**
  - **Given** the clock is 2026-01-15
  - **When** a goal is posted with `target_date = 2026-01-15`
  - **Then** the response is `422 TARGET_DATE_NOT_FUTURE`.
  - **When** posted with `target_amount = "0.00"`
  - **Then** `422 TARGET_AMOUNT_INVALID`.
  - **When** posted with `priority = 6`
  - **Then** `422 PRIORITY_INVALID`.
- **AC-03.4 Funding cap.**
  - **Given** Alice's goals already total 100.00% funding share
  - **When** she posts a third goal with share 0.01
  - **Then** the response is `422 FUNDING_SHARE_EXCEEDS_100`. A share of 0.00 is accepted.
- **AC-03.5 Isolation.**
  - **Given** Bob is signed in
  - **When** he requests Alice's goal ID
  - **Then** the response is `404`.

**AC-08**: Goal progress is reported as percent_complete = current_goal_value / target_amount, updated on each daily NAV refresh.

- **AC-08.1 Formula.**
  - **Given** Alice's portfolio at 100000.00 and the goals in §2.4
  - **When** progress is fetched
  - **Then** Retirement shows `current_goal_value = "60000.00"` and `percent_complete = "12.00"`, and University shows `"40000.00"` and `"80.00"`.
- **AC-08.2 Updated on NAV refresh.**
  - **Given** the above
  - **When** an admin NAV refresh takes Alice's total to 106000.00
  - **Then:**
    - each goal has a new snapshot with `reason = NAV_REFRESH` and the new `nav_date`;
    - Retirement is 63600.00 / 12.72, and University is 42400.00 / 84.80;
    - the previous snapshots still exist.
- **AC-08.3 Achieved.**
  - **Given** a goal with target 30000.00 and share 40.00 on a 100000.00 portfolio
  - **When** progress is computed
  - **Then** `percent_complete = "133.33"` and `status = "ACHIEVED"`.
- **AC-08.4 Idempotent refresh.**
  - **Given** NAV date D is already loaded
  - **When** refresh is called again for D
  - **Then** no new snapshots are created.
- **AC-08.5 Decimal precision.**
  - **Given** a target of 30000.00 and a value of 10000.00
  - **When** progress is computed
  - **Then** `percent_complete = "33.33"`, computed in Decimal (no float on the path).

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | Amounts, shares, values and percentages are Decimal 2 dp, half-even |
| NFR-02 | Progress snapshots are append-only |
| NFR-03 | Goal names, amounts and progress are never logged |
| NFR-04 | CUSTOMER role; own goals only (404 otherwise) |
