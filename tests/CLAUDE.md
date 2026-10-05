# tests/: backend test suites

All backend tests live here and run from `backend/` with `poetry run pytest` (`testpaths = ["../tests"]`). Frontend unit tests and Playwright E2E live in `frontend/` (see `frontend/CLAUDE.md`).

## Layout

| Folder | What | Rules |
|---|---|---|
| `unit/domain/…` | Pure domain functions, mirroring `backend/app/domain/` | No DB, no I/O; fast (< 10 s total); 100% branch coverage target |
| `integration/repositories/` | Models, append-only guards, published-version immutability, DecimalText round-trip | In-memory SQLite, fresh schema per test |
| `integration/services/` | Use cases end to end below HTTP | Fixed `Clock`; assert final state and **exact row counts** |
| `acceptance/` | HTTP-level tests per AC via `httpx.AsyncClient` against the app | One file per spec: `test_ac_risk_profile.py`, … |
| `architecture/` | Structural rules (NFR-08 and layering) | See the list below |
| `fixtures/`, `factories/` | Synthetic data builders, seeded | Realistic synthetic values; never `"test"`, `"foo"` or `0` stand-ins |

## Required architecture tests (`tests/architecture/`)

1. `test_layering.py`: import-linter contracts pass, and `app.domain` imports only stdlib.
2. `test_no_float_money.py`: no `float` annotations or `Float`/`Numeric` columns in domain, models or schemas; no `Decimal(<float literal>)`.
3. `test_allocation_sum_invariant.py`: every published template band and every stored recommendation sums to exactly `Decimal("100.00")` (NFR-08).
4. `test_published_templates_immutable.py`: an ORM update or delete on a PUBLISHED version raises `PublishedVersionMutation` (NFR-08).
5. `test_band_reassignment_requires_override.py`: no customer band column exists, and band writes only happen through `risk_assessments` and `risk_band_overrides` (NFR-08).
6. `test_append_only_tables.py`: UPDATE or DELETE on each append-only model raises `AppendOnlyViolation` (NFR-02).
7. `test_routes_declare_roles.py`: every non-public route has a `require_role` dependency (NFR-04).
8. `test_no_pii_in_logs.py`: run the main flows with log capture, and assert no seeded name, email, username, amount or units string appears (NFR-03).
9. `test_migrations_locked.py`: hashes of migration files from approved phases match `backend/migrations/LOCKED_HASHES.txt` (NFR-05).

## AC tagging (mandatory)

- Every AC scenario `AC-NN.k` in `specs/` has at least one test.
- The test is decorated with `@pytest.mark.ac("AC-NN")`, its name starts with `test_ac_NN_`, and its docstring cites `AC-NN.k`.
- Worked examples in the specs are copied **verbatim** as expected values. Never recompute them in the test.
- **TDD:** write the failing test first and run it. Paste the real **red** output, then the **green** output after implementing, into the phase review as red–green–refactor evidence.

## Rules

- **Fix the code, never the test** (Harness self-healing rule). A test changes only when its spec changes.
- Mock only external boundaries: the clock, and the NAV CSV reader if needed. Never mock domain logic.
- Tests must not depend on a developer's `.env` (`_env_file=None` for settings tests).
- Each test is independent: no ordering dependencies and no shared mutable state.
