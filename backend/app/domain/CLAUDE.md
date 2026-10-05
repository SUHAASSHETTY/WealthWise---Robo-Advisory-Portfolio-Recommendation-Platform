# backend/app/domain/: pure business rules

The heart of WealthWise. Every wealth-advisory rule lives here as **pure, deterministic functions** over plain data.

## Allowed imports

stdlib only: `decimal`, `dataclasses`, `enum`, `datetime` (types only, never `now()`/`today()`), `typing`, `collections`, `itertools`, `math` (integers only).

**Forbidden:** `app.core`, `app.repositories`, `app.services`, `app.api`, `sqlalchemy`, `fastapi`, `pydantic`, `logging`, `os`, any I/O. Import-linter enforces this.

## Modules (one responsibility each)

| Module | Rules | Spec |
|---|---|---|
| `money.py` | `q2`/`q4` quantisers, `Percent` and `Money` helpers, `to_decimal(str)` (rejects float) | app_spec §5.1 |
| `risk/scoring.py` | `score_answers`, `band_for_score`, `apply_caps`, `assess` | risk_profile §2 |
| `risk/effective_band.py` | `effective_band(assessments, overrides)` | risk_profile §2.5 |
| `allocation/templates.py` | `template_for_band`, sum invariant (`AllocationSumError`) | recommendation §2.1, §2.4 |
| `allocation/horizon.py` | `horizon_months`, `select_rule`, `apply_horizon` | recommendation §2.2 |
| `allocation/recommend.py` | `recommend(band, template_version, horizon_months)` | recommendation §2.5 |
| `portfolio/valuation.py` | `value_holdings`, `current_allocation` | holdings §2.1 |
| `portfolio/drift.py` | `compute_drift` | holdings §2.1 |
| `rebalancing/proposal.py` | `propose_rebalance` (quantities, settlement, negative-cash guard) | rebalancing §2.2 |
| `goals/progress.py` | `validate_goal`, `order_goals`, `primary_goal`, `goal_progress` | goal_tracker §2 |
| `policy/validation.py` | `validate_risk_policy`, `validate_template_version` | admin_versioning §2.2–2.3 |
| `errors.py` | Typed domain errors (`AllocationSumError`, `OversellError`, `PolicyInvalid`, …) | — |

## Rules

- **Never use float.** Construct `Decimal` from `str`/`int` only. Quantise only where the spec says, with the spec's rounding mode (`ROUND_HALF_EVEN` for money and percent, `ROUND_DOWN` for quantities).
- **Policy values are parameters.** Functions receive the policy or template definition as an argument; there are no module-level copies of points, thresholds or template percentages. v1 numbers appear only in tests and seed migrations.
- **Immutable data:** use `@dataclass(frozen=True)` value objects and enums for bands, asset classes, actions and statuses.
- **Determinism:** the same inputs always give equal outputs, and there's no hidden state.
- **Coverage target 100%** (Harness ratchet). Every branch is tested from the spec's worked examples and boundaries.
- **Tests** live in `tests/unit/domain/…`, mirroring this tree, tagged with ACs.
