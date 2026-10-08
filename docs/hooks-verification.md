# WealthWise project hooks: verification

**Audience:** reviewers and engineers adding hooks. **Run date:** 2026-10-05 (Phase 02).

## Hooks under test

| Hook | Event / matcher | Blocks |
|---|---|---|
| `allocation-sum-invariant-check.js` | PreToolUse `Write\|Edit\|MultiEdit` | Seed, migration, fixture, template or allocation files (not tests, not `.claude/`) containing an allocation (≥ 3 of EQUITY/DEBT/GOLD/CASH, or `asset_class`/`target_pct` rows) whose values aren't 2-dp decimals in [0, 100] summing to **exactly 100.00**. Uses integer hundredths, never float. |
| `template-immutability-check.js` | PreToolUse `Write\|Edit\|MultiEdit` and `Bash` | Edits to migrations listed in `backend/migrations/LOCKED_HASHES.txt`; edits to existing policy or template definition files whose status is `PUBLISHED`; Bash `UPDATE`/`DELETE FROM` on `template_versions` or `risk_policy_versions`; Bash `rm`/`mv`/`sed -i`/`>` on a locked migration |
| `pii-redaction-check.js` | PreToolUse `Write\|Edit\|MultiEdit` | Log or print calls in `backend/app/`, `frontend/src/` or `scripts/` (tests excluded) that reference PII (name, email, PAN, phone, DOB, credentials) or position data (value, units, amount, NAV, drift, allocation %, band), as identifiers, `extra` keys, f-string or template-literal expressions, or email/PAN/phone literals. `len(x)` counts are allowed. |
| `no-float-money-check.js` | PreToolUse `Write\|Edit\|MultiEdit` | In `backend/app/domain/**` and `backend/app/services/**` `.py`: the `float` type or `float()`, SQLAlchemy `Float`, float literals and exponent literals. Strings and comments are masked first, so `Decimal("0.01")` is fine. |

All four are registered in `.claude/settings.json` and share `.claude/hooks/lib/` (input parsing, edit simulation, string/comment masking).

**Design choice.** Block messages go to **stderr** with exit code 2, which Claude Code feeds back to the agent for PreToolUse hooks. The Harness hooks write to stdout, so their reason text is lost (see `docs/harness/harness-overview.md` §8.4); these hooks avoid that problem.

## How to run

```bash
node .claude/hooks/tests/run-wealthwise-hook-tests.js
```

The runner builds a throwaway fixture project in the OS temp dir. The fixture holds a locked migration `0001_seed_policy_v1.py`, a `PUBLISHED` `template_v1.json` and a `DRAFT` `template_v2_draft.json`. The runner pipes real hook-input JSON (`tool_name`, `tool_input`, `cwd`) into each hook, checks that the exit code is 0 (PASS) or 2 (BLOCK), and deletes the fixture afterwards.

Each hook has at least one passing and one failing input. Out-of-scope cases (test files, the API layer) are included to show that the hooks don't over-block.

## Real output

```
$ node .claude/hooks/tests/run-wealthwise-hook-tests.js
[OK  ] allocation-sum-invariant-check | template JSON, every band = 100.00 | expected PASS, got PASS (exit 0)
[OK  ] allocation-sum-invariant-check | template JSON, AGGRESSIVE = 100.01 | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by allocation-sum-invariant-check:
         - backend/app/seed/policies/template_v2.json line 15: allocation {EQUITY=75.00, DEBT=15.00, GOLD=7.51, CASH=2.50} sums to 100.01, expected exactly 100.00
       Fix: Every allocation template/seed row must sum to exactly 100.00 with 2-dp decimal strings (recommendation_spec §2.4).
[OK  ] allocation-sum-invariant-check | seed rows (Python), manual allocation = 99.99 | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by allocation-sum-invariant-check:
         - backend/app/seed/manual_allocations.py line 1: allocation {EQUITY=40.00, DEBT=40.00, GOLD=10.00, CASH=9.99} sums to 99.99, expected exactly 100.00
       Fix: Every allocation template/seed row must sum to exactly 100.00 with 2-dp decimal strings (recommendation_spec §2.4).
[OK  ] allocation-sum-invariant-check | out of scope: test file with a deliberately bad sum | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | new migration file (not locked) | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | edit locked migration 0001 | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by template-immutability-check:
         - backend/migrations/versions/0001_seed_policy_v1.py is a locked migration from an approved phase — migrations are append-only
       Fix: Create a NEW version (draft → publish) or a NEW Alembic revision instead; see /publish-template-version.
[OK  ] template-immutability-check | edit PUBLISHED template_v1.json | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by template-immutability-check:
         - backend/app/seed/policies/template_v1.json contains a PUBLISHED policy/template version — published versions are immutable
       Fix: Create a NEW version (draft → publish) or a NEW Alembic revision instead; see /publish-template-version.
[OK  ] template-immutability-check | edit DRAFT template_v2_draft.json | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | Bash: UPDATE template_versions | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by template-immutability-check:
         - command mutates template_versions / risk_policy_versions directly
       Fix: Create a NEW version (draft → publish) or a NEW Alembic revision instead; see /publish-template-version.
[OK  ] template-immutability-check | Bash: rm locked migration | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by template-immutability-check:
         - command modifies locked migration(s): 0001_seed_policy_v1.py
       Fix: Create a NEW version (draft → publish) or a NEW Alembic revision instead; see /publish-template-version.
[OK  ] template-immutability-check | Bash: SELECT from template_versions | expected PASS, got PASS (exit 0)
[OK  ] pii-redaction-check | service logs IDs and a count only | expected PASS, got PASS (exit 0)
[OK  ] pii-redaction-check | logger.info with email in extra | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by pii-redaction-check:
         - backend/app/services/auth_service.py line 1: log/print call references email
       Fix: Log only IDs, enums, counts and durations via extra={...} allow-listed keys (app_spec §5.6, NFR-03).
[OK  ] pii-redaction-check | print of full_name + PAN literal | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by pii-redaction-check:
         - scripts/seed_report.py line 1: log/print call references full_name, PAN literal
       Fix: Log only IDs, enums, counts and durations via extra={...} allow-listed keys (app_spec §5.6, NFR-03).
[OK  ] pii-redaction-check | TS console.log of position value | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by pii-redaction-check:
         - frontend/src/features/holdings/HoldingsTable.tsx line 1: log/print call references holding, current_value
       Fix: Log only IDs, enums, counts and durations via extra={...} allow-listed keys (app_spec §5.6, NFR-03).
[OK  ] no-float-money-check | Decimal("0.01") with float-looking text only in strings/comments | expected PASS, got PASS (exit 0)
[OK  ] no-float-money-check | float annotations + float literal in domain | expected BLOCK, got BLOCK (exit 2)
       BLOCKED by no-float-money-check:
         - backend/app/domain/portfolio/drift.py line 1: `float` type or float() conversion → def drift(current: float, target: float) -> float:
         - backend/app/domain/portfolio/drift.py line 1: `float` type or float() conversion → def drift(current: float, target: float) -> float:
         - backend/app/domain/portfolio/drift.py line 1: `float` type or float() conversion → def drift(current: float, target: float) -> float:
         - backend/app/domain/portfolio/drift.py line 2: float literal → return abs(current - target) * 1.0
       Fix: Use decimal.Decimal built from str/int and quantize per app_spec §5.1 (NFR-01). Never float.
[OK  ] no-float-money-check | out of scope: api layer file | expected PASS, got PASS (exit 0)

RESULT: 18/18 cases behaved as expected
```

The runner's process exit code was `0` (captured in a separate invocation: `tests exit=0`).

## Known limitations

- **Pattern-based checks.** They catch the common shapes (JSON or dict allocations, row lists, direct log calls). Indirect cases, such as logging a variable that *holds* an email under a neutral name, are covered by `tests/architecture/test_no_pii_in_logs.py` (runtime log capture), not by this hook.
- **Hook config is loaded at session start.** Edits to `.claude/settings.json` take effect in a new Claude Code session, or after review in `/hooks`.
- **The Harness `check-function-length` hook miscounts braces inside string literals.** That's why `lib/code-mask.js` builds `{`/`}` from char codes.
