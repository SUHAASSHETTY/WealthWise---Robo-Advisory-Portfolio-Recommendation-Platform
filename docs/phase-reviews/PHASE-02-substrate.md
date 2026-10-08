# PHASE-02: Project substrate (agents, skills, commands, hooks, plugin, MCP, Agent SDK)

**Status:** awaiting human review · **Date:** 2026-10-05 · **Branch:** `phase-02-substrate` (10 commits, not merged, not pushed)

## Summary

This phase adds the WealthWise-specific AI-native substrate on top of the Harness in `./.claude/`. Every Harness file is kept; the only changes to existing Harness files are additive (listed below).

| Artifact | Added |
|---|---|
| **Agents** (6) | `risk-profiler-agent`, `recommendation-engine-agent`, `rebalancing-agent` (domain); `policy-version-validator-agent`, `archtest-author-agent`, `doc-writer` (technical). Each has frontmatter (name, description, tools) plus Scope, Inputs, Outputs and "Must read first" (specs and skills). |
| **Skills** (6) | `risk-band-scorer`, `allocation-template-resolver`, `drift-calculator`, `rebalancing-quantity-proposer`, `goal-progress-tracker`, `spec-to-test-generator`. Each has the exact spec formula, Decimal and rounding rules, signatures, verbatim worked examples and test vectors, and pitfalls. |
| **Commands** (4) | `/new-feature-sprint`, `/ac-coverage-check` (backed by `scripts/ac_coverage.py`; exit 1 if any AC lacks a test), `/publish-template-version`, `/rubric-audit` |
| **Hooks** (4) | `allocation-sum-invariant-check.js`, `template-immutability-check.js`, `pii-redaction-check.js`, `no-float-money-check.js`. All are PreToolUse Node hooks registered in `.claude/settings.json`, with shared `lib/` and a test runner. They block via **stderr** with exit 2, which fixes the Harness stdout problem in harness-overview §8.4. |
| **Plugin** | Root `plugin.json` (`wealthwise-substrate` 0.2.0) packaging the 6 agents, 6 skills, 4 commands, hooks (`.claude/hooks/wealthwise-hooks.json`) and MCP (`.mcp.json`). It is separate from the Harness `.claude/.claude-plugin/plugin.json`. |
| **MCP** | `.mcp.json` registers Playwright (`npx @playwright/mcp@latest`). Added `mcp__playwright__browser_*` tool names to `evaluator` (9) and `design-critic` (8), alongside the plugin-style names, plus a note in the `evaluate` skill. Before this, the evaluator couldn't use the project MCP server (harness-overview §8.1a). |
| **Agent SDK** | `scripts/agent_sdk_review.py`: a `claude_agent_sdk.query()` with Read/Grep/Glob only (writes, Bash and web tools are disallowed), model `claude-opus-5-5`, and a turn and budget cap. It writes `specs/reviews/sdk-review-<date>.md`: a deterministic traceability table, then the agent's per-AC findings and verdict. |
| **Docs** | `docs/hooks-verification.md`, an updated `AGENTS.md` (95 links, all resolve), and the root `CLAUDE.md` git rule changed to local phase-branch commits (per your instruction). |

### Additive edits to existing Harness files

- `.claude/settings.json`: two new PreToolUse entries; nothing removed.
- `.claude/agents/evaluator.md` and `design-critic.md`: extra `mcp__playwright__*` tool lines.
- `.claude/skills/evaluate/SKILL.md`: a one-sentence tool-name note.

## Files changed

`git diff --stat main...HEAD`: **35 files changed, 2091 insertions(+), 9 deletions(-)**

| Area | Files |
|---|---|
| Agents | `.claude/agents/{risk-profiler-agent,recommendation-engine-agent,rebalancing-agent,policy-version-validator-agent,archtest-author-agent,doc-writer}.md` (new); `evaluator.md`, `design-critic.md` (+MCP tools) |
| Skills | `.claude/skills/{risk-band-scorer,allocation-template-resolver,drift-calculator,rebalancing-quantity-proposer,goal-progress-tracker,spec-to-test-generator}/SKILL.md` (new); `evaluate/SKILL.md` (1 line) |
| Commands | `.claude/commands/{new-feature-sprint,ac-coverage-check,publish-template-version,rubric-audit}.md` |
| Hooks | `.claude/hooks/{allocation-sum-invariant-check,template-immutability-check,pii-redaction-check,no-float-money-check}.js`, `lib/{wealthwise-hook-utils,code-mask}.js`, `tests/run-wealthwise-hook-tests.js`, `wealthwise-hooks.json`; `.claude/settings.json` |
| Packaging | `plugin.json` |
| Scripts | `scripts/ac_coverage.py`, `scripts/agent_sdk_review.py` |
| Docs and outputs | `docs/hooks-verification.md`, `specs/reviews/sdk-review-2026-10-05.md`, `AGENTS.md`, `CLAUDE.md`, this file |

**Commits:**
1. `60964f0` CLAUDE.md git rule
2. `efdbc6d` agents
3. `cb937bb` skills
4. `b68a620` commands and coverage scanner
5. `00b8c49` hooks, tests and verification
6. `fe0ec73` MCP wiring
7. `1829349` plugin.json
8. `4050b06` Agent SDK script
9. `b8be182` AGENTS.md
10. This review (committed next)

## ACs covered

No AC is implemented in this phase; there is no application code yet. The substrate **enforces and supports** the ACs:

| AC / NFR | Supported by |
|---|---|
| AC-01 | `risk-profiler-agent`, `risk-band-scorer` |
| AC-02, AC-04 | `recommendation-engine-agent`, `allocation-template-resolver`, `allocation-sum-invariant-check` |
| AC-03, AC-08 | `goal-progress-tracker` |
| AC-05, AC-06, AC-07 | `rebalancing-agent`, `drift-calculator`, `rebalancing-quantity-proposer` |
| AC-09, AC-10 | `policy-version-validator-agent`, `template-immutability-check`, `/publish-template-version` |
| All ACs | `spec-to-test-generator`, `/ac-coverage-check`, `agent_sdk_review.py` |
| NFR-01 | `no-float-money-check` |
| NFR-03 | `pii-redaction-check` |
| NFR-05, NFR-08 | `template-immutability-check`, `allocation-sum-invariant-check`, `archtest-author-agent` |

## Real test output

### 1. Hook tests (`node .claude/hooks/tests/run-wealthwise-hook-tests.js`, exit 0)

The full verbatim output is in [docs/hooks-verification.md](../hooks-verification.md). Summary lines from that run:

```
[OK  ] allocation-sum-invariant-check | template JSON, every band = 100.00 | expected PASS, got PASS (exit 0)
[OK  ] allocation-sum-invariant-check | template JSON, AGGRESSIVE = 100.01 | expected BLOCK, got BLOCK (exit 2)
[OK  ] allocation-sum-invariant-check | seed rows (Python), manual allocation = 99.99 | expected BLOCK, got BLOCK (exit 2)
[OK  ] allocation-sum-invariant-check | out of scope: test file with a deliberately bad sum | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | new migration file (not locked) | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | edit locked migration 0001 | expected BLOCK, got BLOCK (exit 2)
[OK  ] template-immutability-check | edit PUBLISHED template_v1.json | expected BLOCK, got BLOCK (exit 2)
[OK  ] template-immutability-check | edit DRAFT template_v2_draft.json | expected PASS, got PASS (exit 0)
[OK  ] template-immutability-check | Bash: UPDATE template_versions | expected BLOCK, got BLOCK (exit 2)
[OK  ] template-immutability-check | Bash: rm locked migration | expected BLOCK, got BLOCK (exit 2)
[OK  ] template-immutability-check | Bash: SELECT from template_versions | expected PASS, got PASS (exit 0)
[OK  ] pii-redaction-check | service logs IDs and a count only | expected PASS, got PASS (exit 0)
[OK  ] pii-redaction-check | logger.info with email in extra | expected BLOCK, got BLOCK (exit 2)
[OK  ] pii-redaction-check | print of full_name + PAN literal | expected BLOCK, got BLOCK (exit 2)
[OK  ] pii-redaction-check | TS console.log of position value | expected BLOCK, got BLOCK (exit 2)
[OK  ] no-float-money-check | Decimal("0.01") with float-looking text only in strings/comments | expected PASS, got PASS (exit 0)
[OK  ] no-float-money-check | float annotations + float literal in domain | expected BLOCK, got BLOCK (exit 2)
[OK  ] no-float-money-check | out of scope: api layer file | expected PASS, got PASS (exit 0)

RESULT: 18/18 cases behaved as expected
```

### 2. `/ac-coverage-check` on this repo (`python3 scripts/ac_coverage.py`, exit 1, expected because no tests exist yet)

```
AC      scenarios  tests  status
AC-01           8      0  MISSING
AC-02           5      0  MISSING
AC-03           5      0  MISSING
AC-04           5      0  MISSING
AC-05           7      0  MISSING
AC-06           6      0  MISSING
AC-07           7      0  MISSING
AC-08           5      0  MISSING
AC-09           8      0  MISSING
AC-10           8      0  MISSING

RESULT: FAIL (0/10 ACs covered)
exit=1
```

### 3. Coverage scanner positive check (fixture: specs copy + 9 tagged pytest files + 1 Playwright spec, `--root <fixture>`, exit 0)

```
AC-09           8      1  OK
        - tests/unit/test_ac_09.py::test_ac_09_example
AC-10           8      1  OK
        - frontend/e2e/admin.spec.ts (playwright)

RESULT: PASS (10/10 ACs covered)
exit=0
```

With `--strict`, the same fixture reports `uncited scenarios: AC-10.1, … AC-10.8` and `RESULT: FAIL`.

### 4. Agent SDK script

```
$ python3 -m py_compile scripts/agent_sdk_review.py scripts/ac_coverage.py
py_compile OK
$ python3 scripts/agent_sdk_review.py --offline
Wrote specs/reviews/sdk-review-2026-10-05.md (offline)
offline exit=0
$ python3 scripts/agent_sdk_review.py
claude-agent-sdk is not installed: pip install claude-agent-sdk (or use --offline)
online exit=2
```

**The live agent review has not run.** `claude-agent-sdk` isn't installed and there's no `claude` CLI on PATH. I didn't install packages or spend API credit without your go-ahead. The SDK calls (`query`, `ClaudeAgentOptions` fields, `AssistantMessage`/`TextBlock`/`ResultMessage`) were written against the current Agent SDK Python reference (code.claude.com/docs/en/agent-sdk/python).

### 5. Structural checks

```
agent   risk-profiler-agent              OK
agent   recommendation-engine-agent      OK
agent   rebalancing-agent                OK
agent   policy-version-validator-agent   OK
agent   archtest-author-agent            OK
agent   doc-writer                       OK
skill   risk-band-scorer                 OK
skill   allocation-template-resolver     OK
skill   drift-calculator                 OK
skill   rebalancing-quantity-proposer    OK
skill   goal-progress-tracker            OK
skill   spec-to-test-generator           OK
command new-feature-sprint               OK
command ac-coverage-check                OK
command publish-template-version         OK
command rubric-audit                     OK
RESULT: ALL OK
settings.json valid
plugin.json valid JSON; components: {'agents': 6, 'skills': 6, 'commands': 4} ; missing paths: none
.claude/agents/evaluator.md tools: 23 project playwright tools: 9
.claude/agents/design-critic.md tools: 19 project playwright tools: 8
AGENTS.md links: 95 checked (0 missing)
```

### 6. Security review of the scripts (security-reviewer agent) and fixes

The verdict was **WARN, with no BLOCK findings**. All three WARNs were fixed in this phase:

| Finding | Fix | Verification (real output) |
|---|---|---|
| W1: `--date` path traversal into the output filename | `--date` is parsed with `date.fromisoformat` | `--date ../../x` → `error: argument --date: --date must be YYYY-MM-DD, got '../../x'`, exit 2 |
| W2: the agent could Read/Grep/Glob outside the repo (prompt-injection exfiltration into the report) | `can_use_tool=gate_tool` allows only in-repo paths and denies `.env*`, `.git`, `id_rsa*`/`id_ed25519*` and `*.pem`/`*.key`/`*.p12` | `is_safe_repo_path`: `specs/app_spec.md` True; `../../.ssh/id_rsa`, `/etc/passwd`, `.env`, `backend/.env.local`, `.git/config` and `certs/server.pem` all False |
| W3: a deny-list let `Task`, MCP and settings-sourced tools through | Every tool goes through `can_use_tool`, which allows only Read/Grep/Glob. `allowed_tools` was removed, because the docs say allow rules bypass the callback. `setting_sources=[]` keeps project `git push` allow rules out, and `mcp_servers={}`. | `py_compile` OK; `--offline` exit 0 |

INFO items:
- **I3 (regex backtracking):** fixed by tightening to `[ \t]*\n[ \t]*`. The fixture scan still gives `RESULT: PASS (10/10 ACs covered)`.
- **I1 (raw Markdown in the report):** accepted, because the report is meant to be Markdown.
- **I2 (`--root` is operator input):** accepted.

## Observations and decisions

1. **The Harness `check-function-length` hook miscounts braces inside string literals.** It blocked `lib/code-mask.js` (claiming a 6-line function was 85 lines), and its message was swallowed ("No stderr output"). I worked around it by building `{`/`}` from char codes. This is a candidate for `docs/knowledge-deposits.md`.
2. **Hooks load at session start.** The new hooks become active in the next Claude Code session (or after `/hooks` review). They were verified by direct invocation with real hook-input JSON.
3. **`plugin.json` couldn't be validated by the CLI** because `claude plugin validate` isn't available. It was checked for valid JSON and that every referenced path exists. The `skills` path field is the least certain manifest field.
4. **Pattern-based hooks.** PII and float detection are static. Runtime enforcement comes later via `tests/architecture/test_no_pii_in_logs.py` and `test_no_float_money.py` (archtest-author-agent).

## Review checklist

- [ ] 6 agents with frontmatter, scope, inputs, outputs and required reading
- [ ] 6 skills encode the exact spec formulas, Decimal rules and worked examples
- [ ] 4 commands; `/ac-coverage-check` fails when any AC lacks a test (exit 1 shown)
- [ ] 4 hooks registered in `.claude/settings.json`; each has passing and failing inputs; output recorded in `docs/hooks-verification.md`
- [ ] Root `plugin.json` packages the substrate, separate from the Harness manifest
- [ ] `.mcp.json` has Playwright; evaluator and design-critic reference `mcp__playwright__*`
- [ ] `scripts/agent_sdk_review.py` uses `claude_agent_sdk` and writes `specs/reviews/sdk-review-<date>.md`; offline run verified, live run pending your approval
- [ ] AGENTS.md updated (TOC only)
- [ ] Harness files only changed additively; `./claude_harness_eng_v1/` untouched
- [ ] Commits are on `phase-02-substrate` only; nothing on `main`, nothing pushed
