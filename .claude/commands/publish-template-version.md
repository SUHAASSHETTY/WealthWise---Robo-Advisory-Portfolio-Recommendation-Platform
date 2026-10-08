---
name: publish-template-version
description: Safely publish a new WealthWise allocation-template (or risk-policy) version — draft, validate (exact-100 sums, horizon rules, threshold), verify immutability of older versions, publish as a NEW version, never edit an existing one.
argument-hint: "<template|risk-policy> <path-to-draft-definition.json>"
---

# /publish-template-version

Publishing changes advice for **new** recommendations or assessments only. In-flight customers keep the version they were advised under (admin_versioning_spec §2.4, AC-10).

## Rules (non-negotiable)

- **Never edit a PUBLISHED version** (file, DB row or migration). A change is always a **new** `version_no`. The `template-immutability-check` hook blocks edits to published definitions and locked migrations.
- Percentages are decimal **strings** (`"7.50"`). Every band sums to exactly `100.00`; the `allocation-sum-invariant-check` hook blocks seed and template writes that don't.

## Steps

1. **Read** `specs/admin_versioning_spec.md` §2 and `.claude/skills/allocation-template-resolver/SKILL.md` (or `risk-band-scorer` for risk policies).

2. **Load the draft** from `$ARGUMENTS`. Show the user a table: band × asset class, row sums, horizon rules and `drift_threshold_pct`.

3. **Validate.** Spawn the `policy-version-validator-agent` on the draft. It must write `specs/reviews/policy-validation-<date>.md` with `VERDICT: PASS`. If the verdict is FAIL, show the violations and stop. Don't "fix" values without the user's explicit instruction.

4. **Choose the publish path:**

   | App state | How |
   |---|---|
   | App running (Phase ≥ admin feature) | `POST /api/v1/admin/<template-versions\|risk-policies>/drafts`, then `PUT …/{id}` with the definition, then `POST …/{id}/publish`, using an ADMIN token (`erin.admin`). Expect `200 {version_no, status:"PUBLISHED"}`. |
   | Seeded versions (before the admin API exists) | Add a **new** Alembic data migration that inserts the version row with `status = PUBLISHED`. Never modify the v1 migration. |

5. **Verify immutability.**
   - `PUT` on the previous version must return `409 POLICY_VERSION_IMMUTABLE`.
   - `tests/architecture/test_published_templates_immutable.py` and `test_allocation_sum_invariant.py` must pass. Paste their output.

6. **Report** the new `version_no`, the validator verdict and the test output. Then add an entry to the current phase review.
