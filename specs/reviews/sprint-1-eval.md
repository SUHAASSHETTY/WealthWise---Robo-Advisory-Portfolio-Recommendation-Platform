# Evaluator Report — Sprint 1 (Groups A, B, C, D, E)

Date: 2026-10-05T23:59:00Z
VERDICT: PASS

## Summary

| Dimension | Scope | Result | Target | Status |
|---|---|---|---|---|
| Contract API Checks | 62 checks (api-001…062) | 62/62 passed | 62/62 | PASS |
| Features Passed | F001…F071 | 71/71 passed | 71/71 | PASS |
| Pytest Test Suite | Unit, Integration, Acceptance, Architecture | 338 passed | 100% | PASS |
| Code Coverage | Total backend | 98% (100% domain) | ≥ 80% | PASS |
| Architectural Layering | Import-linter contracts | 4/4 kept, 0 broken | 4/4 | PASS |
| Type Safety | Mypy strict mode | 0 errors (65 source files) | 0 errors | PASS |
| Code Style & Linting | Ruff lint & format | 0 errors (99 files clean) | 0 errors | PASS |
| Frontend Verification | Vitest, ESLint, TypeScript, Build | 6 tests passed, build clean | All pass | PASS |
| WealthWise Hook Tests | Invariant, immutability, PII, no-float | 18/18 cases passed | 18/18 | PASS |

---

## API Checks Summary (62/62 PASS)

- **api-001…006 [AC-10.1 / AC-10.8]:** GET initial active v1 template and risk policy versions (status PUBLISHED, version_no 1).
- **api-007…008 [AC-01.1 / AC-01.8]:** GET /api/v1/risk-profile/questionnaire (7 questions × 5 options, no internal points/scoring keys).
- **api-009…016 [AC-01.2–01.7 / NFR-02]:** Alice submits assessment ANS_16 → 201 Created (total_score=16, MODERATE, policy_version_no=1). Effective profile returns MODERATE. Second submission ANS_0 → CONSERVATIVE; history reflects append-only audit trail newest first.
- **api-017…023 [AC-01.3 / AC-01.4]:** Bob submits assessment ANS_0 → CONSERVATIVE. Frank submits ANS_28 → AGGRESSIVE. Grace submits ANS_20 → MODERATE. Validation errors 422 for missing questions and invalid options verified.
- **api-024…032 [AC-02.1 / AC-04.1 / AC-04.3 / AC-04.4]:** Alice requests recommendation with no goal → MODERATE base template (50/35/10/5). Frank requests recommendation with 48-month goal → AGGRESSIVE shifted 20 points EQUITY → DEBT (55/35/7.50/2.50). Grace requests recommendation with primary goal (29-month) → MODERATE shifted 30 points EQUITY → DEBT (20/65/10/5). Carol requests recommendation without risk assessment → 409 RISK_PROFILE_REQUIRED.
- **api-033…046 [AC-10.1–10.4 / AC-10.7]:** Admin template version lifecycle: create DRAFT v2 (copied from v1), reject concurrent second draft (409 DRAFT_EXISTS), update draft with invalid sum → publish rejected with 422 TEMPLATE_INVALID (violations list details), update draft with valid sum (45/40/10/5 for MODERATE) → publish successful (status PUBLISHED, version_no 2).
- **api-047…049 [AC-10.5]:** In-flight guarantee: Alice's existing recommendation retains template v1; new recommendation created for Alice uses newly active template v2.
- **api-050…056 [AC-10.1 / AC-10.6]:** Admin risk policy version lifecycle: create DRAFT v2, update bands (MODERATE 12-19, AGGRESSIVE 20-28), publish v2. Questionnaire now serves active v2 policy.
- **api-057…062 [AC-10.6]:** Alice attempts submission against stale policy v1 → 409 POLICY_VERSION_STALE. Alice's historical assessments remain pinned to policy v1. Bob submits ANS_20 against policy v2 → AGGRESSIVE (rescored from MODERATE under v1). New recommendation for Bob uses AGGRESSIVE on template v2.

---

## Architecture Checks

- **Layering:** `backend/.importlinter` verified (api → services → repositories → domain). No forbidden cross-boundary imports.
- **Domain Purity:** Zero framework or I/O imports in `app/domain/`.
- **Decimal Invariant (NFR-01):** `DecimalText` handles all monetary, percentage, and drift values. Zero float usage in domain or database models.
- **Append-Only Invariant (NFR-02):** `protect_append_only` event listeners prevent UPDATE and DELETE on `risk_assessments`, `recommendations`, `recommendation_allocations`, and `audit_events`.
- **Published Immutability (AC-10.3 / NFR-08):** `protect_published_version` event listeners prevent UPDATE and DELETE on published `template_versions` and `risk_policy_versions`.
- **PII Protection (NFR-03):** Loggers use allow-listed structured fields; correlation IDs tracked across all requests.

---

## Features Updated in `features.json`

All 71 features (F001 through F071) verified PASS.
