# Recommendation Spec

**Owns:** AC-02, AC-04 · **Related:** risk_profile (effective band), goal_tracker (horizon), admin_versioning (templates), holdings (targets) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

Turn a customer's effective risk band and goal horizon into a target allocation across asset classes, using the active **template version**. Recommendations are deterministic, sum to exactly 100.00, and are stored append-only with the versions and inputs that produced them. The customer's **latest recommendation** is the target used for drift.

## 2. Domain rules

### 2.1 Allocation templates v1 (percent, 2 dp)

| Band | EQUITY | DEBT | GOLD | CASH | Sum |
|---|---|---|---|---|---|
| `CONSERVATIVE` | 20.00 | 60.00 | 10.00 | 10.00 | **100.00** |
| `MODERATE` | 50.00 | 35.00 | 10.00 | 5.00 | **100.00** |
| `AGGRESSIVE` | 75.00 | 15.00 | 7.50 | 2.50 | **100.00** |

### 2.2 Goal-horizon adjustment (template v1)

`horizon_months` is the number of **completed calendar months** from `as_of_date` to the goal's `target_date`:
- `months = (y2−y1)·12 + (m2−m1) − (1 if d2 < d1 else 0)`;
- if `target_date ≤ as_of_date`, then `months = 0`.

| Rule code | Horizon (months) | Adjustment |
|---|---|---|
| `H_84_PLUS` | ≥ 84 | none |
| `H_60_83` | 60 – 83 | move **10.00** pts EQUITY → DEBT |
| `H_36_59` | 36 – 59 | move **20.00** pts EQUITY → DEBT |
| `H_12_35` | 12 – 35 | move **30.00** pts EQUITY → DEBT |
| `H_0_11` | 0 – 11 | move **all** EQUITY → CASH |
| `NO_GOAL` | no goal applies | none |

- The amount moved is `min(rule_shift, template[EQUITY])`, so no class goes negative.
- Moving points between classes preserves the 100.00 sum by construction.

**Which goal applies:**
- If the request names `goal_id`, that goal applies; it must belong to the caller.
- Otherwise the **primary goal** applies: lowest `priority` number, then earliest `target_date`, then earliest `created_at`.
- If the customer has no goals, the rule is `NO_GOAL`.

### 2.3 Worked examples (normative; used in tests)

| Band | Horizon | Rule | EQUITY | DEBT | GOLD | CASH |
|---|---|---|---|---|---|---|
| MODERATE | 120 | `H_84_PLUS` | 50.00 | 35.00 | 10.00 | 5.00 |
| MODERATE | 48 | `H_36_59` | 30.00 | 55.00 | 10.00 | 5.00 |
| AGGRESSIVE | 24 | `H_12_35` | 45.00 | 45.00 | 7.50 | 2.50 |
| CONSERVATIVE | 24 | `H_12_35` (shift capped at 20.00) | 0.00 | 80.00 | 10.00 | 10.00 |
| AGGRESSIVE | 6 | `H_0_11` | 0.00 | 15.00 | 7.50 | 77.50 |

### 2.4 Invariants (NFR-08)

- Every stored recommendation has exactly one allocation row per asset class in the template.
- Each `target_pct` is in [0.00, 100.00] with 2 dp, and `Σ target_pct == Decimal("100.00")` exactly.
- The domain function raises `AllocationSumError` if violated; the service never persists a violating allocation.

### 2.5 Determinism

`recommend(band, template_version, horizon_months) -> Allocation` is pure. Given the same band, template version and `horizon_months`, the output is byte-identical. `as_of_date` comes from the injected clock.

### 2.6 Manual recommendations

An advisor may log a manual allocation (see advisor_workbench). It is stored with `source = ADVISOR_MANUAL`, obeys the same invariants, and becomes the latest recommendation.

## 3. Data model

**`recommendations`** (append-only)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `customer_id` | UUID FK | |
| `source` | enum | `SYSTEM` \| `ADVISOR_MANUAL` |
| `risk_band` | enum | Effective band at creation |
| `risk_band_source_id` | UUID | Assessment or override ID |
| `template_version_id` | UUID FK | Active template version at creation; also the drift threshold source |
| `goal_id` | UUID FK, null | |
| `horizon_months` | INT, null | |
| `horizon_rule` | text | Rule code |
| `as_of_date` | DATE | |
| `note` | text, null | Manual only |
| `created_by` | UUID | User |
| `created_at` | timestamp UTC | |

**`recommendation_allocations`** (append-only): `recommendation_id`, `asset_class_code`, `target_pct` (DecimalText 2). PK is (`recommendation_id`, `asset_class_code`).

## 4. API contract (role: CUSTOMER)

| Method & path | Request | Success | Errors |
|---|---|---|---|
| `POST /api/v1/recommendations` | `{goal_id?: uuid}` | `201 {id, source, risk_band, template_version_no, goal_id, horizon_months, horizon_rule, as_of_date, allocation:[{asset_class, target_pct:"50.00"}], total_pct:"100.00", created_at}` | 401, 403, 404 `GOAL_NOT_FOUND`, 409 `RISK_PROFILE_REQUIRED` |
| `GET /api/v1/recommendations/latest` | — | `200` (same shape) or `404 RECOMMENDATION_NOT_FOUND` | 401, 403 |
| `GET /api/v1/recommendations` | — | `200 [ … ]`, newest first | 401, 403 |

Side effects: insert the recommendation, its allocation rows and an `audit_events` row (`RECOMMENDATION_CREATED`). Log the IDs and `horizon_rule` only.

## 5. Acceptance criteria

**AC-02**: The risk band determines a recommended asset allocation per a versioned template, and allocation percentages always sum to 100.

- **AC-02.1 Template per band.**
  - **Given** template v1 is active and the customer's effective band is MODERATE with no goals
  - **When** `POST /api/v1/recommendations` is called
  - **Then** the response is `201` with allocation EQUITY 50.00, DEBT 35.00, GOLD 10.00, CASH 5.00, `template_version_no = 1` and `horizon_rule = "NO_GOAL"`.
- **AC-02.2 Each band.**
  - **Given** template v1
  - **When** recommending for CONSERVATIVE and for AGGRESSIVE with no goal
  - **Then** the allocations equal the v1 rows in §2.1 exactly.
- **AC-02.3 Sum invariant across the input space.**
  - **Given** template v1
  - **When** a recommendation is computed for every band × `horizon_months` in {0, 1, 11, 12, 35, 36, 59, 60, 83, 84, 240}
  - **Then** every allocation sums to exactly `Decimal("100.00")` and no `target_pct` is negative.
- **AC-02.4 Invariant guard.**
  - **Given** a corrupted template whose MODERATE row sums to 99.99
  - **When** the domain function is called
  - **Then** it raises `AllocationSumError` and nothing is persisted.
- **AC-02.5 No band yet.**
  - **Given** a customer with no assessment or override
  - **When** `POST /api/v1/recommendations` is called
  - **Then** the response is `409 RISK_PROFILE_REQUIRED`.

**AC-04**: The portfolio-recommendation engine returns an allocation that maps to the customer's risk band and goal horizon, and the output is deterministic given the same inputs.

- **AC-04.1 Horizon adjustment.**
  - **Given** the band is MODERATE, the clock is 2026-01-15, and a goal (priority 1) has target_date 2030-01-15 (48 months)
  - **When** a recommendation is requested for that goal
  - **Then** the allocation is 30.00/55.00/10.00/5.00 with `horizon_rule = "H_36_59"`.
- **AC-04.2 Worked examples.**
  - **Given** template v1
  - **When** each row of §2.3 is computed
  - **Then** each output equals that row exactly.
- **AC-04.3 Primary goal selection.**
  - **Given** goals A (priority 2, 2040-01-01) and B (priority 1, 2028-06-30), and the clock is 2026-01-15
  - **When** a recommendation is requested without `goal_id`
  - **Then** goal B is used: `horizon_months = 29` and `horizon_rule = "H_12_35"`.
- **AC-04.4 Determinism.**
  - **Given** a fixed clock, band and goal
  - **When** `POST /api/v1/recommendations` is called twice
  - **Then** both responses have identical `allocation`, `horizon_months`, `horizon_rule` and `template_version_no`, and two distinct recommendation rows exist (append-only).
- **AC-04.5 Horizon month counting.**
  - **Given** `as_of_date = 2026-01-31`
  - **When** `target_date` is 2026-02-28, 2027-01-31 or 2025-12-01
  - **Then** `horizon_months` is 0, 12 and 0 respectively.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | Percentages are Decimal 2 dp stored as TEXT; JSON values are strings |
| NFR-02 | `recommendations` and `recommendation_allocations` are insert-only |
| NFR-03 | Allocations and bands are not logged |
| NFR-04 | CUSTOMER role; the customer comes from the token |
| NFR-08 | `tests/architecture/test_allocation_sum_invariant.py` checks every published template and every stored recommendation sums to 100.00 |
