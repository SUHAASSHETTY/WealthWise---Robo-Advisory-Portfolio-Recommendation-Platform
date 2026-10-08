# PHASE-09: Final Evidence, Fix Loops, Post-Mortems & Rubric Audit

**Status:** READY FOR REVIEW · **Date:** 2026-10-06 · **Git:** no git writes; everything uncommitted (root `CLAUDE.md` rule 3)

## Summary

| Task | Result |
|---|---|
| 1. Fix Loop (`fix-loop-001.md`) | Executed full real fix loop: created invalid template v2 where MODERATE summed to 101.00%, captured real PreToolUse hook rejection (`allocation-sum-invariant-check.js`, exit code 2) and domain validation failure (`PolicyInvalid`), corrected allocation to 100.00%, and verified re-validation. Recorded full command trace and before/after diffs in `docs/fix-loops/fix-loop-001.md`. |
| 2. Post-Mortem (`docs/postmortems/`) | Documented real debugging post-mortem demonstrating environment-first resolution (`2026-10-06-rebalancing-kyc-and-auth-mismatch.md`) covering bearer token prefix alignment (`stub-token-dan`) and KYC verification gating for rebalancing trade placement. |
| 3. Knowledge Deposits (`docs/knowledge-deposits.md`) | Documented recurring failure modes and the permanent rules, hooks, skills, or architecture tests into which each lesson was encoded (Fixed-Point Decimal NFR-01, Allocation Sum Invariant AC-02/AC-10, Append-Only Protection NFR-02, PII Redaction NFR-03, Deterministic Clock, Layering & Import-Linter). |
| 4. AC Coverage Verification (`ac_coverage.py`) | Executed `scripts/ac_coverage.py`. Verified 100% test coverage across all 10 Acceptance Criteria (**10/10 ACs covered with 164 mapped tests**). |
| 5. Capstone Rubric Audit (`docs/rubric-audit.md`) | Audited complete codebase against Brief Section 7 rubric: 24 skills (≥3), 5 commands (≥2), 20 hooks (≥2), 13 agents (≥2), SDK review script, `plugin.json`, `.mcp.json`, 10 domain rule modules (≥4), 7 architecture test files (≥3), 25 test files (≥10), 406 passing backend pytest tests (≥20 unit), `coverage.xml` (95% coverage), 19,944 lines of code (≥3000), 7 Playwright UI snapshots, and 100% AC coverage. **0 Gaps Found.** |

---

## Files Created & Updated in Phase 09 (all uncommitted)

| Area | Files |
|---|---|
| Fix Loops | `docs/fix-loops/fix-loop-001.md` |
| Post-Mortems | `docs/postmortems/2026-10-06-rebalancing-kyc-and-auth-mismatch.md` |
| Knowledge Deposits | `docs/knowledge-deposits.md` |
| Rubric Audit | `docs/rubric-audit.md` |
| Phase Review Document | `docs/phase-reviews/PHASE-09-evidence.md` |

---

## Real Evidence Trace

### 1. Fix Loop Rejection Trace (PreToolUse Hook)

```
$ node -e "
const { spawnSync } = require('child_process');
const payload = JSON.stringify({
  tool_name: 'Write',
  tool_input: {
    file_path: 'backend/app/seed/policies/template_v2.json',
    content: JSON.stringify({
      templates: {
        CONSERVATIVE: { EQUITY: '20.00', DEBT: '60.00', GOLD: '10.00', CASH: '10.00' },
        MODERATE: { EQUITY: '51.00', DEBT: '35.00', GOLD: '10.00', CASH: '5.00' },
        AGGRESSIVE: { EQUITY: '75.00', DEBT: '15.00', GOLD: '7.50', CASH: '2.50' }
      }
    }, null, 2)
  }
});
const res = spawnSync('node', ['.claude/hooks/allocation-sum-invariant-check.js'], { input: payload, encoding: 'utf8' });
console.log('EXIT CODE:', res.status);
console.log('STDERR:\n', res.stderr);
"
EXIT CODE: 2
STDERR:
 BLOCKED by allocation-sum-invariant-check:
  - backend/app/seed/policies/template_v2.json line 9: allocation {EQUITY=51.00, DEBT=35.00, GOLD=10.00, CASH=5.00} sums to 101.00, expected exactly 100.00
Fix: Every allocation template/seed row must sum to exactly 100.00 with 2-dp decimal strings (recommendation_spec §2.4).
```

### 2. AC Coverage Trace (`scripts/ac_coverage.py`)

```
$ python3 scripts/ac_coverage.py

AC ID       Spec  Tests  Status
===============================
AC-01          7     15  OK
AC-02          7     35  OK
AC-03          6     10  OK
AC-04          6     29  OK
AC-05          7     19  OK
AC-06          6      3  OK
AC-07          7     10  OK
AC-08          5      6  OK
AC-09          8     11  OK
AC-10          8     26  OK

RESULT: PASS (10/10 ACs covered)
```

### 3. Full Project Test Suite Verification

```
Backend:  406 passed, 0 failures (95% code coverage, 100% domain coverage)
Frontend: 7 Vitest tests passed, 14 Playwright E2E tests passed (Chromium Desktop + Mobile Chrome)
Layering: 4/4 import-linter contracts kept, 0 broken
Hooks:    18/18 hook test fixtures passing
```

---

## Review Checklist

- [x] Fix loop completed and documented with real command outputs and diffs in `docs/fix-loops/fix-loop-001.md`.
- [x] Environment-first debugging post-mortem documented in `docs/postmortems/2026-10-06-rebalancing-kyc-and-auth-mismatch.md`.
- [x] Knowledge deposits cataloging recurring mistakes and encodings documented in `docs/knowledge-deposits.md`.
- [x] `ac-coverage-check` run and validated with 10/10 ACs passing.
- [x] Capstone Section 7 rubric audit completed with 0 gaps in `docs/rubric-audit.md`.
- [x] No git writes executed (all project files cleanly uncommitted per rule 3).
