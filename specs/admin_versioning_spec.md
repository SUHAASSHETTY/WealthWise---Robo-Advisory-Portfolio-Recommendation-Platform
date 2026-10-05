# Admin & Versioning Spec

**Owns:** AC-10 · **Related:** risk_profile, recommendation, holdings, rebalancing (all consume policy versions) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

Administrators manage the investment policy as **versioned, immutable-once-published** artefacts:
- **risk policy versions** (questionnaire, points, band thresholds, caps);
- **template versions** (allocation templates per band, horizon rules, drift threshold);
- the **asset-class master**.

Publishing a new version affects only *new* assessments and recommendations. Customers already advised keep the version that was active at that time.

The stubbed **NAV feed** trigger is also an admin function.

## 2. Domain rules

### 2.1 Lifecycle

`DRAFT → PUBLISHED`. There is no other transition and no un-publishing.

- At most **one DRAFT per policy type** at a time.
- A new draft is created as a copy of the active published version's definition.
- DRAFT versions may be edited (`PUT`) or deleted.
- **PUBLISHED versions are immutable.** `PUT`/`DELETE` returns `409 POLICY_VERSION_IMMUTABLE`, and the repository guard raises `PublishedVersionMutation` on any ORM update or delete.
- **Active version** = the PUBLISHED version with the highest `version_no` for that type.
- `version_no` is a per-type integer sequence starting at 1. v1 of each type is inserted by a data migration.

### 2.2 Risk policy definition (JSON)

```json
{
  "questions": [
    {"code": "AGE", "order": 1, "prompt": "...",
     "options": [{"code": "AGE_18_29", "label": "18–29", "points": 4}]}
  ],
  "bands": [
    {"band": "CONSERVATIVE", "min_score": 0, "max_score": 11},
    {"band": "MODERATE", "min_score": 12, "max_score": 20},
    {"band": "AGGRESSIVE", "min_score": 21, "max_score": 28}
  ],
  "caps": [
    {"code": "NO_EMERGENCY_FUND", "question_code": "EMERGENCY_FUND",
     "option_code": "NONE", "max_band": "MODERATE"}
  ]
}
```

v1 content is specified in [risk_profile_spec.md §2](risk_profile_spec.md).

**Publish validation** (`422 POLICY_INVALID` with a `details.violations[]` list):
- **Questions:** at least 6, with unique codes and orders 1…n.
- **Options:** each question has 2–6 options with unique codes; points are integers 0–10.
- **Bands:** exactly the three bands, in order. The first `min_score` is 0, the last `max_score` equals the maximum achievable score, and the ranges are contiguous with no gaps or overlaps.
- **Caps:** each cap references an existing question, option and band.

### 2.3 Template version definition (JSON)

```json
{
  "templates": {
    "CONSERVATIVE": {"EQUITY": "20.00", "DEBT": "60.00", "GOLD": "10.00", "CASH": "10.00"},
    "MODERATE":     {"EQUITY": "50.00", "DEBT": "35.00", "GOLD": "10.00", "CASH": "5.00"},
    "AGGRESSIVE":   {"EQUITY": "75.00", "DEBT": "15.00", "GOLD": "7.50",  "CASH": "2.50"}
  },
  "horizon_rules": [
    {"code": "H_84_PLUS", "min_months": 84, "max_months": null, "shift": "0.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_60_83",   "min_months": 60, "max_months": 83,   "shift": "10.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_36_59",   "min_months": 36, "max_months": 59,   "shift": "20.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_12_35",   "min_months": 12, "max_months": 35,   "shift": "30.00", "from": "EQUITY", "to": "DEBT"},
    {"code": "H_0_11",    "min_months": 0,  "max_months": 11,   "shift": "ALL",   "from": "EQUITY", "to": "CASH"}
  ],
  "drift_threshold_pct": "5.00"
}
```

All decimals are strings. v1 content is specified in [recommendation_spec.md §2](recommendation_spec.md).

**Publish validation** (`422 TEMPLATE_INVALID` with violations):
- **Templates:** all three bands are present. Each has exactly one entry per **active** asset class. Each value is a decimal string with ≤ 2 dp in [0.00, 100.00], and **each band sums to exactly 100.00**.
- **Horizon rules:** they cover [0, ∞) contiguously with no overlap. `shift` is either `"ALL"` or a decimal in [0.00, 100.00]. `from` ≠ `to`, and both are active asset classes.
- **Drift threshold:** `drift_threshold_pct` is in (0.00, 50.00].

### 2.4 In-flight customers

- **Every consumer stores the version it used:**
  - `risk_assessments.risk_policy_version_id`;
  - `recommendations.template_version_id`.
- **Drift and rebalancing** read target percentages from the customer's *latest recommendation's* allocation rows, and the threshold from *that recommendation's* template version. They never read the newest template.
- **Only new actions use the newest version:** new assessments use the active risk policy; new recommendations use the active template version.

### 2.5 Asset-class master

- `asset_classes(code PK, name, is_active, display_order, created_at)`, seeded with `EQUITY`, `DEBT`, `GOLD` and `CASH`.
- Admins may add a class or rename one. Codes are immutable (`^[A-Z_]{2,20}$`).
- Deactivating a class referenced by the **active** template version returns `409 ASSET_CLASS_IN_USE`.
- A newly added class takes part only in template versions published after it was added.

### 2.6 NAV feed (stub)

- **Trigger:** `POST /api/v1/admin/nav-refresh` advances to the next date in `backend/app/seed/nav_series.csv` and inserts one `nav_prices` row per active asset class.
- **Schedule:** a configurable timer (`NAV_REFRESH_CRON`, default `"0 18 * * 1-5"`; disabled when `NAV_SCHEDULER_ENABLED=false`, which is the test default) can trigger the same refresh.
- **Idempotent:** if the next date already exists, the call returns `200 {status:"ALREADY_LOADED"}` with no side effects.
- **After inserting prices**, in the same service call:
  1. snapshot goal progress (goal_tracker);
  2. run the drift evaluation for every customer (rebalancing).
- **The cash NAV** is fixed at `1.0000`.

## 3. Data model

**`risk_policy_versions`** and **`template_versions`** share the same shape:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `version_no` | INT | Unique per table |
| `status` | enum | `DRAFT` \| `PUBLISHED` |
| `definition` | JSON | |
| `created_by` | UUID | |
| `created_at` | timestamp | |
| `published_by` | UUID, null | |
| `published_at` | timestamp, null | |

A partial unique index allows only one `DRAFT` per table.

**`asset_classes`**: see §2.5.

**`nav_prices`**: `asset_class_code`, `nav_date`, `nav` (DecimalText 4). Unique on (`asset_class_code`, `nav_date`).

## 4. API contract (role: ADMIN)

| Method & path | Success | Errors |
|---|---|---|
| `GET /api/v1/admin/risk-policies` | `200 [{id, version_no, status, published_at}]` | 401, 403 |
| `GET /api/v1/admin/risk-policies/{id}` | `200 {…, definition}` | 404 |
| `POST /api/v1/admin/risk-policies/drafts` | `201` draft copied from active | 409 `DRAFT_EXISTS` |
| `PUT /api/v1/admin/risk-policies/{id}` with `{definition}` | `200` | 409 `POLICY_VERSION_IMMUTABLE`, 422 `POLICY_INVALID` (schema-level) |
| `DELETE /api/v1/admin/risk-policies/{id}` | `204` (draft only) | 409 `POLICY_VERSION_IMMUTABLE` |
| `POST /api/v1/admin/risk-policies/{id}/publish` | `200 {version_no, status:"PUBLISHED"}` | 409 `ALREADY_PUBLISHED`, 422 `POLICY_INVALID` |
| `…/admin/template-versions…` | Same set of routes as risk policies | 409 as above, 422 `TEMPLATE_INVALID` |
| `GET /api/v1/admin/asset-classes` | `200 [ … ]` | |
| `POST /api/v1/admin/asset-classes` with `{code, name, display_order}` | `201` | 409 `ASSET_CLASS_EXISTS`, 422 |
| `PATCH /api/v1/admin/asset-classes/{code}` with `{name?, is_active?, display_order?}` | `200` | 409 `ASSET_CLASS_IN_USE` |
| `POST /api/v1/admin/nav-refresh` | `201 {nav_date, prices_loaded, goals_snapshotted, rebalances_proposed}` or `200 {status:"ALREADY_LOADED"}` | 409 `NAV_SERIES_EXHAUSTED` |

Every mutating call writes an `audit_events` row: `POLICY_DRAFT_CREATED`, `POLICY_DRAFT_UPDATED`, `POLICY_PUBLISHED`, `ASSET_CLASS_CHANGED`, `NAV_REFRESHED`.

## 5. Acceptance criteria

**AC-10**: Risk-band rules and asset-allocation templates are versioned, published versions are immutable, and in-flight customers continue on the version active at the time of their recommendation.

- **AC-10.1 Versioned rules.**
  - **Given** risk policy v1 is published
  - **When** an admin creates a draft, changes the MODERATE range to 12–19 and AGGRESSIVE to 20–28, and publishes it
  - **Then** v2 is `PUBLISHED`, v1 is still `PUBLISHED` and unchanged, and the active policy is v2.
- **AC-10.2 Published immutable (API).**
  - **Given** template v1 is published
  - **When** an admin calls `PUT /api/v1/admin/template-versions/{v1_id}`
  - **Then** the response is `409 POLICY_VERSION_IMMUTABLE` and v1's definition is byte-identical to before.
- **AC-10.3 Published immutable (persistence).**
  - **Given** a published template version
  - **When** code attempts an ORM update or delete on it
  - **Then** `PublishedVersionMutation` is raised and the transaction rolls back.
- **AC-10.4 Publish validation.**
  - **Given** a template draft whose AGGRESSIVE row sums to 100.01
  - **When** it is published
  - **Then** the response is `422 TEMPLATE_INVALID` and the violations name `AGGRESSIVE` and `sum=100.01`.
- **AC-10.5 In-flight recommendation.**
  - **Given** customer Alice got a MODERATE recommendation under template v1 (50/35/10/5)
  - **When** an admin publishes template v2 with MODERATE 45/40/10/5
  - **Then** Alice's `GET /recommendations/latest` still shows `template_version_no = 1` and 50/35/10/5, and her holdings drift is computed against 50/35/10/5.
  - **When** Alice then requests a new recommendation
  - **Then** it uses v2 (45/40/10/5).
- **AC-10.6 In-flight risk band.**
  - **Given** Bob was assessed MODERATE (score 20, `EMERGENCY_FUND` ≠ `NONE`) under risk policy v1
  - **When** policy v2 (from AC-10.1) is published
  - **Then** Bob's effective band is still MODERATE with `policy_version_no = 1`. A new assessment with the same answers under v2 yields AGGRESSIVE.
- **AC-10.7 Single draft.**
  - **Given** a risk-policy draft exists
  - **When** another draft is requested
  - **Then** the response is `409 DRAFT_EXISTS`.
- **AC-10.8 Role boundary.**
  - **Given** a CUSTOMER or ADVISOR token
  - **When** any `/api/v1/admin/*` route is called
  - **Then** the response is `403 FORBIDDEN_ROLE`.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-01 | Template percentages and the drift threshold are decimal strings, validated to 2 dp |
| NFR-04 | ADMIN-only routes |
| NFR-05 | Version rows are append-only once published; v1 is inserted by a data migration; migrations are never edited (hash lock test) |
| NFR-08 | `tests/architecture/test_published_templates_immutable.py`: an ORM update on a PUBLISHED row raises. `test_allocation_sum_invariant.py` validates every published template |
