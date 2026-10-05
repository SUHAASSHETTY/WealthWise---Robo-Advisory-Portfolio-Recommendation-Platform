# Advisor Workbench Spec

**Owns:** AC-09 · **Related:** risk_profile (effective band), recommendation (manual recommendations), holdings, goal_tracker, rebalancing (read views) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

Give advisors one place to:
- review an assigned customer's risk profile, goals, holdings, drift, recommendations and open rebalancing proposals;
- **override the customer's risk band** with a reason and a supporting note;
- **log a manual recommendation**.

Every advisor action is append-only and audited with the actor and timestamp.

## 2. Domain rules

### 2.1 Assignment

- Each customer has an `advisor_id`, and an advisor can access **only assigned customers**. Others return `404 CUSTOMER_NOT_FOUND`, which avoids leaking that a customer exists.
- Seed data assigns `dan.advisor` to Alice, Bob and Carol.

### 2.2 Risk-band override

| Field | Rule | Error (422) |
|---|---|---|
| `new_band` | `CONSERVATIVE` \| `MODERATE` \| `AGGRESSIVE` | `BAND_INVALID` |
| `reason_code` | `CLIENT_CIRCUMSTANCES_CHANGED` \| `QUESTIONNAIRE_MISUNDERSTOOD` \| `SUITABILITY_REVIEW` \| `OTHER` | `REASON_CODE_INVALID` |
| `note` | Trimmed, 20–1000 characters | `OVERRIDE_NOTE_INVALID` |
| `new_band` vs current effective band | Must differ | `OVERRIDE_SAME_BAND` |
| Customer has at least one assessment | Required | `409 RISK_PROFILE_REQUIRED` |

**Effects (one transaction):**
1. Insert a `risk_band_overrides` row recording `previous_band`, `new_band`, `reason_code`, `note`, `actor_user_id`, `actor_role = ADVISOR` and `created_at` (UTC).
2. Insert an `audit_events` row with `action = RISK_BAND_OVERRIDDEN`.

**Rules after an override:**
- The customer's **effective band** becomes `new_band` (risk_profile §2.5).
- The original assessment row is untouched.
- Existing recommendations are **not** regenerated; the next recommendation uses the overridden band.
- A later customer self-assessment produces a new effective band. The override stays in history.

**NFR-08 rule:** a customer's band may change *only* by inserting a `risk_assessments` row (customer self-assessment) or a `risk_band_overrides` row (advisor). No other code path may produce a different effective band. This is enforced by architecture tests.

### 2.3 Manual recommendation

- **Allocation:** `allocation` lists every **active** asset class exactly once. Each `target_pct` is a 2 dp decimal string in [0.00, 100.00], and **Σ = 100.00 exactly**. Violations return `422 ALLOCATION_SUM_INVALID` or `422 ALLOCATION_CLASSES_INVALID`.
- **Note:** `note` is 20–1000 characters.
- **Stored as:** a `recommendations` row with `source = ADVISOR_MANUAL`, `risk_band` = the effective band, `template_version_id` = the active template version (threshold source), `created_by` = the advisor, plus its allocation rows. Audit action `MANUAL_RECOMMENDATION_LOGGED`.
- **Effect:** it becomes the customer's latest recommendation, and so the drift target.

### 2.4 Customer visibility

- The customer sees `source = "ADVISOR_OVERRIDE"` and the `reason_code` in `GET /risk-profile` and its history.
- The advisor's free-text `note` is visible only to advisors.

## 3. Data model

**`risk_band_overrides`** (append-only)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `customer_id` | UUID FK | |
| `previous_band` | enum | |
| `new_band` | enum | |
| `reason_code` | enum | |
| `note` | text | |
| `actor_user_id` | UUID FK | |
| `actor_role` | enum | Always `ADVISOR` |
| `created_at` | timestamp UTC | |

`customers` gains `advisor_id` (UUID FK) and `kyc_verified` (BOOL). `audit_events` is defined in app_spec §5.4.

## 4. API contract (role: ADVISOR)

| Method & path | Request | Success | Errors |
|---|---|---|---|
| `GET /api/v1/advisor/customers` | — | `200 [{customer_id, display_name, effective_band, band_source, portfolio_breached, open_rebalance_id?}]` | 401, 403 |
| `GET /api/v1/advisor/customers/{customer_id}/portfolio` | — | `200 {customer:{id, display_name, kyc_verified}, risk_profile:{band, source, as_of}, goals:[…with progress], holdings:{…holdings shape}, latest_recommendation:{…}, open_rebalance:{…}?}` | 404 |
| `POST /api/v1/advisor/customers/{customer_id}/risk-overrides` | `{new_band, reason_code, note}` | `201 {override_id, previous_band, new_band, reason_code, actor_user_id, created_at}` | 404, 409 `RISK_PROFILE_REQUIRED`, 422 (§2.2) |
| `POST /api/v1/advisor/customers/{customer_id}/manual-recommendations` | `{allocation:[{asset_class, target_pct}], note}` | `201 {recommendation shape, source:"ADVISOR_MANUAL"}` | 404, 409 `RISK_PROFILE_REQUIRED`, 422 |
| `GET /api/v1/advisor/customers/{customer_id}/audit` | — | `200 [{occurred_at, action, actor_role, actor_user_id, entity_type, entity_id, details}]`, newest first | 404 |

Logs carry the advisor ID, customer ID, override ID and reason code. They never carry the note, the bands or any values.

## 5. Acceptance criteria

**AC-09**: An advisor can override a customer's risk band with a reason and supporting note, and the override is audited with actor and timestamp.

- **AC-09.1 Override.**
  - **Given** Bob's effective band is MODERATE (from an assessment), `dan.advisor` is signed in, and the clock is 2026-01-20T10:00:00Z
  - **When** Dan posts `{new_band:"CONSERVATIVE", reason_code:"CLIENT_CIRCUMSTANCES_CHANGED", note:"Client retiring in 18 months; needs capital stability."}`
  - **Then:**
    - the response is `201` with `previous_band = "MODERATE"`, `new_band = "CONSERVATIVE"`, `actor_user_id = Dan` and `created_at = "2026-01-20T10:00:00Z"`;
    - Bob's `GET /risk-profile` returns `CONSERVATIVE` with `source = "ADVISOR_OVERRIDE"`.
- **AC-09.2 Audit record.**
  - **Given** AC-09.1
  - **When** Dan calls `GET /api/v1/advisor/customers/{bob}/audit`
  - **Then** it includes `RISK_BAND_OVERRIDDEN`, `actor_role = ADVISOR`, Dan's ID, the timestamp and the override ID, and `details` contains no note text.
- **AC-09.3 Reason and note required.**
  - **Given** Dan is signed in
  - **When** an override has no `reason_code`
  - **Then** the response is `422 REASON_CODE_INVALID`.
  - **When** the note is "Client asked" (12 characters)
  - **Then** `422 OVERRIDE_NOTE_INVALID`.
  - In both cases no row is created.
- **AC-09.4 Same band rejected.**
  - **Given** Bob's effective band is CONSERVATIVE
  - **When** Dan overrides to CONSERVATIVE
  - **Then** the response is `422 OVERRIDE_SAME_BAND`.
- **AC-09.5 History preserved.**
  - **Given** AC-09.1
  - **When** Bob's history is fetched
  - **Then** both the original assessment (MODERATE) and the override (CONSERVATIVE, with reason code) are present.
  - An attempted UPDATE on `risk_band_overrides` raises `AppendOnlyViolation`.
- **AC-09.6 Role and assignment boundary.**
  - **Given** a CUSTOMER token
  - **When** it calls any `/api/v1/advisor/*` route
  - **Then** the response is `403 FORBIDDEN_ROLE`.
  - **Given** an advisor not assigned to Bob
  - **When** they call Bob's portfolio
  - **Then** the response is `404`.
- **AC-09.7 Reassignment needs an override record (NFR-08).**
  - **Given** the codebase
  - **When** architecture tests run
  - **Then** no repository or service writes a band anywhere except `risk_assessments` and `risk_band_overrides`, and no table has a mutable band column for customers.
- **AC-09.8 Manual recommendation.**
  - **Given** Dan and Alice
  - **When** Dan logs EQUITY 40.00, DEBT 40.00, GOLD 10.00, CASH 10.00 with a note of 20 or more characters
  - **Then:**
    - the response is `201` with `source = "ADVISOR_MANUAL"`;
    - it is Alice's latest recommendation;
    - her holdings drift uses 40/40/10/10.
  - **When** he submits allocations summing to 99.99
  - **Then** the response is `422 ALLOCATION_SUM_INVALID`.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | Manual allocation percentages are Decimal 2 dp; exact-100 check |
| NFR-02 | Overrides, manual recommendations and audit events are append-only |
| NFR-03 | Notes, bands and values are not logged; advisor views expose PII only in API responses, never in logs |
| NFR-04 | ADVISOR role plus assignment check at the API and service boundary |
| NFR-08 | Override record required for any advisor reassignment (AC-09.7) |
