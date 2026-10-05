# WealthWise: root CLAUDE.md

A rule-based robo-advisory platform: risk profiling, deterministic allocation, goal tracking, drift and rebalancing.
Capstone BC-AINE-008. Brief: `docs/AI Native Engineer Capstone - BC-008 WealthWise.pdf`. Business context: `docs/business-case.md`. Specs: `specs/app_spec.md`.

## Rules (non-negotiable)

1. **No hand-coding.** Agents generate all production code, tests and migrations. The human reviews. Humans edit only specs, CLAUDE.md files, agents, skills, commands, hooks and docs.
2. **The spec is the truth.** If code and spec disagree, update the spec deliberately first (and record the change in the phase review), then regenerate the code. Never implement behaviour a spec doesn't describe.
3. **No git.** Never run any `git` command (including `status`, `log` and `diff`), and never run `gh`. Version control is handled by the human.
4. **Phase workflow.** Each phase ends with `docs/phase-reviews/PHASE-NN-<name>.md` containing Summary, Files changed, ACs covered, **real** test output (pasted from the actual run, never invented) and a Review checklist. Then **stop** for human approval. Don't start the next phase until the human approves.
5. **Synthetic data only.** No real or confidential customer data, anywhere.
6. **NFR-01: Decimal only.** Money, percentages, units, NAV and drift use `decimal.Decimal`, built from `str`/`int`, never `float`. Rounding rules are in `specs/app_spec.md` §5.1. Store as TEXT via `DecimalText`; serialise as JSON strings.
7. **NFR-03: no PII or positions in logs.** Log IDs, enums, counts and durations only. Never log names, emails, amounts, units, percentages or bands tied to a customer.
8. **Never modify `./claude_harness_eng_v1/`.** It is the read-only company original and is not used at runtime. The working substrate is `./.claude/`. Project-specific agents, skills, commands and hooks are added there alongside the Harness files.

Also always:
- **Append-only (NFR-02):** assessments, overrides, recommendations, rebalancing proposals and decisions, goal snapshots and audit events are insert-only.
- **Determinism:** domain functions are pure; use the injected `Clock`, never `date.today()` or `datetime.now()` in domain or services.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| Database | SQLite (approved substitute for the Harness's "real DB" default) |
| Backend tooling | Poetry, pytest + pytest-cov, ruff, mypy (strict), import-linter |
| Frontend | React + Vite + TypeScript, npm, Vitest, ESLint |
| E2E / UI validation | Playwright (`frontend/e2e/`), Playwright MCP for the evaluator (`.mcp.json`) |

## Layout

```
backend/                 Poetry project (pyproject.toml, alembic.ini)
  app/
    domain/              pure rules, no I/O              → backend/app/domain/CLAUDE.md
    services/            use cases, transactions, audit  → backend/app/services/CLAUDE.md
    repositories/        ORM models, data access         → backend/app/repositories/CLAUDE.md
    api/                 FastAPI routers, schemas, auth  → backend/app/api/CLAUDE.md
    core/                config, logging, db, security, clock
    seed/                synthetic seed data and NAV series
  migrations/            Alembic (append-only)
frontend/                React app and Playwright e2e   → frontend/CLAUDE.md
tests/                   backend pytest suites          → tests/CLAUDE.md
specs/                   source-of-truth specs          → specs/CLAUDE.md
docs/                    business case, phase reviews, Harness docs, post-mortems
.claude/                 Harness + project substrate
```

Layering is **api → services → repositories → domain**; `core` is importable by everything except `domain`. This is enforced by import-linter and `tests/architecture/`. The Harness `check-architecture` hook doesn't cover this layout (harness-overview §8.1b).

## Run commands

These are the target commands; the scaffold phase creates the config they depend on.

```bash
# backend (always from backend/)
cd backend && poetry install
cd backend && poetry run alembic upgrade head
cd backend && poetry run uvicorn app.main:app --reload --port 8000   # http://localhost:8000/health
cd backend && poetry run pytest                 # testpaths = ../tests; writes ../coverage.xml
cd backend && poetry run ruff check . && poetry run ruff format --check .
cd backend && poetry run mypy app
cd backend && poetry run lint-imports

# frontend (always from frontend/)
cd frontend && npm ci
cd frontend && npm run dev                      # http://localhost:5173
cd frontend && npm test                         # vitest
cd frontend && npm run lint && npm run typecheck
cd frontend && npx playwright test              # e2e; snapshots in frontend/e2e/__snapshots__/
```

The Harness hooks and gates call `uv run …`. In this repo the equivalent is `poetry run …` from `backend/`.

## Phase workflow

1. **Read first:** this file, the relevant layer CLAUDE.md, and the specs for the ACs in scope.
2. **Spec change first** if behaviour must differ from the spec. Edit `specs/*`, and list the change under "Spec changes" in the phase review.
3. **TDD:** write a failing test tagged with the AC (`@pytest.mark.ac("AC-NN")`, named `test_ac_NN_…`) and run it to capture the **red** output. Then implement, run again for **green**, and refactor. Paste the red and green excerpts into the phase review.
4. **Gates:** all tests pass, coverage ≥ 80% (target 100% on `domain/`), and ruff, mypy, lint-imports and Playwright (once the UI exists) pass.
5. **Phase review:** write `docs/phase-reviews/PHASE-NN-<name>.md` with Summary, Files changed, ACs covered, real test output and Review checklist. **Stop** and wait for approval.
6. **Record knowledge:** recurring mistakes go to `docs/knowledge-deposits.md`; fix loops go to `docs/fix-loops/`.

## How the Harness is used here

Full reference: `docs/harness/harness-overview.md`.

### Agents (`.claude/agents/`)

| Agent | Role here |
|---|---|
| `planner` | BRD, stories, design artefacts from our specs |
| `generator` | Writes code and tests (TDD), and proposes sprint contracts |
| `evaluator` | Verifies sprint contracts against the running app |
| `security-reviewer` | OWASP scan |
| `test-engineer` | Test plans and Playwright |
| `ui-designer` | Mockups |
| `design-critic` | UI scoring |

The generator never evaluates its own work.

### Skills (`/name`)

- **Pipeline:** `/spec` and `/design` produce stories and design under `specs/`.
- **Sprint:** `/auto --group X --mode lean|full` runs a sprint; `/implement X` builds one group.
- **Verification:** `/evaluate X` runs the evaluator; `/review` runs the evaluator and security-reviewer; `/test` builds test artefacts.
- **Maintenance:** `/refactor`, `/improve` and `/lint-drift`.
- **Don't use:** `/scaffold` (it would re-copy `.claude/` and run `git init`) and `/fix-issue` (it needs GitHub).

### State files

| File | Purpose |
|---|---|
| `.claude/program.md` | Human steering for `/auto`; re-read every iteration |
| `.claude/state/learned-rules.md` | Monotonic rules injected into every agent prompt |
| `.claude/state/failures.md` | Failure log; 2+ entries in one category produce a learned rule |
| `.claude/state/iteration-log.md` | Per-group sprint log |
| `.claude/state/coverage-baseline.txt` | Ratchet floor; only goes up, never below 80 |
| `.claude/state/eval-scores.json` | Design score history |
| `features.json`, `claude-progress.txt` | Feature pass/fail and session chaining (root) |
| `sprint-contracts/<group>.json` | Negotiated done-criteria; immutable once finalised |
| `specs/reviews/` | `evaluator-report.md` (`VERDICT:` line), `eval-failures-NNN.json`, `security-review.md` |

### No-git adaptations

- `/auto` normally commits on PASS, and runs `git checkout -- .` or `git revert` after a 3rd failure. **Skip every git step.**
  - On PASS, record the result in the phase review.
  - After the 3rd failure, stop, log to `failures.md`, extract a learned rule, and escalate to the human (no automatic revert).
- The `pre-commit-gate` and `sprint-contract-gate` hooks only fire on `git commit`, so they are inert here. Run the equivalent checks explicitly (lint-imports, architecture tests, evaluator verdict) and include their output in the phase review.

## Where to find things

| What | Where |
|---|---|
| ACs and NFRs → specs map | `specs/app_spec.md` §6–7 |
| Agents, skills, commands, hooks index | `AGENTS.md` |
| Harness behaviour and adaptations | `docs/harness/harness-overview.md` |
| Harness quality rules (function ≤ 50 lines, file ≤ 300 lines, typing) | `.claude/skills/code-gen/SKILL.md` |
| Phase reviews | `docs/phase-reviews/` |
