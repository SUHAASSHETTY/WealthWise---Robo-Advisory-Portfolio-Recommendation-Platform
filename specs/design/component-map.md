# Sprint 1 component map

Paths are relative to the repo root. "Owns" means the story creates the file, or is the first to change it in Sprint 1. Existing scaffold files are marked *(extend)*.

| Story | Layer | Files owned | Tests owned |
|---|---|---|---|
| E1-S1 | Repository | `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_sprint1_schema.py`, `backend/migrations/LOCKED_HASHES.txt`, `backend/app/repositories/models/{user,customer,asset_class,risk_policy_version,goal,risk_assessment,recommendation,audit_event}.py`, `backend/app/repositories/models/template_version.py` *(extend: created_by, published_by)*, `backend/app/repositories/models/__init__.py` *(extend)*, `backend/app/repositories/guards.py` *(extend: append-only guard)*, `backend/app/repositories/errors.py` *(extend: AppendOnlyViolation)*, `backend/app/repositories/policy_version_repository.py` (`active_published`, `get`, `next_version_no`, `insert_draft`), `backend/app/repositories/audit_repository.py` (`insert_audit_event`) | `tests/conftest.py` *(extend: migrated DB fixture)*, `tests/integration/repositories/test_schema_migration.py`, `tests/integration/repositories/test_version_guards.py`, `tests/architecture/test_published_templates_immutable.py` *(extend)*, `tests/architecture/test_append_only_tables.py`, `tests/architecture/test_band_reassignment_requires_override.py`, `tests/architecture/test_migrations_locked.py`, `tests/architecture/test_no_float_money.py` *(extend)* |
| E1-S2 | Types | `backend/app/domain/bands.py`, `backend/app/domain/template_version_validator.py` | `tests/unit/domain/test_bands.py`, `tests/unit/domain/test_template_version_validator.py`, `tests/fixtures/__init__.py`, `tests/fixtures/policy_definitions.py` |
| E1-S3 | Config | `backend/migrations/versions/0002_sprint1_seed.py`, `backend/app/core/security.py` *(extend: frank, grace stub tokens)*, `backend/app/core/config.py` *(extend: fixed_clock)*, `backend/app/main.py` *(extend: app.state.clock)*, `backend/app/api/deps.py` *(extend: get_clock, current_customer_id)*, `backend/app/repositories/customer_repository.py`, `backend/app/repositories/goal_repository.py` (read-only), `backend/app/services/customer_resolver.py`, `backend/app/services/errors.py` (`ServiceError(status, code, details)`), `backend/app/api/errors.py` *(extend: `ServiceError` → error envelope)* | `tests/integration/repositories/test_seed_migration.py`, `tests/integration/services/test_customer_resolver.py`, `tests/integration/api/test_clock_injection.py`, `tests/architecture/test_allocation_sum_invariant.py` *(extend: published templates from DB)*, `tests/architecture/test_no_wall_clock.py` |
| E2-S1 | Types | `backend/app/domain/risk_band_rules.py` | `tests/unit/domain/test_risk_band_rules.py`, `tests/fixtures/answer_sets.py` |
| E3-S1 | Types | `backend/app/domain/goal_horizon_policy.py`, `backend/app/domain/allocation_template_policy.py` | `tests/unit/domain/test_goal_horizon_policy.py`, `tests/unit/domain/test_allocation_template_policy.py` |
| E1-S4 | API | `backend/app/services/policy_version_service.py`, `backend/app/api/schemas/policy_versions.py`, `backend/app/api/schemas/decimals.py` (string-only decimal type → `422 DECIMAL_MUST_BE_STRING`), `backend/app/api/routers/admin_risk_policies.py`, `backend/app/api/routers/admin_template_versions.py`, `backend/app/main.py` *(extend: include routers)* | `tests/integration/services/test_policy_version_service.py`, `tests/acceptance/test_ac_admin_versioning.py`, `tests/architecture/test_routes_declare_roles.py` |
| E2-S2 | API | `backend/app/repositories/risk_assessment_repository.py`, `backend/app/services/risk_profile_service.py`, `backend/app/api/schemas/risk_profile.py`, `backend/app/api/routers/risk_profile.py`, `backend/app/main.py` *(extend)* | `tests/integration/services/test_risk_profile_service.py`, `tests/acceptance/test_ac_risk_profile.py`, `tests/architecture/test_no_pii_in_logs.py` |
| E3-S2 | API | `backend/app/repositories/recommendation_repository.py`, `backend/app/services/recommendation_service.py`, `backend/app/api/schemas/recommendations.py`, `backend/app/api/routers/recommendations.py`, `backend/app/main.py` *(extend)* | `tests/integration/services/test_recommendation_service.py`, `tests/acceptance/test_ac_recommendation.py`, `tests/architecture/test_allocation_sum_invariant.py` *(extend: stored recommendations)* |
| E3-S3 | API | none new (service fixes only if tests expose gaps) | `tests/acceptance/test_ac_in_flight_versions.py` |

## Produces / Consumes

| Producer | Artefact | Consumers |
|---|---|---|
| E1-S1 | ORM models, `AppendOnlyViolation`, `PublishedVersionMutation` guards, migrated-DB fixture in `tests/conftest.py` | E1-S3, E1-S4, E2-S2, E3-S2 |
| E1-S1 | `policy_version_repository.active_published(model)`, `audit_repository.insert_audit_event(...)` | E1-S4, E2-S2 (active risk policy, audit), E3-S2 (active template, audit) |
| E1-S2 | `domain/bands.RiskBand`, `min_band` | E2-S1, E3-S1, E2-S2, E3-S2 |
| E1-S2 | `template_version_validator.parse_risk_policy`, `parse_template_version`, `validate_risk_policy`, `validate_template_version` | E1-S3 (seed check), E1-S4 (publish), E2-S1, E3-S1 (typed definitions) |
| E1-S2 | `tests/fixtures/policy_definitions.py` (`RISK_POLICY_V1`, `RISK_POLICY_V2_AC_10_1`, `TEMPLATE_V1`, `TEMPLATE_V2_AC_10_5`, `TEMPLATE_AGGRESSIVE_100_01`) | all later stories' tests |
| E1-S3 | `services/errors.ServiceError` + envelope mapping in `api/errors.py` | E1-S4, E2-S2, E3-S2 |
| E1-S3 | Seeded v1 rows, users/customers, goal IDs; `deps.get_clock`; `deps.current_customer_id`; `customer_resolver` | E1-S4, E2-S2, E3-S2, E3-S3 |
| E1-S4 | Admin publish routes; `api/schemas/decimals.py` (string-only decimal type) | E3-S2 (decimal strings in responses), E3-S3 (publish via HTTP) |
| E2-S1 | `risk_band_rules.assess`, `effective_band`, `AssessmentValidationError`; `tests/fixtures/answer_sets.py` | E2-S2, E3-S2, E3-S3 |
| E2-S2 | **`risk_profile_service.effective_band(customer_id)`** | **E3-S2** (recommendation band and `risk_band_source_id`) |
| E3-S1 | `goal_horizon_policy.horizon_months`, `select_rule`, `primary_goal`; `allocation_template_policy.recommend`, `Allocation` | E3-S2 |
| E3-S2 | `recommendation_service.latest_for(customer_id)` | E3-S3; later holdings/drift (AC-05) |

## Parallel-group note

E1-S4 and E2-S2 run in parallel in group C. Both need the active-version query and the audit writer, so those live in E1-S1's repositories (group A), not in either group C story. Error-envelope mapping (`ServiceError`) is owned by E1-S3 (group B) for the same reason. The only file both group C stories touch is `backend/app/main.py` (one `include_router` line each); merge both lines. `api/schemas/decimals.py` is owned by E1-S4; E2-S2 has no decimal fields, and E3-S2 (group D) consumes it.
