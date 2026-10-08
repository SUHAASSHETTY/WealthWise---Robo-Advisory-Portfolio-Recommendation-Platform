---
name: rubric-audit
description: Audit the WealthWise repository against the BC-AINE-008 AI-Native Engineering rubric (brief §7–§8) — counts and checks each evidence item with real commands and writes specs/reviews/rubric-audit-<date>.md.
---

# /rubric-audit

Check every rubric evidence item from the brief (§7.1–7.5, §8.1–8.2) with a **real command**. Never mark an item present without the command output to prove it.

## Steps

1. Run each check below from the project root, and record the command, the output (trimmed to the relevant lines) and PASS, PARTIAL or FAIL.

### 7.1 Claude Code specs (40)

| Item | Check | Threshold |
|---|---|---|
| Root and feature specs with ACs | `ls specs/*_spec.md specs/app_spec.md`; `grep -l "Acceptance criteria" specs/*_spec.md` | app_spec + ≥ 6 feature specs |
| Layered CLAUDE.md | `find . -name CLAUDE.md -not -path "./claude_harness_eng_v1/*" -not -path "*/node_modules/*"` | root + per-module + per-folder |
| AGENTS.md is a TOC | `wc -l AGENTS.md`; confirm it contains only links and headings | TOC only |
| Project skills | `ls .claude/skills` minus the 18 Harness skills | ≥ 3 |
| Project commands | `ls .claude/commands` minus `scaffold.md` | ≥ 2 |
| Project hooks | `ls .claude/hooks/*.js` minus the 15 Harness hooks; registered in `.claude/settings.json` | ≥ 2 |
| Project agents | `ls .claude/agents` minus the 7 Harness agents | ≥ 2 |
| Agent SDK script | `grep -l "claude_agent_sdk" scripts/*.py` | ≥ 1 |
| Own plugin.json | `cat plugin.json` (root) | present |
| Post-mortem or debugging log | `ls docs/postmortems docs/*debug* 2>/dev/null` | ≥ 1 |
| Playwright MCP | `cat .mcp.json`; `grep -n "mcp__playwright__" .claude/agents/evaluator.md` | configured and referenced |

### 7.2 Business understanding (20)

| Item | Check |
|---|---|
| `docs/business-case.md` sections | `grep -nE "^## " docs/business-case.md` (problem, users, metrics, rules, value) |
| ≥ 4 rule files in domain | `find backend/app/domain -name "*.py" -not -name "__init__.py" \| wc -l` |
| Responsive frontend | `grep -rn "@media\|sm:\|md:\|lg:" frontend/src \| head` |
| ACs in testable form, ≥ 4 specs | `grep -c "\*\*Given\*\*" specs/*_spec.md` |

### 7.3 Architectural discipline (8)

| Item | Check |
|---|---|
| ≥ 3 architecture tests | `ls tests/architecture/test_*.py` |
| import-linter configured | `grep -n "importlinter" backend/pyproject.toml`; `cd backend && poetry run lint-imports` |
| `docs/tdd.md` + ≥ 10 test files across history | `test -f docs/tdd.md`; `git log --diff-filter=A --name-only --format= -- tests frontend/e2e \| grep -c "test"` |

### 7.4 Technical implementation (26)

| Item | Check |
|---|---|
| `docs/architecture.md` with a diagram | `grep -c "mermaid" docs/architecture.md` |
| ≥ 3000 lines of generated code | `find backend/app frontend/src -name "*.py" -o -name "*.ts" -o -name "*.tsx" \| xargs wc -l \| tail -1` |
| Playwright snapshot directory | `ls frontend/e2e/__snapshots__` |
| Every AC has a test | `python3 scripts/ac_coverage.py` (exit 0) |
| ≥ 20 unit tests + coverage artefact | `cd backend && poetry run pytest --collect-only -q \| tail -1`; `ls coverage.xml`; `grep pytest-cov backend/pyproject.toml` |

### 7.5 CI/CD (6)

| Item | Check |
|---|---|
| CI pipeline | `ls .gitlab-ci.yml .github/workflows 2>/dev/null` |
| Claude Code Action wired | `grep -n "claude" .gitlab-ci.yml` |
| ≥ 3 `--no-ff` merges; no direct commits on main | `git log --merges --first-parent main --oneline \| wc -l`; `git log --first-parent --no-merges main --oneline` (should show only the foundation commit) |

### 8.1 Mandatory deliverables

Also check: single-command local run plus README quick-start; seed data; sprint contracts in `sprint-contracts/`; evaluator outputs in `specs/reviews/`.

2. Write `specs/reviews/rubric-audit-<YYYY-MM-DD>.md` with:
   - a summary table (category, items PASS/PARTIAL/FAIL, notes);
   - the evidence per item;
   - a **prioritised gap list**: highest marks at risk first, each with the concrete next action.

3. Show the user the summary table and the top 5 gaps. Don't fix anything in this command.
