# PHASE-05: Sprint 2 (AC-05 Holdings, NAV Feed, Drift & AC-08 Groundwork)

**Status:** READY FOR REVIEW · **Date:** 2026-10-06 · **Git:** no git writes; everything uncommitted (root `CLAUDE.md` rule 3)

## Summary

| Task | Result |
|---|---|
| 1. Sprint contract & stories | `sprint-contracts/sprint-2.json` negotiated across 4 stories (E4-S1…E4-S4) with 6 API verification checks (api-s2-001…006) and 12 features (F072…F083). |
| 2. Domain rules | Pure domain policy module `backend/app/domain/drift_policy.py` implementing `value_holdings`, `current_allocation` (with half-even rounding `q2` and largest-remainder 100.00% sum reconciliation), `compute_drift` (`abs(current% - target%)` per asset class, strict `drift > threshold` comparison), and `calculate_goal_progress`. 100% statement and 100% branch test coverage. |
| 3. Repositories & schema | 3 new ORM models (`Holding`, `NavPrice`, `GoalProgressSnapshot`), Alembic migration `0003_sprint2_holdings_nav_snapshots.py` with initial 2026-01-15 NAV prices and customer holdings seed data, and append-only event listener protection (`protect_append_only`) on `goal_progress_snapshots` (NFR-02). |
| 4. Services & API | `holdings_service.py`, `nav_feed_service.py`, `api/routers/holdings.py` (`GET /api/v1/holdings`), `api/routers/admin_nav.py` (`POST /api/v1/admin/nav-refresh`). Role isolation enforced (403 for non-customers on holdings, 403 for non-admins on nav refresh). Version-pinned drift threshold source maintained against active/historical recommendation template versions (AC-05.6 / NFR-08). |
| 5. TDD & verification | Strict TDD logged in `docs/tdd-log.md`. 360 backend tests passing with 98% overall coverage (100% domain coverage). All 6 Sprint 2 API contract checks evaluated and passing against `eval.db`. Evaluator report written to `specs/reviews/sprint-2-eval.md`. |

---

## Files changed (all uncommitted)

| Area | Files |
|---|---|
| Domain | `backend/app/domain/drift_policy.py` |
| Repositories | `backend/app/repositories/holding_repository.py`, `backend/app/repositories/nav_repository.py`, `backend/app/repositories/goal_snapshot_repository.py`, `backend/app/repositories/models/holding.py`, `backend/app/repositories/models/nav_price.py`, `backend/app/repositories/models/goal_progress_snapshot.py` |
| Services | `backend/app/services/holdings_service.py`, `backend/app/services/nav_feed_service.py` |
| API & Schemas | `backend/app/api/routers/holdings.py`, `backend/app/api/routers/admin_nav.py`, `backend/app/api/schemas/holdings.py`, `backend/app/main.py` |
| Migrations & Seed | `backend/migrations/versions/0003_sprint2_holdings_nav_snapshots.py`, `backend/app/seed/nav_series.csv` |
| Tests | `tests/unit/domain/test_drift_policy.py`, `tests/integration/services/test_holdings_service.py`, `tests/integration/services/test_nav_feed_service.py`, `tests/acceptance/test_ac_holdings.py`, `tests/acceptance/test_ac_nav_feed.py`, `tests/architecture/test_append_only_tables.py` |
| Harness & Docs | `sprint-contracts/sprint-2.json`, `specs/reviews/sprint-2-eval.md`, `docs/tdd-log.md`, `features.json`, `.claude/state/iteration-log.md`, this review |

---

## ACs and NFRs covered

| Item | Status | Evidence |
|---|---|---|
| **AC-05** (Holdings & allocation drift) | 100% | Customer holdings valued at latest NAVs per asset class; percentage calculated with `q2` half-even rounding and 100.00% sum invariant reconciliation; drift calculated as `abs(current% - target%)`; strict threshold comparison (`drift > threshold`); pinned to recommendation template version (e.g. Alice remains on v1 threshold 5.00% after v2 published with 3.00%); customer without recommendation returns `has_target: false` with null drift. Tagged in `test_ac_holdings.py`, `test_holdings_service.py`, and `test_drift_policy.py`. |
| **AC-08 Groundwork** (Goal progress snapshotting) | 100% | NAV feed refresh calculates and records goal progress snapshots (`current_goal_value = q2(total_value * funding_share / 100)`, `percent_complete = q2(current_goal_value / target_amount * 100)`, `status = IN_PROGRESS / ACHIEVED`). Tagged in `test_ac_nav_feed.py`, `test_nav_feed_service.py`, and `test_drift_policy.py`. |
| **NFR-01** (Decimal precision) | 100% | Holdings units (4dp), NAV prices (4dp), monetary valuations (2dp), current/target/drift percentages (2dp) strictly managed with Python `Decimal` and `DecimalText` (VARCHAR). Zero floats. |
| **NFR-02** (Append-only records) | 100% | `GoalProgressSnapshot` records are append-only. `protect_append_only` listener rejects any UPDATE or DELETE operations with `AppendOnlyViolation`. |
| **NFR-03** (PII redaction) | 100% | Loggers record correlation IDs, entity IDs, customer IDs, and status codes without leaking customer PII or financial holdings balances. |
| **NFR-04** (Role-based auth) | 100% | `GET /api/v1/holdings` requires CUSTOMER role (ADVISOR and ADMIN receive 403); `POST /api/v1/admin/nav-refresh` requires ADMIN role (CUSTOMER and ADVISOR receive 403). Unauthenticated requests return 401. |
| **NFR-05** (Database migration) | 100% | Migration `0003_sprint2_holdings_nav_snapshots.py` applies cleanly and idempotently on top of revisions 0001 and 0002. |
| **NFR-08** (Architecture rules as tests) | 100% | Append-only invariant for goal snapshots verified in `test_append_only_tables.py`; import linter contracts pass with 0 broken. |

---

## Real test output

### 1. Pytest Test Suite (360 tests passed, 98% coverage)

```
$ poetry run pytest ../tests
================================ tests coverage ================================
Name                                                Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------------
app/domain/drift_policy.py                             76      0     14      0   100%
app/domain/risk_band_rules.py                          89      0     24      0   100%
app/domain/allocation_template_policy.py               29      0      4      0   100%
app/domain/goal_horizon_policy.py                      21      0      8      0   100%
app/services/holdings_service.py                       45      1      6      1    96%   60
app/services/nav_feed_service.py                       69      3     26      4    93%   33, 55, 69, 119->122
app/api/routers/holdings.py                            17      0      0      0   100%
app/api/routers/admin_nav.py                           17      1      2      1    89%   29
TOTAL                                                1848     29    246     21    98%
360 passed, 24 warnings in 4.28s
```

### 2. Contract API Evaluator (6/6 checks passed on eval.db)

```
$ poetry run python scripts/eval_sprint2.py
Running check api-s2-001: GET /api/v1/holdings ... PASS
Running check api-s2-002: POST /api/v1/admin/nav-refresh ... PASS
Running check api-s2-003: GET /api/v1/holdings ... PASS
Running check api-s2-004: POST /api/v1/admin/nav-refresh?target_date=2026-01-16 ... PASS
Running check api-s2-005: GET /api/v1/holdings ... PASS
Running check api-s2-006: GET /api/v1/holdings ... PASS

Total: 6, Passed: 6, Failed: 0
```

### 3. Layering & Architectural Integrity

```
$ poetry run lint-imports
Analyzed 99 files, 374 dependencies.
Contracts: 4 kept, 0 broken.

$ poetry run mypy app
Success: no issues found in 77 source files

$ poetry run ruff check app ../tests
All checks passed!

$ poetry run ruff format --check app ../tests
117 files already formatted
```

---

## Verification Summary

- **Contract:** `sprint-contracts/sprint-2.json` fully satisfied with 6/6 API checks passing.
- **Features:** 12/12 features F072–F083 passing; 83/83 total features passing in `features.json`.
- **Quality Gates:** 0 lint errors, 0 type errors, 0 architectural violations, 98% test coverage across 360 automated tests.
- **Next Sprint:** Ready for Sprint 3 (Rebalancing Proposer & Quantity Calculation — AC-06, AC-07).
