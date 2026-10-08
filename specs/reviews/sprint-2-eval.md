# Evaluator Report — Sprint 2 (Epic E4: Holdings, NAV Feed, Drift & Snapshotting)

Date: 2026-10-06T00:30:00Z
VERDICT: PASS

## Summary

| Dimension | Scope | Result | Target | Status |
|---|---|---|---|---|
| Contract API Checks | 6 checks (api-s2-001…006) | 6/6 passed | 6/6 | PASS |
| Features Passed | F072…F083 | 12/12 passed (83/83 cumulative) | 12/12 | PASS |
| Pytest Test Suite | Unit, Integration, Acceptance, Architecture | 360 passed | 100% | PASS |
| Code Coverage | Total backend | 98% (100% domain) | ≥ 80% | PASS |
| Architectural Layering | Import-linter contracts | 4/4 kept, 0 broken | 4/4 | PASS |
| Type Safety | Mypy strict mode | 0 errors (77 source files) | 0 errors | PASS |
| Code Style & Linting | Ruff lint & format | 0 errors (117 files clean) | 0 errors | PASS |
| WealthWise Hook Tests | Invariant, immutability, PII, no-float | 18/18 cases passed | 18/18 | PASS |

---

## API Checks Summary (6/6 PASS)

- **api-s2-001 [AC-05.1 / AC-05.2]:** `GET /api/v1/holdings` with Alice token. Returns 200 OK with total valuation `$100,000.00` across 4 asset classes (`EQUITY`, `DEBT`, `GOLD`, `CASH`), current percentages (`60.00%`, `25.00%`, `9.00%`, `6.00%`), target percentages from recommendation v1 (`50.00%`, `35.00%`, `10.00%`, `5.00%`), and calculated drift (`10.00%`, `10.00%`, `1.00%`, `1.00%`). Drift threshold `5.00%` is breached on `EQUITY` and `DEBT`, resulting in `portfolio_breached: true`.
- **api-s2-002 [AC-05.3 / AC-08.2]:** `POST /api/v1/admin/nav-refresh` with Erin token. Returns 201 Created. Advances NAV feed to `2026-01-16` (`EQUITY` $165.00, `DEBT` $25.00, `GOLD` $60.00, `CASH` $1.0000), inserts 4 NAV price rows, and snapshots progress for all active customer goals.
- **api-s2-003 [AC-05.3]:** `GET /api/v1/holdings` with Alice token. Returns 200 OK. Holdings re-valued at new NAVs: total value increases to `$106,000.00`, `EQUITY` value rises to `$66,000.00` (`62.26%`), drift becomes `12.26%` (breached).
- **api-s2-004 [AC-08.4]:** `POST /api/v1/admin/nav-refresh?target_date=2026-01-16` with Erin token. Returns 200 OK `{"status": "ALREADY_LOADED"}` idempotently without creating duplicate prices or snapshots.
- **api-s2-005 [AC-05.5]:** `GET /api/v1/holdings` with Carol token (customer with holdings but no risk profile or recommendation). Returns 200 OK with `has_target: false`, `recommendation_id: null`, `template_version_no: null`, `drift_threshold_pct: null`, and `portfolio_breached: false`. All asset class lines have null target and drift percentages.
- **api-s2-006 [NFR-04]:** `GET /api/v1/holdings` with Dan token (ADVISOR role). Returns 403 Forbidden (`FORBIDDEN_ROLE`).

---

## Architecture & Invariant Checks

- **Pure Domain Policy (`drift_policy.py`):** 100% pure domain rule file with zero framework or I/O imports. 100% branch and statement test coverage. Implements exact Decimal arithmetic, half-even rounding `q2`, and largest-remainder reconciliation ensuring the sum of asset class percentages strictly equals `100.00%`.
- **Decimal Invariant (NFR-01):** Monetary amounts (`current_value`, `total_value`), unit balances (`units`), NAV prices (`nav`), and percentages (`current_pct`, `target_pct`, `drift_pct`) are strictly stored as `DecimalText` (VARCHAR) and processed as Python `Decimal`.
- **Append-Only Invariant (NFR-02):** `GoalProgressSnapshot` database table is protected by `protect_append_only` event listeners, rejecting any UPDATE or DELETE operations.
- **Version Pinning Invariant (AC-05.6 / NFR-08):** Holdings drift threshold is pinned to the template version referenced in the customer's recommendation. When Admin publishes a new template version v2 with a modified drift threshold (`3.00%`), Alice's holdings evaluation continues to use v1's threshold (`5.00%`).
- **Role Isolation (NFR-04):** Role boundaries strictly enforced via FastAPI dependencies. `/admin/nav-refresh` rejects CUSTOMER and ADVISOR roles (403); `/holdings` rejects ADVISOR and ADMIN roles (403).

---

## Features Updated in `features.json`

All 12 Sprint 2 features (**F072 through F083**) verified and marked as `passes: true` (83/83 cumulative passing features).
