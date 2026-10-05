# Risk Profile Spec

**Owns:** AC-01 · **Related:** advisor_workbench (overrides), admin_versioning (policy versions) · **Root:** [app_spec.md](app_spec.md)

## 1. Purpose

A customer answers a scored questionnaire and the system assigns a risk band (`CONSERVATIVE`, `MODERATE` or `AGGRESSIVE`) using the rules of the active **risk policy version**. Every assessment is stored append-only with its inputs and policy version, so any past band can be reproduced exactly.

## 2. Domain rules

### 2.1 Risk policy v1: questionnaire and points

Seven questions, each answered with exactly one option. Points are integers. The maximum total is **28**.

| # | Question code | Prompt | Options: code (points) |
|---|---|---|---|
| 1 | `AGE` | What is your age? | `AGE_18_29` (4) · `AGE_30_39` (3) · `AGE_40_49` (2) · `AGE_50_59` (1) · `AGE_60_PLUS` (0) |
| 2 | `HORIZON` | When will you need most of this money? | `LT_3Y` (0) · `Y3_5` (1) · `Y5_7` (2) · `Y7_10` (3) · `GT_10Y` (4) |
| 3 | `INCOME_STABILITY` | How stable is your income? | `NO_REGULAR` (0) · `IRREGULAR` (1) · `STABLE_SINGLE` (2) · `STABLE_GROWING` (3) · `MULTIPLE_STABLE` (4) |
| 4 | `EMERGENCY_FUND` | How many months of expenses do you hold in savings? | `NONE` (0) · `LT_3M` (1) · `M3_6` (2) · `M6_12` (3) · `GT_12M` (4) |
| 5 | `LOSS_REACTION` | If your portfolio fell 20% in one month, you would… | `SELL_ALL` (0) · `SELL_SOME` (1) · `HOLD` (2) · `BUY_SOME` (3) · `BUY_MORE` (4) |
| 6 | `EXPERIENCE` | Which best describes your investing experience? | `NONE` (0) · `DEPOSITS_ONLY` (1) · `FUNDS_LT_3Y` (2) · `FUNDS_STOCKS_3_7Y` (3) · `ACTIVE_GT_7Y` (4) |
| 7 | `OBJECTIVE` | What is your main investment objective? | `PRESERVE` (0) · `INCOME` (1) · `BALANCED` (2) · `GROWTH` (3) · `AGGRESSIVE_GROWTH` (4) |

### 2.2 Score → band thresholds (v1)

`total_score = Σ points of the selected options`

| Total score (inclusive) | Computed band |
|---|---|
| 0 – 11 | `CONSERVATIVE` |
| 12 – 20 | `MODERATE` |
| 21 – 28 | `AGGRESSIVE` |

### 2.3 Caps (v1)

| Cap code | Condition | Effect |
|---|---|---|
| `NO_EMERGENCY_FUND` | `EMERGENCY_FUND` answer is `NONE` | The assigned band is at most `MODERATE`. A computed `AGGRESSIVE` becomes `MODERATE`; other bands are unchanged. |

`assigned_band = apply_caps(computed_band, answers)`. Band order is `CONSERVATIVE < MODERATE < AGGRESSIVE`.

### 2.4 Validation

An assessment is rejected with `422` if any of the following applies:
- a question is unanswered → `ANSWER_MISSING`;
- a question is answered twice → `ANSWER_DUPLICATE`;
- an unknown question code → `QUESTION_UNKNOWN`;
- an option that doesn't belong to its question → `OPTION_INVALID`;
- the submitted `policy_version_id` is not the currently active risk policy → `409 POLICY_VERSION_STALE`, so the client refetches the questionnaire.

### 2.5 Effective band

The **effective risk band** for a customer is the band of the newest event:
- an assessment (`assigned_band`), or
- an advisor override (`new_band`, see advisor_workbench).

Ordering is by `created_at`, then `id`. No mutable "current band" column exists anywhere (NFR-02, NFR-08). With no events, the effective band is `null` and dependent features return `409 RISK_PROFILE_REQUIRED`.

### 2.6 Domain functions (pure, `backend/app/domain/risk/`)

- `score_answers(policy, answers) -> int`
- `band_for_score(policy, score) -> RiskBand`
- `apply_caps(policy, band, answers) -> tuple[RiskBand, list[CapCode]]`
- `assess(policy, answers) -> AssessmentResult(total_score, computed_band, assigned_band, applied_caps)`
- `effective_band(assessments, overrides) -> EffectiveBand | None`

## 3. Data model

**`risk_assessments`** (append-only)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `customer_id` | UUID FK | |
| `risk_policy_version_id` | UUID FK | Policy used |
| `answers` | JSON | `[{question_code, option_code}]`, sorted by question order |
| `total_score` | INT | |
| `computed_band` | enum | Before caps |
| `assigned_band` | enum | After caps |
| `applied_caps` | JSON | List of cap codes |
| `created_at` | timestamp UTC | |

The questionnaire definition itself lives in `risk_policy_versions.definition` (see admin_versioning).

## 4. API contract (role: CUSTOMER)

| Method & path | Request | Success | Errors |
|---|---|---|---|
| `GET /api/v1/risk-profile/questionnaire` | — | `200 {policy_version_id, version_no, questions:[{code, prompt, order, options:[{code, label}]}]}`. **Points and thresholds are not exposed to customers.** | 401, 403 |
| `POST /api/v1/risk-profile/assessments` | `{policy_version_id, answers:[{question_code, option_code}]}` | `201 {assessment_id, total_score, computed_band, assigned_band, applied_caps, policy_version_no, created_at}` | 401, 403, 409 `POLICY_VERSION_STALE`, 422 (see §2.4) |
| `GET /api/v1/risk-profile` | — | `200 {risk_band, source: "ASSESSMENT"\|"ADVISOR_OVERRIDE", source_id, as_of}`, or `200 {risk_band: null}` | 401, 403 |
| `GET /api/v1/risk-profile/history` | — | `200 [{type, id, band, created_at, policy_version_no?, reason_code?}]`, newest first | 401, 403 |

Side effects of `POST …/assessments`:
- insert a `risk_assessments` row and an `audit_events` row (`action=RISK_ASSESSMENT_SUBMITTED`), in the same transaction;
- the log line carries `assessment_id` and `customer_id` only, never the band or answers.

## 5. Acceptance criteria

**AC-01**: A customer can complete a risk-profile questionnaire of at least 6 questions, and a deterministic scoring rule assigns a risk band (CONSERVATIVE / MODERATE / AGGRESSIVE).

- **AC-01.1 Questionnaire has ≥ 6 questions.**
  - **Given** risk policy v1 is active
  - **When** an authenticated customer calls `GET /api/v1/risk-profile/questionnaire`
  - **Then** the response has 7 questions, each with 5 options, and contains no point values.
- **AC-01.2 Moderate example.**
  - **Given** v1 is active
  - **When** the customer submits `AGE_30_39`, `Y7_10`, `STABLE_SINGLE`, `M3_6`, `HOLD`, `FUNDS_LT_3Y`, `BALANCED`
  - **Then** the response is `201` with `total_score = 16` and `assigned_band = "MODERATE"`.
- **AC-01.3 Band boundaries.**
  - **Given** v1 is active
  - **When** answer sets totalling 0, 11, 12, 20, 21 and 28 are scored (no caps triggered except where noted)
  - **Then** the bands are CONSERVATIVE, CONSERVATIVE, MODERATE, MODERATE, AGGRESSIVE and AGGRESSIVE respectively.
  - The answer sets for 0 and 11 use `EMERGENCY_FUND = NONE` and are unaffected by the cap.
- **AC-01.4 Cap applies.**
  - **Given** v1 is active
  - **When** the customer submits the maximum-points option for every question except `EMERGENCY_FUND = NONE` (total 24)
  - **Then** `computed_band = "AGGRESSIVE"`, `assigned_band = "MODERATE"` and `applied_caps = ["NO_EMERGENCY_FUND"]`.
- **AC-01.5 Determinism.**
  - **Given** the same policy version and the same answers
  - **When** they are scored 100 times, and also submitted twice through the API
  - **Then** every result has an identical `total_score`, `computed_band` and `assigned_band`.
- **AC-01.6 Invalid submissions.**
  - **Given** v1 is active
  - **When** a submission omits `OBJECTIVE`
  - **Then** the response is `422 ANSWER_MISSING` and no assessment row is created.
  - **When** a submission uses option `GT_10Y` for question `AGE`
  - **Then** the response is `422 OPTION_INVALID`.
- **AC-01.7 Append-only history.**
  - **Given** a customer with one assessment
  - **When** they submit a second assessment
  - **Then** both rows exist, `GET /risk-profile` returns the second band, and an attempted UPDATE on `risk_assessments` raises `AppendOnlyViolation`.
- **AC-01.8 Stale version.**
  - **Given** risk policy v2 was published after the client fetched v1
  - **When** the client submits with v1's `policy_version_id`
  - **Then** the response is `409 POLICY_VERSION_STALE`.

## 6. NFR mapping

| NFR | How it applies here |
|---|---|
| NFR-02 | `risk_assessments` is append-only; the effective band is derived |
| NFR-03 | Answers, scores and bands are never logged; only IDs |
| NFR-04 | All routes are CUSTOMER-only; the customer comes from the token |
| NFR-08 | Architecture test: no table has a mutable `risk_band` column; band reassignment by anyone other than the customer (via a new assessment) must go through `risk_band_overrides` |
