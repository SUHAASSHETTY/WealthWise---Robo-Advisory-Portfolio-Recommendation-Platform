# PHASE-01: Specs, business case, CLAUDE.md hierarchy, AGENTS.md

**Status:** APPROVED by human on 2026-10-05 · **Date:** 2026-10-05 · **Workflow:** no-git phase workflow (root `CLAUDE.md` rule 3–4)

## Summary

This phase establishes the specification substrate that every later phase generates code from:

- `docs/business-case.md` covers the problem, the target users (retail investor, advisor, admin), the value proposition, domain rules in business language, success metrics, scope and risks.
- `specs/app_spec.md` (root) and seven feature specs, each with Purpose, Domain Rules, Data Model, API Contract, Given–When–Then Acceptance Criteria (AC-01…AC-10 as scenarios `AC-NN.k`) and an NFR mapping. The root spec maps every AC and NFR-01…NFR-08.
- Concrete deterministic rules:
  - a 7-question risk questionnaire with points;
  - band thresholds and an emergency-fund cap;
  - v1 templates summing to exactly 100.00;
  - a goal-horizon adjustment table;
  - a 5.00% drift threshold;
  - a BUY/SELL quantity formula with explicit rounding.
- The layered CLAUDE.md hierarchy (9 files) and `AGENTS.md` as a table of contents only.

The specs, business case, layer CLAUDE.md files and AGENTS.md already existed from the earlier PR-based setup (PR-003). In this phase they were **reused rather than regenerated**, and updated for the new workflow rules:

- **Root `CLAUDE.md` rewritten:**
  - the "PRs only" rule is replaced by **No git** and the **Phase workflow**;
  - added the rule that `./claude_harness_eng_v1/` is never modified and `.claude/` is the working substrate;
  - added run commands;
  - added a "How the Harness is used here" section (agents, skills, state files, no-git adaptations for `/auto`).
- **Git and PR wording replaced** with phase-review equivalents in `specs/CLAUDE.md`, `specs/app_spec.md`, `backend/CLAUDE.md`, `backend/app/repositories/CLAUDE.md`, `backend/app/api/CLAUDE.md` and `tests/CLAUDE.md`. TDD evidence is now pasted red and green test output instead of commits.
- **`AGENTS.md`** links `docs/phase-reviews/`.

No application code, tests or migrations were written. No files in `./claude_harness_eng_v1/` or `.claude/` were modified. No git commands were run.

## Files changed

| File | Change in this phase |
|---|---|
| `CLAUDE.md` | Rewritten: new rules, run commands, phase workflow, Harness usage, no-git adaptations |
| `specs/CLAUDE.md` | Spec-change and approval wording (no git) |
| `specs/app_spec.md` | Spec-Is-Truth and migration wording (no git) |
| `backend/CLAUDE.md` | Migration and coverage-artefact wording |
| `backend/app/repositories/CLAUDE.md` | Migration wording |
| `backend/app/api/CLAUDE.md` | "Spec change first" wording |
| `tests/CLAUDE.md` | TDD evidence via red and green output; migration-lock wording |
| `AGENTS.md` | Added link to `docs/phase-reviews/` |
| `docs/phase-reviews/PHASE-01-specs.md` | **Added** (this file) |
| `docs/business-case.md`, `specs/*_spec.md` (7), `backend/app/{domain,services}/CLAUDE.md`, `frontend/CLAUDE.md` | Unchanged; already satisfy this phase's requirements (verified below) |

## ACs covered (specified, not yet implemented)

| AC | Owning spec | Scenarios |
|---|---|---|
| AC-01 | risk_profile_spec.md | 8 (AC-01.1–01.8) |
| AC-02 | recommendation_spec.md | 5 |
| AC-03 | goal_tracker_spec.md | 5 |
| AC-04 | recommendation_spec.md | 5 |
| AC-05 | holdings_spec.md | 7 |
| AC-06 | rebalancing_spec.md | 6 |
| AC-07 | rebalancing_spec.md | 7 |
| AC-08 | goal_tracker_spec.md | 5 |
| AC-09 | advisor_workbench_spec.md | 8 |
| AC-10 | admin_versioning_spec.md | 8 |

NFR-01…NFR-08 are mapped in `specs/app_spec.md` §7 and in each feature spec's §6.

## Rules for review

### Risk scoring (risk_profile_spec §2)

| Question | Options (points) |
|---|---|
| `AGE` | 18–29 (4) · 30–39 (3) · 40–49 (2) · 50–59 (1) · 60+ (0) |
| `HORIZON` | <3y (0) · 3–5y (1) · 5–7y (2) · 7–10y (3) · >10y (4) |
| `INCOME_STABILITY` | none (0) · irregular (1) · stable single (2) · stable growing (3) · multiple stable (4) |
| `EMERGENCY_FUND` | none (0) · <3m (1) · 3–6m (2) · 6–12m (3) · >12m (4) |
| `LOSS_REACTION` (−20% in a month) | sell all (0) · sell some (1) · hold (2) · buy some (3) · buy more (4) |
| `EXPERIENCE` | none (0) · deposits only (1) · funds <3y (2) · funds/stocks 3–7y (3) · active >7y (4) |
| `OBJECTIVE` | preserve (0) · income (1) · balanced (2) · growth (3) · aggressive growth (4) |

- **Bands (total 0–28):** **0–11 CONSERVATIVE · 12–20 MODERATE · 21–28 AGGRESSIVE.**
- **Cap `NO_EMERGENCY_FUND`:** if `EMERGENCY_FUND = NONE`, the band is at most MODERATE.

### Allocation templates v1 (recommendation_spec §2.1)

| Band | EQUITY | DEBT | GOLD | CASH | Sum |
|---|---|---|---|---|---|
| CONSERVATIVE | 20.00 | 60.00 | 10.00 | 10.00 | 100.00 |
| MODERATE | 50.00 | 35.00 | 10.00 | 5.00 | 100.00 |
| AGGRESSIVE | 75.00 | 15.00 | 7.50 | 2.50 | 100.00 |

### Goal-horizon adjustment, by months to the primary or selected goal

| Months to goal | Adjustment |
|---|---|
| ≥ 84 | none |
| 60–83 | 10 pts EQUITY → DEBT |
| 36–59 | 20 pts EQUITY → DEBT |
| 12–35 | 30 pts EQUITY → DEBT |
| < 12 | all EQUITY → CASH |

The amount moved is capped at the template's equity.

### Drift and rebalancing

- **Drift:** `abs(current% − target%)`, 2 dp half-even. A proposal is triggered when **any** class is **> 5.00** (strictly greater).
- **Quantity:** `round_down_4dp(|target_value − value| / NAV)` per non-cash class.
- **Cash** is the settlement class (no order), with a negative-cash guard.

### Decisions to confirm

1. Decimals are stored as TEXT on SQLite and serialised as JSON strings.
2. Goals are funded by a declared `funding_share_pct` of the portfolio, with Σ ≤ 100.
3. Accepting a rebalance needs the stub `kyc_verified` flag.
4. The drift threshold is versioned with the templates.
5. Backend tests live in root `tests/`; Playwright lives in `frontend/e2e/`.

## Real test output

There is no application code in this phase, so there is no pytest suite yet. The phase was verified with a spec-verification script (`verify_phase01.py`, kept outside the project in the session scratchpad). It checks:

- the section structure and Given–When–Then form of every spec;
- the AC and NFR maps;
- the questionnaire, threshold and template invariants;
- every worked example, recomputed with Python `decimal`;
- the presence of the CLAUDE.md files;
- that every AGENTS.md link resolves.

**Run 1** (`python3 verify_phase01.py .`, exit 1) produced 7 failures. All were `required sections — missing ['API contract']` (and one `'Data model'`), and all came from the checker's exact-match heading regex. The actual headings carry suffixes (e.g. `## 4. API contract (role: CUSTOMER)`). The checker was changed to a prefix match. **No spec was changed.**

**Run 2** (`python3 verify_phase01.py .`, exit 0), verbatim:

```
== 1. Spec structure and AC coverage ==
[PASS] risk_profile_spec.md: required sections
[PASS] risk_profile_spec.md: AC-01 has Given-When-Then scenarios — 8 scenarios
[PASS] recommendation_spec.md: required sections
[PASS] recommendation_spec.md: AC-02 has Given-When-Then scenarios — 5 scenarios
[PASS] recommendation_spec.md: AC-04 has Given-When-Then scenarios — 5 scenarios
[PASS] holdings_spec.md: required sections
[PASS] holdings_spec.md: AC-05 has Given-When-Then scenarios — 7 scenarios
[PASS] rebalancing_spec.md: required sections
[PASS] rebalancing_spec.md: AC-06 has Given-When-Then scenarios — 6 scenarios
[PASS] rebalancing_spec.md: AC-07 has Given-When-Then scenarios — 7 scenarios
[PASS] goal_tracker_spec.md: required sections
[PASS] goal_tracker_spec.md: AC-03 has Given-When-Then scenarios — 5 scenarios
[PASS] goal_tracker_spec.md: AC-08 has Given-When-Then scenarios — 5 scenarios
[PASS] advisor_workbench_spec.md: required sections
[PASS] advisor_workbench_spec.md: AC-09 has Given-When-Then scenarios — 8 scenarios
[PASS] admin_versioning_spec.md: required sections
[PASS] admin_versioning_spec.md: AC-10 has Given-When-Then scenarios — 8 scenarios

== 2. Root spec maps ==
[PASS] app_spec AC map has AC-01
[PASS] app_spec AC map has AC-02
[PASS] app_spec AC map has AC-03
[PASS] app_spec AC map has AC-04
[PASS] app_spec AC map has AC-05
[PASS] app_spec AC map has AC-06
[PASS] app_spec AC map has AC-07
[PASS] app_spec AC map has AC-08
[PASS] app_spec AC map has AC-09
[PASS] app_spec AC map has AC-10
[PASS] app_spec NFR map has NFR-01
[PASS] app_spec NFR map has NFR-02
[PASS] app_spec NFR map has NFR-03
[PASS] app_spec NFR map has NFR-04
[PASS] app_spec NFR map has NFR-05
[PASS] app_spec NFR map has NFR-06
[PASS] app_spec NFR map has NFR-07
[PASS] app_spec NFR map has NFR-08

== 3. Risk policy v1 ==
[PASS] question count >= 6 — 7 questions
[PASS] max score = 28 — 28
[PASS] band thresholds contiguous 0..max — [(0, 11, 'CONSERVATIVE'), (12, 20, 'MODERATE'), (21, 28, 'AGGRESSIVE')]

== 4. Template v1 (admin_versioning JSON) ==
[PASS] CONSERVATIVE sums to 100.00 — {'EQUITY': '20.00', 'DEBT': '60.00', 'GOLD': '10.00', 'CASH': '10.00'} = 100.00
[PASS] MODERATE sums to 100.00 — {'EQUITY': '50.00', 'DEBT': '35.00', 'GOLD': '10.00', 'CASH': '5.00'} = 100.00
[PASS] AGGRESSIVE sums to 100.00 — {'EQUITY': '75.00', 'DEBT': '15.00', 'GOLD': '7.50', 'CASH': '2.50'} = 100.00
[PASS] drift threshold default 5.00

== 5. Recommendation worked examples (recommendation_spec §2.3) ==
[PASS] MODERATE @ 120m -> H_84_PLUS 50.00 35.00 10.00 5.00 — 50.00 35.00 10.00 5.00
[PASS] MODERATE @ 48m -> H_36_59 30.00 55.00 10.00 5.00 — 30.00 55.00 10.00 5.00
[PASS] AGGRESSIVE @ 24m -> H_12_35 45.00 45.00 7.50 2.50 — 45.00 45.00 7.50 2.50
[PASS] CONSERVATIVE @ 24m -> H_12_35 0.00 80.00 10.00 10.00 — 0.00 80.00 10.00 10.00
[PASS] AGGRESSIVE @ 6m -> H_0_11 0.00 15.00 7.50 77.50 — 0.00 15.00 7.50 77.50
[PASS] AC-02.3 sum invariant over band x horizon grid

== 6. Holdings / rebalancing / goals worked examples ==
[PASS] rebalancing §2.3 lines — EQUITY SELL 66.6666 (9999.99); DEBT BUY 400.0000 (10000.00); GOLD BUY 16.6666 (1000.00)
[PASS] post_trade_cash = 4999.99 — 4999.99
[PASS] AC-05.3 current_pct 62.26
[PASS] AC-05.4 half-even 12.345 -> 12.34
[PASS] AC-08.1/08.2 goal progress — ['12.00', '80.00', '12.72', '84.80']

== 7. CLAUDE.md hierarchy and AGENTS.md links ==
[PASS] exists: CLAUDE.md
[PASS] exists: backend/CLAUDE.md
[PASS] exists: backend/app/domain/CLAUDE.md
[PASS] exists: backend/app/api/CLAUDE.md
[PASS] exists: backend/app/services/CLAUDE.md
[PASS] exists: backend/app/repositories/CLAUDE.md
[PASS] exists: frontend/CLAUDE.md
[PASS] exists: tests/CLAUDE.md
[PASS] exists: specs/CLAUDE.md
[PASS] exists: docs/business-case.md
[PASS] AGENTS.md links resolve (67 links)

RESULT: ALL CHECKS PASSED
```

## Observations (environment)

- The Harness `scope-directory` hook flagged a write to the session scratchpad. It allows paths starting with `/tmp`, but macOS resolves the scratchpad under `/private/tmp`.
- The hook's message didn't reach the agent ("No stderr output"), because Harness hooks print to stdout before exiting with code 2. This confirms `docs/harness/harness-overview.md` §8.4.
- Both are candidates for `docs/knowledge-deposits.md` and a project hook fix in a later phase.

## Review checklist

- [ ] Business case covers problem, three user types, success metrics, domain rules and value proposition, in our own words
- [ ] Root spec plus 7 feature specs each have Purpose, Domain Rules, Data Model, API Contract and Acceptance Criteria
- [ ] AC-01…AC-10 are in Given–When–Then form with concrete values; NFR-01…NFR-08 are mapped
- [ ] Risk scoring: ≥ 6 questions with points; thresholds contiguous 0–28; cap rule acceptable
- [ ] Templates v1 each sum to exactly 100.00; horizon rule, 5.00% drift and BUY/SELL formula with rounding are acceptable
- [ ] Root CLAUDE.md contains every rule from the phase prompt, the stack, run commands, phase workflow and Harness usage
- [ ] All 9 CLAUDE.md files present; AGENTS.md is a table of contents only
- [ ] No application code; no changes to `./claude_harness_eng_v1/` or `.claude/`; no git commands run
