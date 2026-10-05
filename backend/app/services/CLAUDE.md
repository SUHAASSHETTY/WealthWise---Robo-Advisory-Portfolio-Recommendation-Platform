# backend/app/services/: use cases

Services orchestrate one use case each: load data through repositories, call pure domain functions, persist results and audit records in **one transaction**, and return domain or DTO objects.

## Allowed imports

`app.domain`, `app.repositories` (through their public interfaces), `app.core` (clock, config, logging). Never `app.api`, `fastapi` or Pydantic API schemas.

## Rules

- **One service module per feature:**
  - `risk_profile_service.py`, `recommendation_service.py`, `goal_service.py`, `holdings_service.py`;
  - `rebalancing_service.py`, `advisor_service.py`, `policy_admin_service.py`, `nav_feed_service.py`.
- **No business arithmetic.** It belongs in `domain`; services only wire inputs to domain functions.
- **Single owner of state changes** (Harness code-gen rule 4). Each insert has exactly one call site. Pass IDs between services; never re-create records.
- **Audit in the same transaction.** Every state-changing method writes `audit_events` via `AuditRepository` with `actor_user_id`, `actor_role`, `action`, entity, `correlation_id` and non-PII `details`.
- **Ownership checks.** Customer-facing methods take a `customer_id` resolved from the token by the API layer, and query **scoped** by it. A record not owned by that customer raises `NotFound` (→ 404). Advisor methods verify `customers.advisor_id == advisor_id`.
- **Versions are pinned:**
  - recommendations record `template_version_id`;
  - drift and rebalancing read targets and threshold from the latest recommendation's version, never the newest template (admin_versioning §2.4).
- **NAV refresh** (`nav_feed_service.refresh`) runs in one transaction:
  1. insert prices;
  2. expire open proposals;
  3. snapshot goals;
  4. evaluate drift for every customer.
- **Logging:** one INFO line per use case with IDs, counts and outcome enums only.
- **Errors:** raise typed errors from `services/errors.py` (`NotFound`, `Conflict(code)`, `ValidationFailed(code, violations)`). The API maps them.
- **Tests:** `tests/integration/services/` against an in-memory SQLite DB with a fixed `Clock`. Assert final state and exact row counts.
