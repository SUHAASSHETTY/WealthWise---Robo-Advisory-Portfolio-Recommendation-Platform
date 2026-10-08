# backend/app/domain/: pure business rules

The heart of WealthWise. Every wealth-advisory rule lives here as **pure, deterministic functions** over plain data.

## Allowed imports

stdlib only: `decimal`, `dataclasses`, `enum`, `datetime` (types only, never `now()`/`today()`), `typing`, `collections`, `itertools`, `math` (integers only).

**Forbidden:** `app.core`, `app.repositories`, `app.services`, `app.api`, `sqlalchemy`, `fastapi`, `pydantic`, `logging`, `os`, any I/O. Import-linter enforces this.

## Modules (one responsibility each)

| Module | Rules | Spec |
|---|---|---|
| `money.py` | `to_decimal` (rejects float), `q2` half-even, `q4_down` | app_spec §5.1 |
| `bands.py` | `RiskBand` enum and band ordering | risk_profile §2.2 |
| `policy.py` | `PolicyStatus` (DRAFT/PUBLISHED) | admin_versioning §2.1 |
| `allocation/templates.py` | `parse_percentage`, `validate_allocation`, `parse_template_set` (exact-100 invariant) | recommendation §2.1, §2.4 |
| `risk_band_rules.py` | Questionnaire scoring, score → band, caps, validation, effective band | risk_profile §2 |
| `allocation_template_policy.py` | Band → template lookup, horizon shift application, `recommend()` | recommendation §2 |
| `goal_horizon_policy.py` | `horizon_months`, horizon-rule selection, goal ordering and primary goal | recommendation §2.2 |
| `template_version_validator.py` | Publish validation for template and risk-policy definitions | admin_versioning §2.2–2.3 |
| Later: `portfolio/`, `rebalancing/`, `goals/` | Drift, rebalancing quantities, goal progress | holdings, rebalancing, goal_tracker |

## Rules

- **Never use float.** Construct `Decimal` from `str`/`int` only. Quantise only where the spec says, with the spec's rounding mode (`ROUND_HALF_EVEN` for money and percent, `ROUND_DOWN` for quantities).
- **Policy values are parameters.** Functions receive the policy or template definition as an argument; there are no module-level copies of points, thresholds or template percentages. v1 numbers appear only in tests and seed migrations.
- **Immutable data:** use `@dataclass(frozen=True)` value objects and enums for bands, asset classes, actions and statuses.
- **Determinism:** the same inputs always give equal outputs, and there's no hidden state.
- **Coverage target 100%** (Harness ratchet). Every branch is tested from the spec's worked examples and boundaries.
- **Tests** live in `tests/unit/domain/…`, mirroring this tree, tagged with ACs.
