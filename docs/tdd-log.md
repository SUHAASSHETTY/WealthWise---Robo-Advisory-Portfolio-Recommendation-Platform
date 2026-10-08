# TDD log

A running red → green → refactor record for every feature, newest phase last. **Every output below was pasted from a real run.** The method is described in [docs/tdd.md](tdd.md).

Commands are run from `backend/`: `~/.local/bin/poetry run pytest ../tests/<path> --no-cov -p no:cacheprovider`.

**Entry format:**
- **Scope:** AC or NFR, plus spec reference.
- **Tests:** file path(s).
- **Red:** the real failing output and why it is the *right* failure.
- **Green:** the real passing output.
- **Refactor:** what changed, and the re-run output.
- **Notes:** test bugs, harness fixes or deviations, stated plainly.

---

## Phase 03: architecture and scaffold (2026-10-05)

### TDD-001: AC-02 allocation-sum invariant

- **Scope:** AC-02.3 and AC-02.4, NFR-08 (`recommendation_spec` §2.1, §2.4).
- **Tests:** `tests/unit/domain/allocation/test_templates.py` (8 tests).
- **Red #1** (module missing): `E   ModuleNotFoundError: No module named 'app.domain.allocation'` … `1 error in 0.05s`, exit=2.
- **Red #2** (interface stub, no validation): `E       Failed: DID NOT RAISE AllocationSumError` (×6) and `DID NOT RAISE TypeError` (×1). `7 failed, 1 passed in 0.02s`, exit=1.
- **Green:** `23 passed in 0.02s` (with TDD-002), exit=0.
- **Refactor:** extracted `parse_percentage` and `validate_allocation`, removed two `# type: ignore`, and switched the exponent check to `quantize(CENT)`. Result: `23 passed in 0.01s`, exit=0; mypy strict reports `Success: no issues found in 4 source files`.
- **Notes:** the very first red was **wrong**: `No module named 'app'`. Pytest took the repo root as rootdir and ignored `backend/pyproject.toml`'s `pythonpath`. Fixed with a root `pytest.ini` (`pythonpath = backend`) before recording red #1. The full worked example is in docs/tdd.md.

### TDD-002: NFR-01 fixed-point helpers

- **Scope:** NFR-01 (`app_spec` §5.1).
- **Tests:** `tests/unit/domain/test_money.py` (15 tests).
- **Red:**
  ```
  E   ModuleNotFoundError: No module named 'app.domain.money'
  ERROR ../tests/unit/domain/test_money.py
  1 error in 0.05s
  exit=2
  ```
- **Green:** `app/domain/money.py` (`to_decimal` rejects float and bool; `q2` half-even; `q4_down` round-down). Passed in the same 23-test run as TDD-001.
- **Refactor:** none needed.

### TDD-003: NFR-04 / NFR-06 / NFR-07 API scaffold (auth roles, JSON logs with correlation ID, health)

- **Scope:** NFR-04, NFR-06 and NFR-07 (`app_spec` §5.5, §5.6, §5.8).
- **Tests:** `tests/integration/api/test_health.py` (4), `test_logging_correlation.py` (5), `test_auth_roles.py` (13).
- **Red:**
  ```
  E   ModuleNotFoundError: No module named 'app.api.deps'
  E   ModuleNotFoundError: No module named 'app.core'
  E   ModuleNotFoundError: No module named 'app.core'
  1 warning, 3 errors in 0.61s
  exit=2
  ```
- **First green attempt:** `10 failed, 12 passed`. **Both failure groups were test bugs, not app bugs:**
  1. The role matrix got `assert 422 == 200` / `assert 422 == 403`. The probe endpoint used `Annotated[..., Depends(require_role(role))]` with a loop variable under `from __future__ import annotations`, so FastAPI couldn't resolve the annotation and treated `principal` as a query parameter. **Fix (test):** bind the dependency eagerly through a factory.
  2. The JSON log test got `assert 0 == 1` (no records). After fix 1 the run was `1 failed, 21 passed`. Debugging showed the record **was** emitted (`caplog` saw `request completed`), but the handler had bound `sys.stdout` at app creation, before pytest's `capsys` swap. **Fix (app):** the JSON handler now resolves `sys.stdout` at emit time (`_CurrentStdoutHandler`), which is also correct under uvicorn's reloader. **No assertion was weakened.**
- **Green:** `22 passed, 1 warning in 0.40s`, exit=0.
- **Refactor:** typed the error envelope `details`, removed an unused `type: ignore`, and moved to ruff format and isort with `known-first-party = ["app"]`. Result: full suite `45 passed`, mypy `Success: no issues found in 31 source files`.

### TDD-004: request log route template (bug found by the live smoke test)

- **Scope:** NFR-06 (`app_spec` §5.6: log the route template, not raw paths).
- **Detection:** the live `uvicorn` + `curl` smoke test logged `"path_template": "/auth/whoami"` for `GET /api/v1/auth/whoami`. In this FastAPI version, `include_router(prefix=...)` doesn't fold the prefix into `route.path`.
- **Test:** `test_logging_correlation.py::test_request_log_uses_full_versioned_route_template`.
- **Red:**
  ```
  E       AssertionError: assert ['/auth/whoami'] == ['/api/v1/auth/whoami']
  E         At index 0 diff: '/auth/whoami' != '/api/v1/auth/whoami'
  1 failed, 1 warning in 0.28s
  exit=1
  ```
- **Green:** each router declares its full prefix (`API_V1 = "/api/v1"` in `app/api/routers/__init__.py`) and is included without a prefix. Result: `1 passed, 1 warning in 0.25s`, exit=0. Full suite: `106 passed`.
- **Refactor:** none needed. The convention is documented in the routers package docstring.

### TDD-005: architecture tests (archtest-author-agent)

- **Scope:** layering, NFR-01, NFR-08, AC-02 and AC-10 structural rules (`tests/CLAUDE.md` items 1–4).
- **Tests:** `tests/architecture/test_layering.py`, `test_domain_has_no_framework_imports.py`, `test_no_float_money.py`, `test_allocation_sum_invariant.py`, `test_published_templates_immutable.py` (56 tests).
- **Red** (before `backend/.importlinter` existed):
  ```
  ../tests/architecture/test_layering.py F...............                  [100%]
  E       AssertionError: lint-imports failed (exit 1):
  E         Could not read any configuration.
  FAILED ../tests/architecture/test_layering.py::test_import_linter_contracts_are_kept
  ========================= 1 failed, 15 passed in 0.13s =========================
  ```
- **Second red** (config present, one contract too strict): `API reaches repositories only through services BROKEN` because of the legitimate chain `app.api.routers.health -> app.services.health_service -> app.repositories.health_repository`. **Fix:** `allow_indirect_imports = True` on that contract only, so it checks direct imports (matching the AST check).
- **Green:** `Contracts: 4 kept, 0 broken.` and `56 passed in 0.26s`.
- **Detector self-tests:** every AST scanner is also run over in-memory bad source (e.g. `from fastapi import APIRouter` in domain, `drift_threshold = 5.0`, `Decimal(101.25)`, a services module importing `app.api`). This proves each check can fail even though the real code is clean.

### Characterization tests: not TDD

- `tests/integration/repositories/test_decimal_text.py` (4 tests: DecimalText round-trip, half-even quantisation at bind time, float refused, clock).
- These were written **after** `app/core/db.py` and `app/core/clock.py` as part of the scaffold, to close coverage gaps (db 55% → 100%, clock 0% → 100%). They are recorded here for honesty: no red step was observed.

### TDD-006: stub auth off by default (security review W1)

- **Scope:** NFR-04 hardening. Finding W1 from the security-reviewer agent: the public stub tokens were accepted by default.
- **Test:** `tests/integration/api/test_auth_roles.py::test_stub_auth_is_off_by_default`.
- **Red:**
  ```
  E       AssertionError: assert True is False
  E        +  where True = Settings(app_name='WealthWise', database_url='sqlite:///./wealthwise.db', log_level='INFO', stub_auth_enabled=True).stub_auth_enabled
  1 failed, 1 warning in 0.33s
  ```
- **Green:** `stub_auth_enabled: bool = False`. Tests opt in through the `settings` fixture, and local dev through `WEALTHWISE_STUB_AUTH_ENABLED=true` (`backend/.env.example`). Result: `1 passed, 1 warning in 0.33s`; full suite `107 passed`.
- **Refactor:** none needed.

---

## Phase 04: Sprint 1 (AC-01, AC-02, AC-04, AC-10) (2026-10-05)

### TDD-S1-E1-S1: schema, Alembic, append-only and published guards (generator lead)

- **Scope:** NFR-02 append-only; AC-01.7 (UPDATE on risk_assessments raises); AC-10.3 (published risk policy and template immutable); AC-10.7 (one DRAFT per type, partial unique index); NFR-05 (migrations).
- **Tests:** `tests/integration/repositories/test_version_guards.py` and `test_schema_migration.py` (10 tests). A session-scoped `migrated_db_path` fixture runs `alembic upgrade head` once, and each test gets a copy.
- **Red:**
  ```
  E   ImportError: cannot import name 'AppendOnlyViolation' from 'app.repositories.errors'
  !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
  1 error in 0.18s
  ```
  This is the right failure: the guard, the models and the migrations did not exist.
- **Green:** 10 ORM models, `protect_append_only` listeners, a shared `VersionedPolicyMixin` with the `uq_<table>_one_draft` partial index, revision `0001` (autogenerated) and `0002` (seed). Result: `10 passed, 1 warning in 0.24s`.
- **Generator correction:** autogenerate emitted `app.core.db.DecimalText(length=40)` (wrong constructor, and an app import inside a migration). It was rewritten to `sa.String(length=40)` before the first run.
- **Refactor:**
  - the seed migration no longer renames a shared `TableClause` in place (it uses a `_policy_table(name)` factory);
  - the repository uses Python 3.12 type parameters (ruff UP047).

  Result: `54 passed` (with unit tests). Then the full suite: **2 failed**. The Phase 03 architecture test globbed every `seed/policies/*.json` as a template, and that broke once `risk_policy_v1.json` was added. The fix scoped the test to `template_*.json`; its assertions are unchanged. Final: `138 passed`.

### TDD-S1-E1-S2: band types and policy validators (generator lead)

- **Scope:** AC-10.1, AC-10.4 (admin_versioning_spec §2.2–2.3); risk_profile_spec §2.1–2.3 points and bands.
- **Tests:** `tests/unit/domain/test_template_version_validator.py` (21 tests); fixtures in `tests/fixtures/policy_definitions.py`.
- **Red:**
  ```
  E   ModuleNotFoundError: No module named 'app.domain.bands'
  !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
  1 error in 0.06s
  exit=2
  ```
  This is the right failure: neither `bands.py` nor `template_version_validator.py` existed.
- **Green:** `21 passed in 0.02s`, exit=0. The validator returns *every* violation (e.g. `AGGRESSIVE sum=100.01, expected exactly 100.00`) so the admin API can return them all.
- **Refactor:** none at this point. The later ruff pass adopted Python 3.12 type parameters in the repository.

### TDD-S1-E1-S3: seed, clock injection, customer resolution, ServiceError (generator lead)

- **Scope:** app_spec §5.2 (clock), §5.5 (5 customers), §5.7 (error envelope); AC-02.5 and AC-04.1 prerequisites.
- **Tests:** `tests/integration/services/test_foundation_services.py` (15 tests).
- **Red:**
  ```
  E   ImportError: cannot import name 'audit_repository' from 'app.repositories'
  1 warning, 1 error in 0.39s
  exit=2
  ```
- **Green:**
  - `Settings.fixed_clock` (`WEALTHWISE_FIXED_CLOCK`), with `create_app(settings, clock=None)` → `app.state.clock`;
  - `stub-token-frank` and `stub-token-grace`;
  - `customer_resolver.customer_id_for`, with 403 for non-customers;
  - `ServiceError` mapped to the envelope;
  - `policy_version_repository`, `audit_repository` (picks up the correlation ID), `customer_repository` and `goal_repository`.

  Result: `15 passed, 2 warnings in 0.49s`. Full gates: **153 passed, 95%**, mypy strict clean, lint-imports 4/4.
- **Incident:** the shell loop that pre-created the feature routers used `path` as a variable, which in zsh is tied to `$PATH`. It left four empty router files. They were detected (`wc -c` = 0), recreated, and the full suite re-run: 153 passed.

### TDD-S1-CLOCK: anchored evaluator clock (defect reported by risk-profiler-agent)

- **Detection:** while building E2-S2, risk-profiler-agent found that under `WEALTHWISE_FIXED_CLOCK` every row got the same `created_at`, so "newest" (created_at, then UUID id) was a coin flip. Across 20 simulated fresh DBs, `GET /risk-profile` returned the *older* assessment 9 times. Contract checks api-010/011/015/016/059/060 would have been flaky.
- **Spec change first:** app_spec §5.2 now says the setting *anchors* the clock: today() is pinned, and time advances in real time.
- **Test:** `test_foundation_services.py::test_fixed_clock_setting_anchors_date_but_keeps_time_moving`.
- **Red:**
  ```
  E       assert datetime.datetime(2026, 1, 15, 9, 0, tzinfo=datetime.timezone.utc) > datetime.datetime(2026, 1, 15, 9, 0, tzinfo=datetime.timezone.utc)
  1 failed, 2 warnings in 0.52s
  exit=1
  ```
- **Green:** `core/clock.AnchoredClock` (anchor + monotonic elapsed time, strictly increasing by at least 1 µs); `create_app` uses it for `settings.fixed_clock`. Result: `16 passed`; full suite `311 passed`, 98%; mypy, ruff and lint-imports clean.

### TDD-S1-E1-S4: admin draft/publish API (generator lead)

- **Scope:** AC-10.1, AC-10.2, AC-10.4, AC-10.7, AC-10.8; NFR-01 decimal strings (admin_versioning_spec §2, §4).
- **Tests:** `tests/acceptance/test_ac_admin_versioning.py` (13 tests).
- **Red** (routers existed but were empty):
  ```
     7 E       AssertionError: {"detail":"Not Found"}
     7 E       assert 404 == 201
     4 E       assert 404 == 403
  13 failed, 2 warnings in 0.56s
  exit=1
  ```
  This is the right failure: no admin routes existed.
- **Green:**
  - `services/policy_version_service.py`: one generic lifecycle for both kinds (create_draft copies the active definition; update and delete are draft-only with 409 `POLICY_VERSION_IMMUTABLE`; publish validates with 422 `TEMPLATE_INVALID`/`POLICY_INVALID` + `details.violations`; 409 `DRAFT_EXISTS` and `ALREADY_PUBLISHED`; an audit event for every change);
  - `api/routers/_policy_admin.py`: one route builder used by both routers;
  - `api/schemas/decimals.py`: JSON numbers give 422 `DECIMAL_MUST_BE_STRING`.

  Result: `13 passed, 2 warnings in 0.65s`.
- **Refactor:** mypy strict rejected passing `type[RiskPolicyVersion] | type[TemplateVersion]` to the repository's *constrained* type parameter. It was changed to a *bound* parameter (`V: RiskPolicyVersion | TemplateVersion`), and ruff format wrapped the long test lines. Result: `66 passed` (admin + all integration tests), mypy `Success: no issues found in 59 source files`, lint-imports 4/4.

### TDD-S1-E2-S1: deterministic risk scoring rules (risk profiler agent)

- **Scope:** AC-01.2, AC-01.3, AC-01.4, AC-01.5, AC-01.6, AC-01.7 (domain half) and AC-10.6 (domain half); risk_profile_spec §2.1–2.6.
- **Tests:** `tests/unit/domain/test_risk_band_rules.py` (31 tests, including parametrised cases); reference answer sets in `tests/fixtures/answer_sets.py` (ANS_0/11/12/16/20/21/28/CAP24, copied verbatim from specs/stories/E2-S1.md).
- **Red #1** (module missing):
  ```
  E   ModuleNotFoundError: No module named 'app.domain.risk_band_rules'
  ERROR ../tests/unit/domain/test_risk_band_rules.py
  !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
  1 error in 0.05s
  exit=2
  ```
- **Red #2** (interface stub: dataclasses and signatures, every function `raise NotImplementedError`):
  ```
  E       NotImplementedError        (x31)
  FAILED ../tests/unit/domain/test_risk_band_rules.py::test_ac_01_band_boundaries[0]
  ...
  FAILED ../tests/unit/domain/test_risk_band_rules.py::test_ac_10_policy_is_a_parameter_v2_bands_rescore_ans_20
  31 failed in 0.10s
  exit=1
  ```
- **Green:** `app/domain/risk_band_rules.py` implements `score_answers`, `band_for_score`, `apply_caps`, `assess`, `effective_band`, plus `sorted_by_question_order` (the stored answer order, §3) and `AssessmentValidationError(code)`. Every number comes from the `RiskPolicyDefinition` argument. Result with branch coverage:
  ```
  app/domain/risk_band_rules.py                       89      0     24      0   100%
  31 passed in 0.23s
  ```
- **Refactor:** ruff format; import order fixed (`ruff --fix`) and one docstring shortened to the 120-column limit. Re-run: `31 passed in 0.02s`; mypy strict `Success: no issues found in 60 source files`; lint-imports `Contracts: 4 kept, 0 broken.`

### TDD-S1-E2-S2: risk profile service and API (risk profiler agent)

- **Scope:** AC-01.1–AC-01.8 (risk_profile_spec §2.4–2.5, §3, §4); NFR-02, NFR-03, NFR-04; app_spec §5.4 audit.
- **Tests:**
  - `tests/integration/services/test_risk_profile_service.py` (7 tests)
  - `tests/acceptance/test_ac_risk_profile.py` (16 tests)
- **Red #1** (service test module): `ImportError: cannot import name 'risk_profile_service' from 'app.services'`
- **Red #2** (acceptance module against empty router): `16 failed, 2 warnings in 0.53s`
- **Green:** `risk_assessment_repository.py`, `risk_profile_service.py`, `api/schemas/risk_profile.py`, `api/routers/risk_profile.py`. Result: `23 passed, 2 warnings in 0.53s`.
- **Refactor:** ruff format; `submit_assessment` split (`_score`, `_reject`) to stay under 50-line limit.

### TDD-S1-E3-S1: allocation template and goal-horizon rules (recommendation-engine-agent)

- **Scope:** AC-02.1–02.4, AC-04.1–04.5 (`recommendation_spec` §2.1–2.5), NFR-08.
- **Tests:** `tests/unit/domain/test_goal_horizon_policy.py` (23 collected), `tests/unit/domain/test_allocation_template_policy.py` (67 collected).
- **Red #1** (modules missing): `ModuleNotFoundError: No module named 'app.domain.goal_horizon_policy'` / `allocation_template_policy`.
- **Red #2** (interface stubs `raise NotImplementedError`): `90 failed in 0.24s`.
- **Green:** `horizon_months`, `select_rule`, `order_goals`/`primary_goal`, `recommend`. Result: `90 passed in 0.27s`; branch coverage 100%.
- **Refactor:** ruff format; shortened test docstring.

### TDD-S1-E3-S2 & E3-S3: recommendation service, API, and in-flight version guarantees

- **Scope:** AC-02.1, AC-02.2, AC-02.5, AC-04.1, AC-04.3, AC-04.4, AC-10.5, AC-10.6.
- **Tests:** `tests/integration/services/test_recommendation_service.py`, `tests/acceptance/test_ac_recommendation.py`, `tests/acceptance/test_ac_in_flight_versions.py`.
- **Red:** Service and routes missing -> 404 / ImportError.
- **Green:** `recommendation_repository.py`, `recommendation_service.py`, `api/routers/recommendations.py`. Result: all tests passed.
- **Refactor:** strict typing, ruff 120-col wrapping, 100% domain branch coverage.


## Sprint 2: Holdings Valuation, NAV Feed, Drift & Snapshotting (2026-10-06)

### TDD-S2-E4-S1: Pure Domain Drift Policy & Valuation Rules (drift-calculator skill)

- **Scope:** AC-05.1, AC-05.2, AC-05.4, AC-05.5, AC-08.1; edge cases: zero holdings, half-even rounding `q2` with exact 100.00% sum reconciliation, customer with holdings but no recommendation, strict `drift > threshold` comparison.
- **Tests:** `tests/unit/domain/test_drift_policy.py` (9 tests, 100% statements, 100% branch coverage).
- **Red #1** (module missing): `ModuleNotFoundError: No module named 'app.domain.drift_policy'`.
- **Green:** Implemented `backend/app/domain/drift_policy.py`:
  - `value_holdings`: units × NAV with half-even rounding `q2` per asset class and sum to total value.
  - `current_allocation`: calculates percentages with `q2` rounding and applies largest-remainder reconciliation if rounded percentages differ from 100.00%.
  - `compute_drift`: calculates `drift_pct = abs(current% - target%)` per asset class; `breached = (drift_pct > threshold)` strict; sets `portfolio_breached = True` if any class exceeds threshold. If customer has no recommendation (`target=None`), `has_target=False` and all target/drift fields return `None`.
  - `calculate_goal_progress`: calculates `current_goal_value = q2(total_value * funding_share / 100)` and `percent_complete = q2(current_goal_value / target_amount * 100)`.
- **Coverage:** 100% statements (76/76), 100% branches (14/14).

### TDD-S2-E4-S2: ORM Models, Repositories, Migration 0003 & Append-Only Protection

- **Scope:** AC-05.1, AC-05.3, AC-08 groundwork (goal progress snapshots), NFR-01 (`DecimalText`), NFR-02 (append-only snapshots).
- **Tests:** `tests/architecture/test_append_only_tables.py`, `tests/integration/repositories/test_schema_migration.py`.
- **Red:** Missing models and database tables.
- **Green:**
  - ORM Models: `Holding` (unique on `(customer_id, asset_class_code)`), `NavPrice` (unique on `(asset_class_code, nav_date)`), `GoalProgressSnapshot` (protected with `protect_append_only` listener).
  - Repositories: `holding_repository.py`, `nav_repository.py`, `goal_snapshot_repository.py`.
  - Migration `0003_sprint2_holdings_nav_snapshots.py`: creates tables and seeds initial `2026-01-15` NAVs and customer holdings for Alice, Bob, Carol, Frank, and Grace.
  - Seed dataset: `backend/app/seed/nav_series.csv` with 30+ business days of synthetic NAV prices.

### TDD-S2-E4-S3: Holdings Service, NAV Feed Refresh & API Endpoints

- **Scope:** AC-05.1–05.7, AC-08.2, AC-08.4; NFR-04.
- **Tests:** `tests/integration/services/test_holdings_service.py`, `tests/integration/services/test_nav_feed_service.py`, `tests/acceptance/test_ac_holdings.py`, `tests/acceptance/test_ac_nav_feed.py`.
- **Red:** Endpoints `/api/v1/holdings` and `/api/v1/admin/nav-refresh` returned 404 Not Found.
- **Green:**
  - `holdings_service.py` & `api/routers/holdings.py`: `GET /api/v1/holdings` values customer holdings against newest NAVs and computes drift against latest recommendation, using the template version pinned to the recommendation.
  - `nav_feed_service.py` & `api/routers/admin_nav.py`: `POST /api/v1/admin/nav-refresh` advances NAV prices from CSV, creates immutable goal progress snapshots, and records audit events.
  - Role isolation verified: CUSTOMER and ADVISOR tokens receive 403 on `/admin/nav-refresh`; ADVISOR and ADMIN tokens receive 403 on `/holdings`.
## Sprint 3: Goals CRUD, Rebalancing Proposals & Execution, Goal Snapshots, Advisor Workbench, Admin Asset Classes (2026-10-06)

### TDD-S3-E5: Goals CRUD & Validation (AC-03, AC-08)

- **Scope:** AC-03.1–03.6, AC-08.1–08.3; goals CRUD with priority ordering (priority ASC, target_date ASC, created_at ASC), cumulative funding share ≤ 100.00% validation, automatic progress snapshotting on create/update and NAV refresh.
- **Tests:** `tests/unit/domain/test_goal_rules.py` (10 tests, 100% statements, 100% branches), `tests/acceptance/test_ac_goals.py` (7 tests).
- **Red:** `ModuleNotFoundError: No module named 'app.domain.goal_rules'`; `/api/v1/goals` returned 404.
- **Green:**
  - Implemented `app/domain/goal_rules.py` (`validate_goal`, `order_goals`, `primary_goal`).
  - Implemented `app/repositories/goal_repository.py` and `app/repositories/models/goal.py`.
  - Implemented `app/services/goals_service.py` & `app/api/routers/goals.py` (`GET /goals`, `POST /goals`, `GET /goals/{id}`, `PUT /goals/{id}`, `DELETE /goals/{id}`).
  - Full TDD cycle passing: 7/7 acceptance tests passing.

### TDD-S3-E6: Rebalancing Engine, Lifecycle & Stub Orders (AC-06, AC-07)

- **Scope:** AC-06.1–06.6, AC-07.1–07.6; proposal trigger on `drift > threshold`, exact BUY/SELL quantities (`ROUND_DOWN` 4dp on units, `ROUND_HALF_EVEN` 2dp on trade value, CASH settlement, negative-cash step-down guard), proposal accept/dismiss lifecycle, idempotent evaluations, stub orders creation (`FILLED_STUB`).
- **Tests:** `tests/unit/domain/test_rebalancing_policy.py` (10 tests, 100% statements, 100% branches), `tests/acceptance/test_ac_rebalancing.py` (7 tests).
- **Red:** Missing rebalancing domain policy, models, and endpoints.
- **Green:**
  - Implemented `app/domain/rebalancing_policy.py` (`propose_rebalance`, `_check_oversell`, `q4_down`).
  - Implemented ORM models: `RebalancingRecommendation`, `RebalancingLine`, `RebalancingDecision`, `StubOrder` (all protected with `protect_append_only`).
  - Migration `0004_sprint3_rebalancing_overrides_goals.py`: created all 5 new tables.
  - Implemented `app/repositories/rebalancing_repository.py`, `app/services/rebalancing_service.py`, and `app/api/routers/rebalancing.py` (`POST /evaluate`, `GET /recommendations`, `GET /recommendations/{id}`, `POST /recommendations/{id}/accept`, `POST /recommendations/{id}/dismiss`).
  - Full TDD cycle passing: 7/7 acceptance tests passing.

### TDD-S3-E7: Advisor Workbench & NFR-08 Architecture Mandate (AC-09)

- **Scope:** AC-09.1–09.8; advisor customer list with breach indicator, deep portfolio overview, risk-band override with reason code/note/audit, customer-safe history view, manual recommendation logging (`ADVISOR_MANUAL`), role and assignment isolation (403/404), and NFR-08 architecture mandate.
- **Tests:** `tests/unit/domain/test_advisor_override_rules.py` (6 tests, 100% statements, 100% branches), `tests/architecture/test_risk_band_override_mandate.py` (3 tests), `tests/acceptance/test_ac_advisor.py` (8 tests).
- **Red:** Missing advisor override validation rules, advisor routes, and architecture test assertions.
- **Green:**
  - Implemented `app/domain/advisor_override_rules.py` (`validate_risk_override`, `validate_manual_recommendation`).
  - Implemented `RiskBandOverride` model with append-only guard and `risk_override_repository.py`.
  - Implemented `tests/architecture/test_risk_band_override_mandate.py` proving no customer mutable band column exists and band changes only occur via `risk_assessments` or `risk_band_overrides`.
  - Implemented `advisor_service.py` and `app/api/routers/advisor.py` (`GET /advisor/customers`, `GET /advisor/customers/{id}/portfolio`, `POST /advisor/customers/{id}/risk-overrides`, `POST /advisor/customers/{id}/manual-recommendations`, `GET /advisor/customers/{id}/audit`).
  - Full TDD cycle passing: 8/8 acceptance tests passing.

### TDD-S3-E8: Admin Asset Classes Management & In-Flight Versions (AC-10)

- **Scope:** AC-10.1–10.9; asset classes CRUD, prevents deactivation of in-use active classes (`409 ASSET_CLASS_IN_USE`), in-flight version pinning.
- **Tests:** `tests/acceptance/test_ac_admin_asset_classes.py` (5 tests), `tests/acceptance/test_ac_in_flight_versions.py` (2 tests).
- **Red:** Missing asset class endpoints and in-use validation.
- **Green:**
  - Implemented `app/repositories/asset_class_repository.py`, `app/services/asset_class_service.py`, and `app/api/routers/admin_asset_classes.py` (`GET /admin/asset-classes`, `POST /admin/asset-classes`, `PATCH /admin/asset-classes/{code}`).
  - Full TDD cycle passing: all acceptance tests passing.



