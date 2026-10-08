# Fix Loop 001: Allocation Template Invariant Violation (MODERATE sums to 101.00%)

**Date:** 2026-10-06  
**Trigger:** PreToolUse hook `allocation-sum-invariant-check` and Domain Validator `PolicyInvalid`  
**Rule / Invariant:** AC-02, AC-10, NFR-08 (Every allocation template and published version must sum to EXACTLY 100.00% across all asset classes).

---

## 1. Problem Description & Root Cause

During administrative template authoring for Template Policy v2, the allocation for the `MODERATE` risk band was drafted with an extra 1.00% assigned to `EQUITY` (`EQUITY: 51.00%`, `DEBT: 35.00%`, `GOLD: 10.00%`, `CASH: 5.00%`), causing the total allocation for `MODERATE` to sum to **101.00%** instead of **100.00%**.

---

## 2. Detection via PreToolUse Hook (Failure Reproduction)

When attempting to write or update the template file `backend/app/seed/policies/template_v2.json`, the project hook `.claude/hooks/allocation-sum-invariant-check.js` intercepted the write and rejected it with exit code `2`.

### Command:
```bash
node -e "
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
```

### Real Hook Failure Output:
```
EXIT CODE: 2
STDERR:
 BLOCKED by allocation-sum-invariant-check:
  - backend/app/seed/policies/template_v2.json line 9: allocation {EQUITY=51.00, DEBT=35.00, GOLD=10.00, CASH=5.00} sums to 101.00, expected exactly 100.00
Fix: Every allocation template/seed row must sum to exactly 100.00 with 2-dp decimal strings (recommendation_spec §2.4).
```

---

## 3. Detection via Domain Validation Layer

In the Python backend domain layer, `app.domain.template_version_validator.parse_template_version` and `app.domain.allocation.templates.parse_templates` similarly threw `PolicyInvalid` / `AllocationSumError`.

### Real Domain Validator Output:
```
PolicyInvalid: MODERATE sum=101.00, expected exactly 100.00
```

---

## 4. Remediation & Code Diff

The allocation for `MODERATE` was adjusted from `51.00` back to `50.00` to restore the exact 100.00% sum invariant:

```diff
       "CONSERVATIVE": { "EQUITY": "20.00", "DEBT": "60.00", "GOLD": "10.00", "CASH": "10.00" },
-      "MODERATE": { "EQUITY": "51.00", "DEBT": "35.00", "GOLD": "10.00", "CASH": "5.00" },
+      "MODERATE": { "EQUITY": "50.00", "DEBT": "35.00", "GOLD": "10.00", "CASH": "5.00" },
       "AGGRESSIVE": { "EQUITY": "75.00", "DEBT": "15.00", "GOLD": "7.50", "CASH": "2.50" }
```

---

## 5. Re-Validation & Verification

### A. PreToolUse Hook Check:
```bash
node -e "
const { spawnSync } = require('child_process');
const payload = JSON.stringify({
  tool_name: 'Write',
  tool_input: {
    file_path: 'backend/app/seed/policies/template_v2.json',
    content: JSON.stringify({
      templates: {
        CONSERVATIVE: { EQUITY: '20.00', DEBT: '60.00', GOLD: '10.00', CASH: '10.00' },
        MODERATE: { EQUITY: '50.00', DEBT: '35.00', GOLD: '10.00', CASH: '5.00' },
        AGGRESSIVE: { EQUITY: '75.00', DEBT: '15.00', GOLD: '7.50', CASH: '2.50' }
      }
    }, null, 2)
  }
});
const res = spawnSync('node', ['.claude/hooks/allocation-sum-invariant-check.js'], { input: payload, encoding: 'utf8' });
console.log('EXIT CODE:', res.status);
"
```
**Output:**
```
EXIT CODE: 0
```

### B. Architecture & Unit Test Suite:
```bash
poetry run pytest ../tests/architecture/test_allocation_sum_invariant.py ../tests/unit/domain/allocation/test_templates.py
```
**Output:**
```
14 passed in 0.12s
```

---

## 6. Lessons Learned & System Encodings
- The PreToolUse hook `.claude/hooks/allocation-sum-invariant-check.js` acts as an immediate guard preventing invalid allocations from ever touching the disk.
- Integer hundredths arithmetic in JavaScript (`toHundredths`) and `Decimal` arithmetic in Python ensure floating-point rounding errors never mask invalid allocations.
