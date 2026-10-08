# PHASE-03: Architecture, scaffold, architecture tests, TDD

**Status:** APPROVED by human on 2026-10-05 · **Date:** 2026-10-05 · **Git:** no git writes; everything is uncommitted (root `CLAUDE.md` rule 3)

## Summary

| Task | Result |
|---|---|
| 1. `docs/architecture.md` | Layered structure (api → services → repositories → domain; repositories only behind services; domain framework-free), a **Mermaid C4 context** diagram, a layer flowchart, a **sequence diagram** for questionnaire → risk band → recommendation, the enforcement map for each rule, and the cross-cutting mechanisms. |
| 2. Scaffold | **Backend:** `backend/app/{api,services,domain,repositories,core}` on Python 3.12 with Poetry. `GET /health` does a DB `SELECT 1` and returns 200 or 503 (NFR-07). JSON logging has a correlation-ID middleware and allow-listed log keys (NFR-06, NFR-03). `require_role` auth uses synthetic stub tokens for customer, advisor and admin (NFR-04). Also: `DecimalText`, `Clock`, the error envelope, and an ORM guard making PUBLISHED template versions immutable. **Frontend:** `frontend/` with React 19, Vite 8, TypeScript 6 strict, Vitest 4 and ESLint 10, a typed API client and a responsive app shell. |
| 3. Layer enforcement | `backend/.importlinter` has **4 contracts** (layers; pure domain; independent core; api doesn't import repositories). `tests/architecture/` has **5 files, 56 tests**, written by **archtest-author-agent**: layer rules (import-linter plus AST), no FastAPI/SQLAlchemy/Pydantic in domain, no float in money modules (AST), templates sum to 100, and published templates are immutable. Each AST detector includes self-tests proving it catches violations. |
| 4. TDD | `docs/tdd.md` walks the AC-02 allocation-sum invariant through the full cycle: red #1 (module missing), red #2 (assertion failures against a stub), green and refactor, all with real output. `docs/tdd-log.md` is the running log, with entries TDD-001…005 and an honest note on after-the-fact characterization tests. |

## Files changed (all uncommitted)

| Area | Files |
|---|---|
| Backend app | `backend/app/main.py`; `core/{config,logging,clock,db,security}.py`; `api/{deps,errors,middleware}.py`, `api/routers/{__init__,health,auth}.py`; `services/health_service.py`; `repositories/{base,errors,guards,health_repository}.py`, `repositories/models/template_version.py`; `domain/{money,policy}.py`, `domain/allocation/templates.py`; `seed/policies/template_v1.json`; package `__init__.py` files |
| Backend config | `backend/pyproject.toml`, `backend/poetry.lock`, `backend/.importlinter`, `backend/.env.example` |
| Tests | Root `pytest.ini`; `tests/conftest.py`; `tests/unit/domain/test_money.py`, `tests/unit/domain/allocation/test_templates.py`; `tests/integration/api/test_{health,logging_correlation,auth_roles}.py`; `tests/integration/repositories/test_decimal_text.py`; `tests/architecture/test_{layering,domain_has_no_framework_imports,no_float_money,allocation_sum_invariant,published_templates_immutable}.py` |
| Frontend | `frontend/{package.json,package-lock.json,tsconfig.json,vite.config.ts,eslint.config.js,index.html,.gitignore}`; `frontend/src/{main.tsx,app/App.tsx,app/styles.css,api/client.ts,api/client.test.ts,types/health.ts}` |
| Docs | `docs/architecture.md`, `docs/tdd.md`, `docs/tdd-log.md`, this review |
| Updated | `CLAUDE.md` (run commands), `backend/CLAUDE.md` (pytest and import-linter locations), `tests/CLAUDE.md`, `.claude/agents/archtest-author-agent.md` (config path), `.gitignore` (`*.db`, caches), `scripts/ac_coverage.py` (AST scanner, see below), `coverage.xml` (artefact) |

## ACs and NFRs covered

| Item | Evidence |
|---|---|
| **AC-02** (allocation sums to 100) | 9 tagged tests: 5 unit, covering AC-02.3 and AC-02.4 (corrupted 99.99 / 100.01, range, 2 dp, float, empty band), and 4 architecture tests (every PUBLISHED seed template). Full recommendation AC-02.1/02.2/02.5 come with the recommendation feature. |
| **AC-10** (published versions immutable) | 4 tagged tests: AC-10.3 (ORM update and delete of PUBLISHED raise, row unchanged; unpublishing raises) and the AC-10.1 lifecycle (DRAFT editable → PUBLISHED → frozen). The API-level AC-10.2/10.4–10.8 come with the admin feature. |
| NFR-01 | `domain/money.py` (15 tests); `DecimalText` (round-trip, half-even, float refused); AST no-float test |
| NFR-03 | Log formatter drops non-allow-listed keys (test asserts `alice@example.com` never appears) |
| NFR-04 | `require_role`: 401 for missing or unknown token, a 3×3 role matrix (403 `FORBIDDEN_ROLE`), stub auth can be disabled |
| NFR-06 | `X-Request-ID` echoed or generated (unsafe values replaced), JSON `request completed` line with correlation ID and full route template |
| NFR-07 | `/health` 200 with DB connected; 503 when the DB is unreachable; responds within 1 s of startup; no auth |
| NFR-08 | Templates-sum and published-immutability architecture tests |

`/ac-coverage-check` now reports **2/10 ACs covered (AC-02, AC-10)**. That is expected at this phase; it exits 1 until the feature phases land.

## Real test output

### Final gate run (verbatim; blank lines and the httpx deprecation notice trimmed)

```
$ poetry run pytest ../tests
........................................................................ [ 67%]
..................................                                       [100%]
================================ tests coverage ================================
Name                                          Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------
app/api/deps.py                                  31      0      6      0   100%
app/api/errors.py                                21      3      0      0    86%   26-28
app/api/middleware.py                            26      0      0      0   100%
app/api/routers/auth.py                          13      0      0      0   100%
app/api/routers/health.py                         9      0      0      0   100%
app/core/clock.py                                15      0      0      0   100%
app/core/config.py                               11      0      0      0   100%
app/core/db.py                                   25      0      4      0   100%
app/core/logging.py                              37      0      6      0   100%
app/core/security.py                             15      0      2      0   100%
app/domain/allocation/templates.py               24      0      8      0   100%
app/domain/money.py                              15      0      2      0   100%
app/domain/policy.py                              4      0      0      0   100%
app/main.py                                      26      0      0      0   100%
app/repositories/guards.py                       18      0      4      1    95%   28->exit
app/repositories/health_repository.py             4      0      0      0   100%
app/repositories/models/template_version.py      21      0      0      0   100%
app/services/health_service.py                   21      0      2      0   100%
(empty __init__.py / base.py / errors.py rows: 100%)
-----------------------------------------------------------------------------------------
TOTAL                                           341      3     34      1    99%
Coverage XML written to file ../coverage.xml
106 passed, 1 warning in 1.18s   # before TDD-006; after it: 107 passed, 99%

$ poetry run lint-imports
Analyzed 49 files, 69 dependencies.
Layers: api > services > repositories > domain (no upward imports) KEPT
Domain is pure: no app.core/api/services/repositories, no frameworks KEPT
Core does not import application layers KEPT
API reaches repositories only through services KEPT
Contracts: 4 kept, 0 broken.

$ poetry run mypy
Success: no issues found in 31 source files

$ poetry run ruff check app ../tests && poetry run ruff format --check app ../tests
All checks passed!
47 files already formatted

$ npm run typecheck && npm test && npm run lint && npm run build
 Test Files  1 passed (1)
      Tests  6 passed (6)
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-BUQ0PulU.css    1.36 kB │ gzip:  0.63 kB
dist/assets/index-XW894BCH.js   221.08 kB │ gzip: 69.28 kB
✓ built in 79ms

$ node .claude/hooks/tests/run-wealthwise-hook-tests.js | tail -1
RESULT: 18/18 cases behaved as expected
```

`errors.py` lines 26–28 are the request-validation handler. It will be exercised once routes accept request bodies (feature phases).

### Red → green evidence

The full output is in `docs/tdd.md` and `docs/tdd-log.md`. Headlines:
- **TDD-001 (AC-02):** red #1 `ModuleNotFoundError: No module named 'app.domain.allocation'` → red #2 `7 failed, 1 passed` (`DID NOT RAISE AllocationSumError`) → green `23 passed` → refactor `23 passed`.
- **TDD-003 (NFR-04/06/07):** red: 3 collection errors (`No module named 'app.core'`). The first green attempt was `10 failed, 12 passed`, from **two test bugs** (a FastAPI annotation-resolution issue in the probe test, and the log handler binding stdout too early, which was fixed in the app). Final green: `22 passed`.
- **TDD-004:** a live smoke test found the route template logged without `/api/v1`. Red: `assert ['/auth/whoami'] == ['/api/v1/auth/whoami']`. Green: `1 passed`.
- **TDD-005 (archtest-author-agent):** red: `lint-imports failed … Could not read any configuration.` (`1 failed, 15 passed`). Green: `4 kept, 0 broken`, `56 passed`.

### Live smoke test (`uvicorn app.main:app --port 8765` + `curl`)

```
--- GET /health
HTTP/1.1 200 OK
x-request-id: smoke-1
{"status":"ok","db":"connected"}
--- GET /api/v1/auth/whoami (no token)
{"error":{"code":"UNAUTHENTICATED","message":"A valid bearer token is required.","details":{}}}  [401]
--- GET /api/v1/auth/whoami (advisor stub token)
{"username":"dan.advisor","role":"ADVISOR"}  [200]
--- server stdout (JSON logs)
{"ts": "2026-10-05T09:42:36.012708+00:00", "level": "INFO", "logger": "wealthwise.request", "message": "request completed", "correlation_id": "smoke-1", "duration_ms": 0.51, "method": "GET", "path_template": "/health", "status_code": 200}
```

The smoke test ran before the TDD-004 fix. Its whoami log line showed `"path_template": "/auth/whoami"`, which led to that fix.

### Security review (security-reviewer agent) of `backend/app`

The verdict was **no BLOCK findings**.

**Fixed in this phase:**
- **W1, stub auth on by default (public tokens = anyone is ADMIN):** now defaults to `False`. Tests and local dev opt in explicitly. TDD-006: red `assert True is False`, then green; full suite **107 passed, 99%**, with mypy, ruff and lint-imports clean.
- **W3, uvicorn access log bypasses the JSON/PII rules:** the run command is now `uvicorn … --no-access-log` (root `CLAUDE.md`, `app/main.py` docstring), because the middleware already writes JSON request logs.

**Deferred (tracked here):**
- **W2:** log message text isn't allow-listed. Planned: a ruff or AST rule requiring constant log messages, plus `tests/architecture/test_no_pii_in_logs.py`.
- **I1:** Starlette's own 404/405 and unhandled 500s skip the error envelope. Planned: generic handlers when feature routes land.
- **I4:** security headers; `/docs` should be off in prod.
- **I8:** `pip-audit`.

**Confirmed safe:** no auth bypass in `require_role`, `X-Request-ID` is CRLF-safe, the 503 body leaks nothing, and no CORS by default.

## Decisions, deviations and things to know

1. **Python 3.12:** the machine only had 3.9 (system) and 3.11 (Homebrew). The backend venv uses the user-local `uv`-managed CPython 3.12.13 that was already present; no system changes. Poetry is at `~/.local/bin/poetry` (not on PATH).
2. **Pytest config moved to the repo-root `pytest.ini`.** With explicit `../tests` paths, pytest took the repo root as rootdir and ignored `backend/pyproject.toml`, which produced the wrong red described in TDD-001. Canonical command: `cd backend && poetry run pytest ../tests`. The CLAUDE.md files are updated.
3. **`.importlinter` location:** contracts are in `backend/.importlinter` as the prompt asked, not `pyproject.toml`. CLAUDE.md and the archtest agent are updated to match.
4. **`allow_indirect_imports = True`** on the "api doesn't import repositories" contract only. Otherwise the intended api → services → repositories chain is reported as a violation.
5. **Router convention:** each versioned router declares its full prefix (`API_V1 + "/resource"`), so logged route templates are complete (TDD-004).
6. **The JSON log handler resolves `sys.stdout` at emit time.** This was needed for pytest `capsys` and is correct under uvicorn's reloader.
7. **Fixed in Phase 2 code:** `scripts/ac_coverage.py` used a regex that missed `@pytest.mark.ac` above a multi-line `@pytest.mark.parametrize(...)`, under-counting AC-02 as 6 tests instead of 9. It now uses an AST scan and stays Python 3.9-compatible. The 10/10 fixture check still passes.
8. **Stub tokens** (`stub-token-alice` …) are synthetic and development-only, and are **off by default** (enable with `WEALTHWISE_STUB_AUTH_ENABLED=true`). JWT login per `app_spec` §5.5 comes later.
9. **The Mermaid diagrams were not rendered locally**; no Mermaid CLI is installed. They use only standard `C4Context`, `flowchart` and `sequenceDiagram` syntax. Please eyeball them in GitHub or GitLab preview.
10. **Git state (unchanged by me):** `main` still has the Phase 2 squash-merge staged and uncommitted, from your earlier merge attempt. Phase 3 files sit on top, untracked or modified. When you commit, use a branch, because the pre-commit hook blocks commits on `main`.
11. **Warning noise:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2`. It's harmless for now; switching to httpx2 can be a later chore.

## Review checklist

- [ ] `docs/architecture.md`: layered structure, C4 context diagram, questionnaire → risk band → recommendation sequence diagram
- [ ] Backend layers scaffolded; `/health` (NFR-07), JSON logs + correlation ID (NFR-06), role-based stub-token auth (NFR-04) work in tests **and** on a live server
- [ ] Frontend scaffold builds, typechecks, lints and tests
- [ ] `backend/.importlinter`: 4 contracts kept; `tests/architecture/` has 5 files covering the 5 requested rules, each detector proven able to fail
- [ ] `docs/tdd.md`: the AC-02 example has real red → green → refactor output
- [ ] `docs/tdd-log.md` started, with an honest record (test bugs and characterization tests labelled)
- [ ] 107 backend tests, 99% coverage, mypy strict, ruff, lint-imports all clean
- [ ] Security review: no BLOCK; W1 and W3 fixed; W2, I1, I4 and I8 tracked
- [ ] No git writes; no changes to `./claude_harness_eng_v1/`
