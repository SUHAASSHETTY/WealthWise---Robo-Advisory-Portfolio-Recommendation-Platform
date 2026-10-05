# Holdings & Drift Spec

**Owns:** AC-05 · **Related:** recommendation (targets), admin_versioning (NAV feed, drift threshold), rebalancing (consumes drift) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

Show a customer their holdings per asset class, valued at the latest NAV. Compare each class's current share of the portfolio with the target share from the customer's latest recommendation, reporting drift in percentage points.

## 2. Domain rules

### 2.1 Valuation

For each asset class `c` the customer holds (`units_c`, 4 dp), using the latest loaded NAV `nav_c` (4 dp, the newest `nav_date`):

```
value_c       = quantize_2dp(units_c × nav_c)                    # money, ROUND_HALF_EVEN
total_value   = Σ value_c
current_pct_c = quantize_2dp(value_c / total_value × 100)        # only if total_value > 0
target_pct_c  = latest recommendation's allocation for c (0.00 if c is absent)
drift_pct_c   = abs(current_pct_c − target_pct_c)                # exact, both are 2 dp
breached_c    = drift_pct_c > drift_threshold_pct                # strictly greater
```

- `drift_threshold_pct` comes from the **template version of the latest recommendation** (v1: `5.00`). It is not the newest template (see admin_versioning §2.4).
- Classes in the recommendation that the customer doesn't hold show `units = 0.0000` and `value = 0.00`.
- The rounded `current_pct` values are **not** required to sum to 100.00 (independent rounding). Only target allocations carry the exact-100 invariant.
- **No recommendation yet:** `target_pct`, `drift_pct` and `breached` are `null`, and `has_target = false`.
- **`total_value = 0`:** `current_pct`, `drift_pct` and `breached` are `null`.
- `portfolio_breached = any(breached_c)`.

### 2.2 Worked example (normative; seed customer Alice)

NAV date 2026-01-15:
- EQUITY 150.0000 · DEBT 25.0000 · GOLD 60.0000 · CASH 1.0000.

Latest recommendation: MODERATE, template v1 (50/35/10/5), threshold 5.00.

| Class | Units | Value | Current % | Target % | Drift | Breached |
|---|---|---|---|---|---|---|
| EQUITY | 400.0000 | 60000.00 | 60.00 | 50.00 | 10.00 | yes |
| DEBT | 1000.0000 | 25000.00 | 25.00 | 35.00 | 10.00 | yes |
| GOLD | 150.0000 | 9000.00 | 9.00 | 10.00 | 1.00 | no |
| CASH | 6000.0000 | 6000.00 | 6.00 | 5.00 | 1.00 | no |
| **Total** | | **100000.00** | | | | **portfolio_breached = true** |

### 2.3 Where holdings change

- Holdings are created by synthetic seed data.
- They change **only** through accepted rebalancing recommendations (stub fills; see rebalancing).
- No other API mutates holdings.

### 2.4 Domain functions (pure, `backend/app/domain/portfolio/`)

- `value_holdings(holdings, navs) -> list[ValuedHolding]`
- `current_allocation(valued) -> dict[AssetClass, Decimal | None]`
- `compute_drift(current, target, threshold) -> DriftReport`

## 3. Data model

**`holdings`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `customer_id` | UUID FK | |
| `asset_class_code` | FK | |
| `units` | DecimalText(4) | ≥ 0 |
| `updated_at` | timestamp | |

Unique on (`customer_id`, `asset_class_code`). **`nav_prices`** is defined in admin_versioning.

Holdings are mutable state, not an audit record: their history is reconstructable from `stub_orders`.

## 4. API contract (role: CUSTOMER)

| Method & path | Success | Errors |
|---|---|---|
| `GET /api/v1/holdings` | `200 {nav_date, total_value:"100000.00", has_target, recommendation_id, template_version_no, drift_threshold_pct:"5.00", portfolio_breached, lines:[{asset_class, units:"400.0000", nav:"150.0000", current_value:"60000.00", current_pct:"60.00", target_pct:"50.00", drift_pct:"10.00", breached:true}]}` | 401, 403, 409 `NAV_NOT_LOADED` |

`lines` is ordered by `asset_classes.display_order`. The response contains financial positions, so the request log records the route template, status and duration only.

## 5. Acceptance criteria

**AC-05**: Customer holdings track current value per asset class, and allocation drift = abs(current% − target%) is calculated for each asset class.

- **AC-05.1 Valuation per class.**
  - **Given** Alice's holdings and NAVs from §2.2
  - **When** she calls `GET /api/v1/holdings`
  - **Then** each line's `current_value` matches §2.2 and `total_value = "100000.00"`.
- **AC-05.2 Drift per class.**
  - **Given** the same data and a MODERATE v1 recommendation
  - **When** holdings are fetched
  - **Then** `drift_pct` is 10.00, 10.00, 1.00 and 1.00 for EQUITY, DEBT, GOLD and CASH, and `portfolio_breached = true`.
- **AC-05.3 Value follows NAV.**
  - **Given** Alice's holdings
  - **When** the NAV refresh loads EQUITY at 165.0000 (others unchanged)
  - **Then** EQUITY `current_value = "66000.00"` and `total_value = "106000.00"`.
  - `current_pct` for EQUITY is `quantize(66000/106000×100) = "62.26"`, and drift is 12.26.
- **AC-05.4 Rounding is half-even, 2 dp.**
  - **Given** units 33.3333 at NAV 3.0000
  - **When** valued
  - **Then** `value = "100.00"` (99.9999 rounds to 100.00).
  - **Given** a value/total ratio of exactly 12.345%
  - **When** `current_pct` is computed
  - **Then** it is `"12.34"` (half-even).
- **AC-05.5 No target yet.**
  - **Given** a customer with holdings but no recommendation
  - **When** holdings are fetched
  - **Then** each line has `target_pct = null` and `drift_pct = null`, `has_target = false` and `portfolio_breached = false`.
- **AC-05.6 Threshold source is the recommendation's version.**
  - **Given** Alice's latest recommendation uses template v1 (threshold 5.00), and template v2 with threshold 3.00 is published
  - **When** holdings are fetched
  - **Then** `drift_threshold_pct = "5.00"` and `template_version_no = 1`.
- **AC-05.7 Decimal-only.**
  - **When** the holdings module and its JSON are inspected
  - **Then** no `float` is used anywhere on the valuation path (architecture test), and every decimal in the response is a JSON string.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | Units, NAV, values, percentages and drift are all Decimal with the rounding in §2.1; TEXT storage |
| NFR-03 | Holdings, values and drift are never logged |
| NFR-04 | CUSTOMER role; own holdings only |
