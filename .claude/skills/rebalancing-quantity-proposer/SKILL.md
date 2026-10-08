---
name: rebalancing-quantity-proposer
description: Exact WealthWise rebalancing math — target values, BUY/SELL quantities with ROUND_DOWN, trade values, CASH settlement, negative-cash guard, and the append-only accept/dismiss/expire lifecycle (rebalancing_spec §2, AC-06/AC-07). Read before writing or testing rebalancing code.
---

# Rebalancing Quantity Proposer

**Source of truth:** `specs/rebalancing_spec.md` §2.

## Decimal rules

| Quantity | Rounding |
|---|---|
| target value, trade value, cash | 2 dp `ROUND_HALF_EVEN` |
| quantity (units) | 4 dp **`ROUND_DOWN`**, so we never over-trade |
| NAV | 4 dp, used as stored |

## Formula (non-CASH classes, in `display_order`)

```
target_value_c = q2(V × target_pct_c / 100)
delta_c        = target_value_c − value_c
quantity_c     = q4_down(abs(delta_c) / nav_c)
action_c       = BUY if delta_c > 0 and quantity_c > 0
                 SELL if delta_c < 0 and quantity_c > 0
                 NONE otherwise
trade_value_c  = q2(quantity_c × nav_c)
assert action_c != SELL or quantity_c <= units_c          # else OversellError
```

CASH is the settlement class (no order):

```
cash_change     = Σ trade_value(SELL) − Σ trade_value(BUY)
post_trade_cash = value_CASH + cash_change
```

**Negative-cash guard:** if `post_trade_cash < 0.00`, reduce the quantity of the BUY line with the largest `trade_value` (ties: lowest `display_order`) in 0.0001-unit steps, the fewest steps needed for `post_trade_cash ≥ 0.00`. Recompute after.

**Trigger:** only when `portfolio_breached` (some drift > threshold, strictly). See the `drift-calculator` skill.

## Signature (`backend/app/domain/rebalancing/proposal.py`)

```python
def propose_rebalance(valued: Sequence[ValuedHolding], target: Mapping[str, Decimal],
                      navs: Mapping[str, Decimal], display_order: Sequence[str],
                      settlement_class: str = "CASH") -> RebalanceProposal
```

## Worked example: Alice (rebalancing §2.3, AC-07.1)

V = 100000.00; targets 50/35/10/5.

| Class | Value | Target value | Delta | NAV | Action | Quantity | Trade value |
|---|---|---|---|---|---|---|---|
| EQUITY | 60000.00 | 50000.00 | −10000.00 | 150.0000 | SELL | 66.6666 | 9999.99 |
| DEBT | 25000.00 | 35000.00 | +10000.00 | 25.0000 | BUY | 400.0000 | 10000.00 |
| GOLD | 9000.00 | 10000.00 | +1000.00 | 60.0000 | BUY | 16.6666 | 1000.00 |
| CASH | 6000.00 | — | — | 1.0000 | SETTLEMENT | — | change −1000.01 |

`post_trade_cash = 4999.99`. Post-accept units (AC-07.2): EQUITY 333.3334, DEBT 1400.0000, GOLD 166.6666, CASH 4999.9900.

## Lifecycle (append-only)

- **Status** is derived from the single `rebalancing_decisions` row: none → `PROPOSED`; otherwise `ACCEPTED`, `DISMISSED` or `EXPIRED`.
- **Accept** requires `kyc_verified` (else `409 KYC_NOT_VERIFIED`) and that the proposal's `nav_date` is the latest (else `409 RECOMMENDATION_STALE`). In one transaction it writes:
  1. the decision row;
  2. `stub_orders` (`FILLED_STUB`);
  3. the holdings update (CASH units += `cash_change`);
  4. the audit event.
- **Dismiss:** an optional reason of up to 500 characters; holdings are unchanged.
- **Expire:** when a new `nav_date` loads, open proposals get an `EXPIRED` decision with actor `SYSTEM`.
- **A second decision** returns `409 ALREADY_DECIDED`. Only one open proposal per customer per `nav_date`; evaluate returns the existing one.

## Pitfalls

- `quantize(…, ROUND_DOWN)` on the **quantity**, never on the value.
- Compute `trade_value` from the rounded quantity, not from the delta.
- Never emit a CASH order.
- Never log quantities or values (NFR-03).
