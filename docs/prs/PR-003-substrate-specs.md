# PR-003: Substrate specs, business case, CLAUDE.md hierarchy, AGENTS.md

**Branch:** `feat/substrate-specs` → `main`
**Merge strategy:** `git merge --no-ff`

## Summary

Lays down the specification substrate that all generated code will follow:

- **Business case** (`docs/business-case.md`): problem, target users (customer, advisor, admin), value proposition, domain rules in business language, success metrics, scope and risks. Written from the brief, in our own words.
- **Specs** (`specs/`): a root `app_spec.md` plus 7 feature specs. Each feature spec has Purpose, Domain Rules, Data Model, API Contract, Given–When–Then Acceptance Criteria (AC-01…AC-10, scenarios `AC-NN.k`) and an NFR mapping. The root spec maps every AC and NFR-01…NFR-08 to its owning specs.
- **Concrete deterministic rules:**
  - a 7-question questionnaire with point values and score thresholds;
  - an emergency-fund cap;
  - v1 allocation templates summing to exactly 100.00;
  - a goal-horizon adjustment table;
  - a default drift threshold of 5.00 (strictly greater triggers);
  - a BUY/SELL quantity formula with explicit rounding.
  - The worked examples were checked with Python `Decimal`.
- **Layered CLAUDE.md:**
  - the root file (rules, stack, commands, workflow);
  - `backend/`, `backend/app/{domain,services,repositories,api}/`;
  - `frontend/`, `tests/`, `specs/`.
- **`AGENTS.md`:** a table of contents only, with links to the CLAUDE.md files, specs, agents, skills, the command, hooks, MCP and docs. All links were verified to resolve.

No application code is included, and no Harness files are modified.

## Files changed

| File | Change |
|---|---|
| `docs/business-case.md` | Added |
| `specs/app_spec.md`, `specs/CLAUDE.md` | Added |
| `specs/risk_profile_spec.md`, `specs/recommendation_spec.md`, `specs/admin_versioning_spec.md` | Added |
| `specs/holdings_spec.md`, `specs/rebalancing_spec.md` | Added |
| `specs/goal_tracker_spec.md`, `specs/advisor_workbench_spec.md` | Added |
| `CLAUDE.md`, `backend/CLAUDE.md`, `backend/app/{domain,services,repositories,api}/CLAUDE.md`, `frontend/CLAUDE.md`, `tests/CLAUDE.md` | Added |
| `AGENTS.md` | Added |
| `docs/prs/PR-003-substrate-specs.md` | Added (this file) |

## Key rules for review

### Risk scoring (risk_profile_spec §2)

- **Questions:** 7 (`AGE`, `HORIZON`, `INCOME_STABILITY`, `EMERGENCY_FUND`, `LOSS_REACTION`, `EXPERIENCE`, `OBJECTIVE`), each with 5 options worth 0–4 points; the maximum total is 28.
- **Bands:** 0–11 CONSERVATIVE · 12–20 MODERATE · 21–28 AGGRESSIVE.
- **Cap `NO_EMERGENCY_FUND`:** `EMERGENCY_FUND = NONE` limits the band to at most MODERATE.

### Templates v1 (recommendation_spec §2.1)

| Band | EQUITY | DEBT | GOLD | CASH |
|---|---|---|---|---|
| CONSERVATIVE | 20.00 | 60.00 | 10.00 | 10.00 |
| MODERATE | 50.00 | 35.00 | 10.00 | 5.00 |
| AGGRESSIVE | 75.00 | 15.00 | 7.50 | 2.50 |

### Horizon adjustment (months to goal)

| Months to goal | Adjustment |
|---|---|
| ≥ 84 | none |
| 60–83 | 10 pts EQUITY → DEBT |
| 36–59 | 20 pts EQUITY → DEBT |
| 12–35 | 30 pts EQUITY → DEBT |
| < 12 | all EQUITY → CASH |

The shift is capped at the available equity.

### Drift and rebalancing

- **Drift:** `abs(current% − target%)`, 2 dp half-even. A proposal is triggered when **any** class is **> 5.00**.
- **Quantities:**
  - per non-cash class, `round_down_4dp(|target_value − value| / NAV)`;
  - CASH is the settlement class, so it gets no order;
  - a negative-cash guard applies.

### Versioning

Published policy and template versions are immutable. Customers keep the versions recorded on their assessment or recommendation.

## Decisions taken (call out if you disagree)

1. **SQLite Decimal storage:** decimals are stored as TEXT (`DecimalText`), because SQLite `Numeric` is REAL. JSON decimals are strings.
2. **Test layout:**
   - backend tests at root `tests/`, run from `backend/` with `testpaths = ["../tests"]`;
   - Playwright in `frontend/e2e/` rather than the Harness default root `e2e/`, to avoid a third npm project.
3. **Goal value:** each goal is funded by a declared `funding_share_pct` of the portfolio. Σ ≤ 100.
4. **Accepting a rebalance needs KYC:** acceptance requires the stub `kyc_verified = true`. Carol is seeded unverified to demonstrate it.
5. **Drift threshold:** it lives in the template version, so it is versioned with the templates.

## Verification

- `git diff --stat main...feat/substrate-specs`: docs and specs only; nothing under `.claude/` changed.
- The worked examples (risk totals, horizon months, allocations, valuation, drift, BUY/SELL quantities, settlement cash, goal progress) were recomputed with Python `decimal` and match the specs.
- The AGENTS.md link check passed (0 missing).
- Each of AC-01…AC-10 appears in exactly one owning spec with Given–When–Then scenarios. Every NFR-01…NFR-08 appears in the app_spec NFR map and the relevant feature specs.

## Review checklist

- [ ] Business case covers problem, users, success metrics, domain rules and value proposition
- [ ] Every feature spec has Purpose, Domain Rules, Data Model, API Contract and Acceptance Criteria
- [ ] AC-01…AC-10 are in Given–When–Then form with concrete values
- [ ] NFR-01…NFR-08 are mapped to specs
- [ ] Questionnaire has ≥ 6 questions with points; thresholds are contiguous 0–28
- [ ] Every template row sums to exactly 100.00
- [ ] Horizon rule, 5.00% drift default and BUY/SELL formula with rounding are defined
- [ ] CLAUDE.md hierarchy is present at all requested paths
- [ ] AGENTS.md is a table of contents only
- [ ] No application code; no Harness files modified
