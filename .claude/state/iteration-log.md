# Iteration Log
<!-- Append-only. Do not edit or delete entries. -->

## Sprint 1 — Groups A, B, C, D, E (Foundations, Risk Profile, Recommendations, Policy Versioning)
- **Date:** 2026-10-05T23:59:00Z
- **Status:** PASS
- **Stories:** [E1-S1, E1-S2, E1-S3, E1-S4, E2-S1, E2-S2, E3-S1, E3-S2, E3-S3]
- **Mode:** lean
- **Summary:** Implemented Sprint 1 scope covering AC-01, AC-02, AC-04, and AC-10. Complete TDD red-green cycle with 338 passing tests, 98% total coverage (100% domain branch coverage), 62/62 contract API checks, zero broken import contracts, clean strict mypy, and clean ruff.
- **Checks:** 62 API checks passed, 0 Playwright checks (frontend out of scope for Sprint 1), 0 design checks (lean mode)
- **Coverage:** 98% (baseline: 95%)
- **Learned Rules Applied:** []

### Micro-DAG
- Phase 1 (Independent): [risk-band-rules, goal-horizon-policy, allocation-template-policy, template-version-validator]
- Phase 2 (Depends on Phase 1): [risk_profile_service, policy_version_service, recommendation_service]
- Phase 3 (Integrators): [api_routers, schema_migrations, contract_evaluator] (shared files: [backend/app/main.py, backend/app/api/routers/__init__.py])

## Sprint 2 — Epic E4 (Holdings Valuation, Daily NAV Feed, Allocation Drift & Goal Snapshotting)
- **Date:** 2026-10-06T00:30:00Z
- **Status:** PASS
- **Stories:** [E4-S1, E4-S2, E4-S3, E4-S4]
- **Mode:** lean
- **Summary:** Implemented Sprint 2 scope covering AC-05, stubbed daily NAV feed, Decimal drift calculation, pure domain drift_policy.py, and groundwork for AC-08 goal progress snapshotting. Complete TDD cycle with 360 passing tests, 98% backend coverage (100% domain statement and branch coverage), 6/6 contract API checks passing on eval.db, 12/12 Sprint 2 features passing (83/83 cumulative), 4/4 import contracts kept, strict mypy clean, and ruff clean.
- **Checks:** 6 API checks passed, 0 Playwright checks (frontend out of scope for Sprint 2), 0 design checks (lean mode)
- **Coverage:** 98% (baseline: 95%)
- **Learned Rules Applied:** []

### Micro-DAG
- Phase 1 (Independent): [drift-policy, nav-series-dataset, orm-models-holding-nav-snapshot]
- Phase 2 (Depends on Phase 1): [holding-repository, nav-repository, goal-snapshot-repository, migration-0003]
- Phase 3 (Integrators): [holdings-service, nav-feed-service, api-routers-holdings-admin-nav, contract-evaluator] (shared files: [backend/app/main.py])

## Sprint 3 — Epics E5, E6, E7, E8 (Goals CRUD & Progress, Rebalancing Engine & Orders, Advisor Workbench & Overrides, Admin Asset Classes)
- **Date:** 2026-10-06T01:25:00Z
- **Status:** PASS
- **Stories:** [E5-S1, E5-S2, E5-S3, E6-S1, E6-S2, E6-S3, E6-S4, E6-S5, E7-S1, E7-S2, E7-S3, E7-S4, E8-S1, E8-S2]
- **Mode:** lean
- **Summary:** Implemented Sprint 3 scope covering AC-03 (Goals CRUD with priority ordering and funding share validation), AC-06 & AC-07 (Rebalancing proposal evaluation, exact BUY/SELL unit calculation with ROUND_DOWN 4dp, CASH settlement, negative-cash step-down guard, proposal accept/dismiss lifecycle, stubbed orders FILLED_STUB), AC-08 (Goal progress snapshots on create/update and automatic evaluation on NAV refresh), AC-09 (Advisor workbench with assigned customers, breach indicators, deep portfolio overview, risk-band override with reason/note/audit, customer-safe history view, manual recommendation logging, NFR-08 architecture mandate), and AC-10 (Admin asset classes CRUD, in-use deactivation guard 409, and in-flight version pinning). 406 tests passed (100%), 95% total backend coverage, 10/10 contract API checks passed on eval.db, 17/17 Sprint 3 features passing (100/100 cumulative), 4/4 import contracts kept, strict mypy clean, and ruff clean.
- **Checks:** 10 API checks passed, 0 Playwright checks (backend focus), 0 design checks (lean mode)
- **Coverage:** 95% (100% domain branch/statement coverage on pure rules)
- **Learned Rules Applied:** []

### Micro-DAG
- Phase 1 (Independent): [goal_rules, rebalancing_policy, advisor_override_rules, orm-models-goal-rebalancing-override-stuborder]
- Phase 2 (Depends on Phase 1): [goal_repository, rebalancing_repository, risk_override_repository, asset_class_repository, migration-0004]
- Phase 3 (Integrators): [goals_service, rebalancing_service, advisor_service, asset_class_service, api-routers-goals-rebalancing-advisor-admin-asset-classes, contract-evaluator] (shared files: [backend/app/main.py])



