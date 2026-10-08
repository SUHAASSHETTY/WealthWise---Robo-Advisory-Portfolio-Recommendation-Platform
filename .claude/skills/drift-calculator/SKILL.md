---
name: drift-calculator
description: Exact WealthWise holdings valuation and drift rules — units×NAV valuation, current %, drift = abs(current% − target%), strict threshold breach, and the version-pinned threshold source (holdings_spec §2, AC-05). Read before writing or testing holdings/drift code.
---

# Drift Calculator

**Source of truth:** `specs/holdings_spec.md` §2.

## Decimal rules

| Quantity | Scale | Rounding |
|---|---|---|
| units, NAV | 4 dp | stored as given |
| value, total | 2 dp | `ROUND_HALF_EVEN` |
| current %, drift | 2 dp | `ROUND_HALF_EVEN` (drift itself is exact, because both inputs are 2 dp) |

Use `with localcontext() as ctx: ctx.prec = 28`. Construct every Decimal from `str`.

## Formula

```
value_c       = q2(units_c × nav_c)
total_value   = Σ value_c
current_pct_c = q2(value_c / total_value × 100)        if total_value > 0 else None
target_pct_c  = latest_recommendation.allocation[c]     (0.00 if c is absent; None if there is no recommendation)
drift_pct_c   = abs(current_pct_c − target_pct_c)       (None if either side is None)
breached_c    = drift_pct_c > threshold                  # STRICTLY greater
portfolio_breached = any(breached_c)
threshold     = template_version(latest_recommendation).drift_threshold_pct   # v1: 5.00, NOT the newest template
```

`q2(x) = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)`. The rounded `current_pct` values need **not** sum to 100.00.

## Signatures (`backend/app/domain/portfolio/`)

```python
def value_holdings(holdings: Sequence[Holding], navs: Mapping[str, Decimal]) -> list[ValuedHolding]
def current_allocation(valued: Sequence[ValuedHolding]) -> dict[str, Decimal | None]
def compute_drift(current: Mapping[str, Decimal | None], target: Mapping[str, Decimal] | None,
                  threshold: Decimal) -> DriftReport
```

## Worked example: Alice (holdings §2.2, AC-05.1/05.2)

NAVs are EQUITY 150.0000, DEBT 25.0000, GOLD 60.0000 and CASH 1.0000. The target is MODERATE v1, threshold 5.00.

| Class | Units | Value | Current % | Target % | Drift | Breached |
|---|---|---|---|---|---|---|
| EQUITY | 400.0000 | 60000.00 | 60.00 | 50.00 | 10.00 | ✓ |
| DEBT | 1000.0000 | 25000.00 | 25.00 | 35.00 | 10.00 | ✓ |
| GOLD | 150.0000 | 9000.00 | 9.00 | 10.00 | 1.00 | |
| CASH | 6000.0000 | 6000.00 | 6.00 | 5.00 | 1.00 | |

Total 100000.00 → `portfolio_breached = true`.

## More vectors

| Case | Expected | AC |
|---|---|---|
| EQUITY NAV goes to 165.0000 | EQUITY 66000.00; total 106000.00; EQUITY % 62.26; drift 12.26 | AC-05.3 |
| 33.3333 units × NAV 3.0000 | value 100.00 (99.9999 → 100.00) | AC-05.4 |
| ratio exactly 12.345 % | 12.34 (half-even) | AC-05.4 |
| No recommendation | target, drift and breached are None; `has_target=false`; `portfolio_breached=false` | AC-05.5 |
| Latest recommendation on v1 while v2 (threshold 3.00) is published | threshold 5.00, `template_version_no` 1 | AC-05.6 |
| Drifts 5.00 / 5.00 / 0 / 0 | not breached (strict) | AC-06.2 |
| EQUITY 55010.00 of 100000.00 | drift 5.01 → breached | AC-06.3 |

## Pitfalls

- Don't divide by a zero total; return None percentages instead.
- Don't use `round()` (banker's rounding on floats). Use `quantize` on Decimal.
- Never log values, units or drift (NFR-03).
