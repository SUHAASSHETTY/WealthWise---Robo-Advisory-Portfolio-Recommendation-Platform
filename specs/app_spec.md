# WealthWise: Application Spec (root)

**Status:** v1.0 · **Owner:** AI-Native Engineer (spec author) · **Source:** BC-AINE-008 brief, `docs/business-case.md`

This is the root specification. It defines the system boundary, shared conventions, cross-cutting rules and the map from every acceptance criterion and NFR to the feature spec that owns it. **The specs win over the code (Spec-Is-Truth).** If code and a spec disagree, update the spec in a reviewed PR, then regenerate the code.

---

## 1. Purpose

WealthWise is a rule-based robo-advisory platform. It lets retail customers:
- profile their risk;
- receive a deterministic asset allocation tuned to their goal horizon;
- track goals;
- act on rebalancing proposals when their portfolio drifts.

Advisors can review customers and override them with an audit record. Administrators manage versioned investment policies.

## 2. Feature specs

| Feature | Spec | Owns ACs |
|---|---|---|
| Risk profile | [risk_profile_spec.md](risk_profile_spec.md) | AC-01 |
| Recommendation | [recommendation_spec.md](recommendation_spec.md) | AC-02, AC-04 |
| Holdings and drift | [holdings_spec.md](holdings_spec.md) | AC-05 |
| Rebalancing | [rebalancing_spec.md](rebalancing_spec.md) | AC-06, AC-07 |
| Goal tracker | [goal_tracker_spec.md](goal_tracker_spec.md) | AC-03, AC-08 |
| Advisor workbench | [advisor_workbench_spec.md](advisor_workbench_spec.md) | AC-09 |
| Admin and versioning | [admin_versioning_spec.md](admin_versioning_spec.md) | AC-10 |

## 3. Glossary

| Term | Meaning |
|---|---|
| **Asset class** | One of the managed classes. Seeded classes: `EQUITY`, `DEBT`, `GOLD`, `CASH`. |
| **Risk band** | `CONSERVATIVE` \| `MODERATE` \| `AGGRESSIVE` |
| **Risk policy version** | Immutable-once-published bundle of questionnaire, points, band thresholds and caps |
| **Template version** | Immutable-once-published bundle of per-band allocation templates, horizon-adjustment rules and the drift threshold |
| **Effective risk band** | The band from the customer's most recent risk event: the latest assessment or advisor override, whichever is newer |
| **Recommendation** | Stored target allocation for a customer: system-generated or advisor-manual |
| **NAV** | Net asset value per unit for an asset class on a date (stubbed daily feed) |
| **Drift** | `abs(current_pct − target_pct)` per asset class, in percentage points |

## 4. Architecture

### 4.1 Layers

The backend is layered: **api → services → repositories → domain**.

| Package | Responsibility | May import |
|---|---|---|
| `backend/app/domain/` | Pure business rules: scoring, allocation, horizon adjustment, drift, rebalancing math, goal progress, policy validation. No I/O, no framework. | stdlib only (`decimal`, `dataclasses`, `enum`, `datetime`, `typing`) |
| `backend/app/repositories/` | SQLAlchemy models and data access; maps rows ↔ domain objects | `domain`, `core` |
| `backend/app/services/` | Use-case orchestration, transactions, audit writing, authorisation of *ownership* | `domain`, `repositories`, `core` |
| `backend/app/api/` | FastAPI routers, Pydantic request/response schemas, auth dependencies (role boundary) | `services`, `domain` (types and enums only), `core` |
| `backend/app/core/` | Config, logging, DB engine/session, security primitives, clock | stdlib, third-party only (never `api`, `services` or `repositories`) |

Enforcement:
- **import-linter** contracts in `backend/pyproject.toml`;
- structural tests in `tests/architecture/`;
- see [`docs/harness/harness-overview.md` §8.1b](../docs/harness/harness-overview.md) for why the Harness layer hook doesn't cover this layout.

### 4.2 Frontend

React + Vite + TypeScript in `frontend/`:
- **Routes:** a customer area (`/risk-profile`, `/goals`, `/recommendation`, `/holdings`, `/rebalancing`), `/advisor/*` and `/admin/*`.
- **Layout:** at least one responsive layout, checked at 375 px and 1280 px.
- **Money:** the frontend never does money arithmetic. It renders decimal strings from the API.

## 5. Cross-cutting rules

### 5.1 Decimal arithmetic (NFR-01)

| Quantity | Python type | Scale | Rounding | DB storage |
|---|---|---|---|---|
| Money (values, amounts) | `Decimal` | 2 dp | `ROUND_HALF_EVEN` | TEXT via `DecimalText(scale=2)` TypeDecorator |
| Percent (allocation, current %, drift, threshold, funding share) | `Decimal` | 2 dp | `ROUND_HALF_EVEN` | TEXT via `DecimalText(scale=2)` |
| Units / quantities | `Decimal` | 4 dp | `ROUND_DOWN` (never over-trade) | TEXT via `DecimalText(scale=4)` |
| NAV per unit | `Decimal` | 4 dp | `ROUND_HALF_EVEN` | TEXT via `DecimalText(scale=4)` |

- Arithmetic runs in `decimal.localcontext()` with `prec=28`. Quantise **only** at the points named in the feature specs.
- **No `float` anywhere in money, percent or quantity paths.** No SQLAlchemy `Float` columns. No `Numeric` columns on SQLite, because SQLite stores them as REAL and loses precision. Constructing a Decimal from a float is forbidden; construct from `str` or `int`.
- **JSON:** every decimal is serialised as a **string** (e.g. `"62.50"`), and the API rejects JSON numbers for decimal inputs with `422 DECIMAL_MUST_BE_STRING`.

### 5.2 Determinism

- Domain functions are pure: same inputs give the same output.
- "Today" comes from an injectable `Clock` (`core/clock.py`), never `date.today()` inside domain or services. Tests use a fixed clock.
- Every generated artefact stores the version IDs and inputs needed to reproduce it.

### 5.3 Append-only records (NFR-02)

These tables are **insert-only**: `risk_assessments`, `risk_band_overrides`, `recommendations`, `recommendation_allocations`, `rebalancing_recommendations`, `rebalancing_lines`, `rebalancing_decisions`, `goal_progress_snapshots` and `audit_events`.
- Repositories expose no update or delete for them.
- A repository-level guard raises `AppendOnlyViolation` on any attempted UPDATE or DELETE (SQLAlchemy `before_update`/`before_delete` events).
- "Current state" is always **derived** (e.g. the effective risk band is the newest event), never stored in a mutable column.

### 5.4 Audit

Every state-changing use case writes an `audit_events` row in the same transaction. The row holds: `id`, `occurred_at` (UTC), `actor_user_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `correlation_id`, and `details` (JSON). `details` must not contain PII or position values; only IDs, enums and version numbers are allowed.

### 5.5 Authentication and roles (NFR-04)

- `POST /api/v1/auth/login` takes `{username, password}` and returns `{access_token, role, expires_at}`. The token is an HS256 JWT signed with `WEALTHWISE_JWT_SECRET` and lasts 60 minutes.
- Passwords are hashed with bcrypt. Seeded **synthetic** users: `alice.customer`, `bob.customer`, `carol.customer` (CUSTOMER); `dan.advisor` (ADVISOR); `erin.admin` (ADMIN).
- **The boundary is the API layer:**
  - every router declares `Depends(require_role(...))`;
  - customer routes resolve the customer from the token (`/me` semantics) and never take a `customer_id` path parameter;
  - advisor routes live under `/api/v1/advisor/*` and admin routes under `/api/v1/admin/*`.
- **Status codes:**
  - wrong role → `403 FORBIDDEN_ROLE`;
  - missing or invalid token → `401 UNAUTHENTICATED`;
  - a customer reaching another customer's resource → `404` (no existence leak).

### 5.6 Logging (NFR-03, NFR-06)

- Logs are structured JSON lines on stdout: `ts`, `level`, `logger`, `message`, `correlation_id`, plus allow-listed `extra` keys.
- Middleware reads `X-Request-ID` or generates a UUID4, binds it to the log context, and echoes it in the response header.
- **Allow-listed log fields:** IDs (UUIDs), enums, version numbers, counts, durations, HTTP method/path template/status.
- **Never logged:**
  - names, emails, usernames, dates of birth, passwords or tokens;
  - money values, units, NAV-times-units, target amounts;
  - percentages tied to a customer, and risk bands tied to a customer.
- A log filter drops non-allow-listed keys. A test asserts no seeded PII or value string appears in captured logs.

### 5.7 Errors

Errors use the envelope `{"error": {"code": "UPPER_SNAKE", "message": "...", "details": {}}}`.

| Status | Meaning |
|---|---|
| 400 | Malformed request |
| 401 | Unauthenticated |
| 403 | Wrong role |
| 404 | Not found or not owned |
| 409 | State conflict (e.g. immutable version, already decided) |
| 422 | Domain validation failure |

### 5.8 Health (NFR-07)

`GET /health` (no auth) returns `200 {"status":"ok","db":"connected"}` after a `SELECT 1`, or `503` otherwise. It must respond in **≤ 1 s** within 1 s of startup completing; a test enforces this.

### 5.9 Migrations and policy data (NFR-05)

- Alembic migrations live in `backend/migrations/versions/`. A merged migration is **never edited or deleted**; changes are new revisions only. A test compares migration file hashes to `backend/migrations/LOCKED_HASHES.txt`.
- The v1 risk policy, v1 templates, asset classes and synthetic seed data are inserted by data migrations or seed scripts as **new rows**.
- Policy changes at runtime create new version rows (see admin spec); published rows are never updated.

### 5.10 Synthetic data

All seed data is fictional:
- 3 customers with holdings across all 4 asset classes;
- 2 goals per customer;
- a deterministic NAV series in `backend/app/seed/nav_series.csv` covering at least 30 business days.

## 6. Acceptance criteria map

| AC | Summary (from brief) | Spec |
|---|---|---|
| AC-01 | Questionnaire of ≥ 6 questions; deterministic scoring assigns a band | risk_profile |
| AC-02 | Band selects a versioned template; percentages always sum to 100 | recommendation |
| AC-03 | Goals with target_amount, target_date and priority; multiple per customer | goal_tracker |
| AC-04 | Recommendation maps to band and goal horizon; deterministic | recommendation |
| AC-05 | Holdings value per asset class; drift = abs(current% − target%) | holdings |
| AC-06 | Rebalance proposed when any drift exceeds threshold (default 5%) | rebalancing |
| AC-07 | BUY/SELL quantities with recommendation ID; accept or dismiss with audit | rebalancing |
| AC-08 | percent_complete = current_goal_value / target_amount, updated each NAV refresh | goal_tracker |
| AC-09 | Advisor override with reason and note, audited with actor and timestamp | advisor_workbench |
| AC-10 | Versioned rules and templates; published immutable; in-flight customers keep their version | admin_versioning |

Each AC is written as Given–When–Then scenarios in its owning spec, numbered `AC-NN.k`.

**Test tagging rules:**
- **Python tests:** use `@pytest.mark.ac("AC-NN")` and a function name starting `test_ac_NN_`.
- **Playwright tests:** the title starts with `AC-NN:`.

## 7. NFR map

| NFR | Requirement | Specs affected | Primary enforcement |
|---|---|---|---|
| NFR-01 | Fixed-point money, %, drift | recommendation, holdings, rebalancing, goal_tracker, admin_versioning | §5.1; `tests/architecture/test_no_float_money.py` |
| NFR-02 | Append-only assignments, recommendations, rebalancing actions, overrides | risk_profile, recommendation, rebalancing, advisor_workbench | §5.3; append-only guard tests |
| NFR-03 | No PII or positions in logs | all | §5.6; log-capture test; PII hook |
| NFR-04 | Auth boundary at controller; roles separated | all API contracts; advisor_workbench; admin_versioning | §5.5; `tests/architecture/test_routes_declare_roles.py` |
| NFR-05 | Append-only DB, policy and template migrations | admin_versioning; app (migrations) | §5.9; migration hash lock test |
| NFR-06 | Structured JSON logs with correlation IDs | app | §5.6 |
| NFR-07 | Health 200 within 1 s of startup | app | §5.8 |
| NFR-08 | Architecture rules as tests: allocations sum to 100; published templates immutable; band reassignment needs an override audit record | recommendation, admin_versioning, risk_profile, advisor_workbench | `tests/architecture/` |

## 8. API surface (summary)

All routes are under `/api/v1` except `/health`. The feature specs hold the full contracts.

| Area | Routes | Role |
|---|---|---|
| Auth | `POST /auth/login` | public |
| Risk profile | `GET /risk-profile/questionnaire`, `POST /risk-profile/assessments`, `GET /risk-profile`, `GET /risk-profile/history` | CUSTOMER |
| Goals | `POST/GET /goals`, `GET/PUT /goals/{goal_id}`, `GET /goals/{goal_id}/progress` | CUSTOMER |
| Recommendation | `POST /recommendations`, `GET /recommendations/latest`, `GET /recommendations` | CUSTOMER |
| Holdings | `GET /holdings` | CUSTOMER |
| Rebalancing | `POST /rebalancing/evaluate`, `GET /rebalancing/recommendations`, `GET /rebalancing/recommendations/{id}`, `POST /rebalancing/recommendations/{id}/accept`, `POST /rebalancing/recommendations/{id}/dismiss` | CUSTOMER |
| Advisor | `GET /advisor/customers`, `GET /advisor/customers/{id}/portfolio`, `POST /advisor/customers/{id}/risk-overrides`, `POST /advisor/customers/{id}/manual-recommendations`, `GET /advisor/customers/{id}/audit` | ADVISOR |
| Admin | `/admin/risk-policies…`, `/admin/template-versions…`, `/admin/asset-classes…`, `POST /admin/nav-refresh` | ADMIN |
| Health | `GET /health` | public |

## 9. Out of scope

- Real brokerage or exchange integration.
- Real-time market data.
- Multi-currency or FX.
- Tax optimisation.
- Real KYC (a stub `customers.kyc_verified` flag is used).
- ML recommendations.
- Production deployment, secrets management and multi-region.
