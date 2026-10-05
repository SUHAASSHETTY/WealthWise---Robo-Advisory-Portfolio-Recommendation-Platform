# Rebalancing Spec

**Owns:** AC-06, AC-07 · **Related:** holdings (drift), recommendation (targets), admin_versioning (NAV refresh, threshold) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

When any asset class drifts beyond the threshold, propose a rebalance back to the target allocation. The proposal is a recommendation with an ID and BUY/SELL quantities per asset class. The customer accepts or dismisses it, and every decision is audited. Acceptance produces **stubbed orders** that are filled immediately at the proposal's NAVs; there is no brokerage.

## 2. Domain rules

### 2.1 Trigger

- A proposal is generated when `portfolio_breached = true` (holdings §2.1): **any** class with `drift_pct > drift_threshold_pct`, strictly greater. A drift of exactly the threshold does not trigger.
- Evaluation needs a latest recommendation (else `409 RECOMMENDATION_REQUIRED`) and `total_value > 0` (else no proposal, reason `EMPTY_PORTFOLIO`).
- **At most one open (`PROPOSED`) proposal per customer.** If one exists for the current `nav_date`, evaluation returns it unchanged.
- **Evaluation runs:**
  - on demand (`POST /rebalancing/evaluate`);
  - automatically for every customer after each NAV refresh.

### 2.2 Quantity formula

Inputs:
- `total_value` V and per-class `value_c`, `nav_c` (holdings §2.1);
- target `target_pct_c` from the latest recommendation.

**CASH is the settlement class:** it never gets an order, and its change is the net of the other trades.

For every non-CASH class `c`:

```
target_value_c = quantize_2dp(V × target_pct_c / 100)            # ROUND_HALF_EVEN
delta_c        = target_value_c − value_c
quantity_c     = round_down_4dp(abs(delta_c) / nav_c)            # ROUND_DOWN: never over-trade
action_c       = BUY if delta_c > 0 and quantity_c > 0
                 SELL if delta_c < 0 and quantity_c > 0
                 NONE otherwise
trade_value_c  = quantize_2dp(quantity_c × nav_c)                # ROUND_HALF_EVEN
```

For CASH:

```
cash_change     = Σ trade_value(SELL) − Σ trade_value(BUY)
post_trade_cash = value_CASH + cash_change                       # action = SETTLEMENT
```

- **SELL limit:** `quantity_c` never exceeds `units_c`. This is guaranteed because the target is ≥ 0, but it's checked anyway: violating it raises `OversellError`.
- **Negative cash guard:** if `post_trade_cash < 0.00`, reduce the quantity of the BUY line with the largest `trade_value` (ties: lowest `display_order`) by the fewest 0.0001-unit steps that make `post_trade_cash ≥ 0.00`, then recompute.
- **Ordering:** lines follow `asset_classes.display_order`. The domain function is pure and deterministic.

### 2.3 Worked example (normative; continues holdings §2.2)

V = 100000.00. Targets: MODERATE 50/35/10/5.

| Class | Value | Target value | Delta | NAV | Action | Quantity | Trade value |
|---|---|---|---|---|---|---|---|
| EQUITY | 60000.00 | 50000.00 | −10000.00 | 150.0000 | SELL | 66.6666 | 9999.99 |
| DEBT | 25000.00 | 35000.00 | +10000.00 | 25.0000 | BUY | 400.0000 | 10000.00 |
| GOLD | 9000.00 | 10000.00 | +1000.00 | 60.0000 | BUY | 16.6666 | 1000.00 |
| CASH | 6000.00 | 5000.00 | — | 1.0000 | SETTLEMENT | — | cash_change = −1000.01 |

- `post_trade_cash = 4999.99`.
- Post-trade units: EQUITY 333.3334, DEBT 1400.0000, GOLD 166.6666, CASH 4999.9900.

### 2.4 Lifecycle (append-only)

- **Proposal state** is derived from its `rebalancing_decisions` row:
  - `PROPOSED` while no decision row exists;
  - `ACCEPTED`, `DISMISSED` or `EXPIRED` once one exists.
- **One decision per proposal** (unique constraint). A second decision returns `409 ALREADY_DECIDED`.
- **Accept** (customer):
  - requires `customers.kyc_verified = true` (stub flag), else `409 KYC_NOT_VERIFIED`;
  - requires the proposal's `nav_date` to equal the latest loaded `nav_date`, else `409 RECOMMENDATION_STALE`.
  - In one transaction, accept:
    1. inserts the decision (`ACCEPTED`, actor, timestamp);
    2. inserts one `stub_orders` row per BUY/SELL line (`status = FILLED_STUB`, quantity, NAV, trade_value);
    3. updates `holdings` units, with CASH units += `cash_change`;
    4. writes `audit_events` `REBALANCE_ACCEPTED`.
- **Dismiss** (customer): takes an optional `reason`, up to 500 characters. It inserts the decision (`DISMISSED`) and writes the audit event `REBALANCE_DISMISSED`. There is no KYC requirement.
- **Expire** (system): when a newer NAV date loads, every open proposal gets a decision row `EXPIRED` with actor `SYSTEM`, before the new evaluation runs.

## 3. Data model (all append-only except via the decision rows noted)

**`rebalancing_recommendations`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK; the "recommendation ID" in AC-07 |
| `customer_id` | UUID FK | |
| `based_on_recommendation_id` | UUID FK | Target source |
| `template_version_id` | UUID FK | Threshold source |
| `nav_date` | DATE | |
| `total_value` | DecimalText(2) | |
| `drift_threshold_pct` | DecimalText(2) | |
| `post_trade_cash` | DecimalText(2) | |
| `created_at` | timestamp UTC | |

**`rebalancing_lines`**: `rebalancing_recommendation_id`, `asset_class_code`, `current_value`, `current_pct`, `target_pct`, `drift_pct`, `target_value`, `nav`, `action` (`BUY`\|`SELL`\|`NONE`\|`SETTLEMENT`), `quantity` (DecimalText 4, null for SETTLEMENT), `trade_value`.

**`rebalancing_decisions`**: `id`, `rebalancing_recommendation_id` (unique), `decision` (`ACCEPTED`\|`DISMISSED`\|`EXPIRED`), `reason` (null), `actor_user_id` (null for SYSTEM), `actor_role` (`CUSTOMER`\|`SYSTEM`), `created_at`.

**`stub_orders`**: `id`, `rebalancing_recommendation_id`, `asset_class_code`, `side`, `quantity`, `nav`, `trade_value`, `status` (`FILLED_STUB`), `created_at`.

## 4. API contract (role: CUSTOMER)

| Method & path | Request | Success | Errors |
|---|---|---|---|
| `POST /api/v1/rebalancing/evaluate` | — | `201 {proposal}` if a new one is created; `200 {proposal}` if an open one exists; `200 {breached:false, reason:"WITHIN_THRESHOLD"\|"EMPTY_PORTFOLIO"}` | 401, 403, 409 `RECOMMENDATION_REQUIRED`, 409 `NAV_NOT_LOADED` |
| `GET /api/v1/rebalancing/recommendations` | — | `200 [{id, status, nav_date, created_at}]`, newest first | 401, 403 |
| `GET /api/v1/rebalancing/recommendations/{id}` | — | `200 {id, status, nav_date, total_value, drift_threshold_pct, post_trade_cash, lines:[…], decision?:{decision, actor_role, created_at, reason?}}` | 404 |
| `POST /api/v1/rebalancing/recommendations/{id}/accept` | — | `200 {id, status:"ACCEPTED", orders:[{id, asset_class, side, quantity, trade_value, status}]}` | 404, 409 `ALREADY_DECIDED`, 409 `KYC_NOT_VERIFIED`, 409 `RECOMMENDATION_STALE` |
| `POST /api/v1/rebalancing/recommendations/{id}/dismiss` | `{reason?: string ≤ 500}` | `200 {id, status:"DISMISSED"}` | 404, 409 `ALREADY_DECIDED`, 422 |

The `{proposal}` shape is the same as `GET …/{id}`. Logs carry the proposal ID, customer ID, line count and decision only.

## 5. Acceptance criteria

**AC-06**: A rebalancing recommendation is generated when any asset class's drift exceeds the configured threshold (e.g. 5%).

- **AC-06.1 Breach creates a proposal.**
  - **Given** Alice's portfolio from holdings §2.2 (EQUITY drift 10.00 > 5.00)
  - **When** `POST /api/v1/rebalancing/evaluate` is called
  - **Then** the response is `201` with a proposal whose `status = "PROPOSED"` and `drift_threshold_pct = "5.00"`.
- **AC-06.2 Exactly at threshold does not trigger.**
  - **Given** a MODERATE customer with values EQUITY 55000.00, DEBT 30000.00, GOLD 10000.00, CASH 5000.00 (drifts 5.00, 5.00, 0.00, 0.00)
  - **When** evaluated
  - **Then** the response is `200 {breached:false, reason:"WITHIN_THRESHOLD"}` and no proposal row exists.
- **AC-06.3 Just over triggers.**
  - **Given** values EQUITY 55010.00, DEBT 29990.00, GOLD 10000.00, CASH 5000.00 (EQUITY drift 5.01)
  - **When** evaluated
  - **Then** a proposal is created.
- **AC-06.4 Automatic after NAV refresh.**
  - **Given** Bob is within threshold and has no open proposal
  - **When** an admin NAV refresh moves EQUITY enough to push Bob's EQUITY drift above 5.00
  - **Then** a `PROPOSED` proposal for Bob exists with the new `nav_date`, and the refresh response counts it in `rebalances_proposed`.
- **AC-06.5 One open proposal.**
  - **Given** Alice has an open proposal for the current `nav_date`
  - **When** evaluate is called again
  - **Then** the response is `200` with the same proposal ID, and no new row exists.
- **AC-06.6 Needs a target.**
  - **Given** a customer with holdings but no recommendation
  - **When** evaluated
  - **Then** the response is `409 RECOMMENDATION_REQUIRED`.

**AC-07**: The rebalancing engine proposes BUY/SELL quantities with a recommendation ID, and the customer can accept or dismiss with audit.

- **AC-07.1 Quantities and ID.**
  - **Given** AC-06.1's proposal
  - **When** it is fetched
  - **Then** it has a UUID `id`, and its lines equal §2.3 exactly: EQUITY SELL 66.6666 (9999.99), DEBT BUY 400.0000 (10000.00), GOLD BUY 16.6666 (1000.00), CASH SETTLEMENT, `post_trade_cash = "4999.99"`.
- **AC-07.2 Accept.**
  - **Given** Alice (`kyc_verified = true`) and an open, current proposal
  - **When** she calls accept
  - **Then:**
    - the response is `200`, `status = "ACCEPTED"`, with 3 `FILLED_STUB` orders;
    - her holdings units become EQUITY 333.3334, DEBT 1400.0000, GOLD 166.6666, CASH 4999.9900;
    - a decision row records `actor_user_id = Alice`, `actor_role = CUSTOMER` and `created_at`;
    - an `audit_events` row `REBALANCE_ACCEPTED` exists.
- **AC-07.3 Dismiss.**
  - **Given** an open proposal
  - **When** the customer dismisses it with reason "Will review next month"
  - **Then** `status = "DISMISSED"`, holdings are unchanged, and the decision and audit rows record the actor, timestamp and reason.
- **AC-07.4 Single decision.**
  - **Given** an accepted proposal
  - **When** accept or dismiss is called again
  - **Then** the response is `409 ALREADY_DECIDED` and nothing changes.
- **AC-07.5 KYC stub.**
  - **Given** Carol (`kyc_verified = false`) with an open proposal
  - **When** she accepts
  - **Then** the response is `409 KYC_NOT_VERIFIED`. Dismiss still succeeds.
- **AC-07.6 Stale proposal.**
  - **Given** an open proposal from nav_date D
  - **When** the NAV for D+1 loads
  - **Then** the proposal's status is `EXPIRED` (actor `SYSTEM`), and accepting it returns `409 ALREADY_DECIDED`.
- **AC-07.7 Append-only.**
  - **When** code attempts an UPDATE or DELETE on `rebalancing_recommendations`, `rebalancing_lines` or `rebalancing_decisions`
  - **Then** `AppendOnlyViolation` is raised.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | All values, quantities, percentages and drift are Decimal with the rounding in §2.2 |
| NFR-02 | Proposals, lines, decisions and stub orders are append-only; status is derived |
| NFR-03 | No values or quantities in logs |
| NFR-04 | CUSTOMER role; a customer can only see or decide their own proposals (404 otherwise) |
