# WealthWise: root CLAUDE.md

A rule-based robo-advisory platform: risk profiling, deterministic allocation, goal tracking, drift and rebalancing.
Capstone BC-AINE-008. Business context: `docs/business-case.md`. Specs: `specs/app_spec.md`.

## Non-negotiable rules

1. **No hand-coding.** Agents generate all production code, tests and migrations. The human reviews. Humans edit only specs, CLAUDE.md files, agents, skills, commands, hooks and docs.
2. **The spec is the truth.** If code and spec disagree, change the spec deliberately (`spec:` commit), then regenerate the code. Never implement behaviour a spec doesn't describe.
3. **PRs only.** Never commit to `main`; a local pre-commit hook blocks it.
   - Every change goes: feature branch → commits → `docs/prs/PR-NNN-<name>.md` → human "approved" → `git checkout main && git merge --no-ff <branch>`.
   - Never run `git branch -M`, rebase `main`, or `--no-verify`.
   - Never push, open a hosted PR or run `gh` unless the human asks in that turn.
4. **Synthetic data only.** No real or confidential customer data, anywhere.
5. **NFR-01: Decimal only.** Money, percentages, units, NAV and drift use `decimal.Decimal`, built from `str`/`int`, never `float`. The rounding rules are in `specs/app_spec.md` §5.1. They are stored as TEXT via `DecimalText` and serialised as JSON strings.
6. **NFR-03: no PII or positions in logs.** Log IDs, enums, counts and durations only. Never log names, emails, amounts, units, percentages or bands tied to a customer.
7. **Append-only (NFR-02).** Assessments, overrides, recommendations, rebalancing proposals and decisions, goal snapshots and audit events are insert-only. Current state is derived.
8. **Determinism.** Domain functions are pure. Use the injected `Clock`; never call `date.today()` or `datetime.now()` in domain or services.
9. **Never modify Harness files** in `.claude/` (agents, hooks, skills, commands, settings, templates). Add project files alongside them. See `docs/harness/harness-overview.md`.

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
docs/                    business case, PRs, Harness docs, post-mortems
.claude/                 Harness (read-only) + project substrate
```

Layering is **api → services → repositories → domain**; `core` is importable by everything except `domain`. This is enforced by import-linter and `tests/architecture/`. The Harness `check-architecture` hook doesn't cover this layout (harness-overview §8.1b).

## Commands

These are the target commands; the scaffold PR creates the config they depend on.

```bash
# backend
cd backend && poetry install
cd backend && poetry run alembic upgrade head
cd backend && poetry run uvicorn app.main:app --reload --port 8000
cd backend && poetry run pytest                 # testpaths = ../tests; coverage → coverage.xml
cd backend && poetry run ruff check . && poetry run ruff format --check .
cd backend && poetry run mypy app
cd backend && poetry run lint-imports

# frontend
cd frontend && npm ci
cd frontend && npm run dev                      # http://localhost:5173
cd frontend && npm test                         # vitest
cd frontend && npm run lint && npm run typecheck
cd frontend && npx playwright test              # e2e; snapshots in frontend/e2e/__snapshots__/
```

The Harness hooks and gates call `uv run …`. In this repo the equivalent is `poetry run …` from `backend/`.

## Workflow

1. **Spec change first.** Edit `specs/*` on the feature branch with `spec:` commits.
2. **TDD.** Write a failing test tagged with the AC (`@pytest.mark.ac("AC-NN")`, named `test_ac_NN_…`), then the implementation, then refactor. Commit red and green separately where practical.
3. **Harness sprint.** Run `/auto --group <X> --mode lean|full` on the feature branch. Sprint contracts go to `sprint-contracts/`, and evaluator and security reports to `specs/reviews/`. Commit them.
4. **Gates before the PR doc.** All tests pass, coverage ≥ 80% (target 100% on `domain/`), ruff, mypy, lint-imports and the Playwright suite pass.
5. **PR doc.** Write `docs/prs/PR-NNN-<name>.md` with Title, Summary, Files changed, Verification and Review checklist. Then stop for human approval, and merge with `--no-ff`.
6. **Record knowledge.** Recurring mistakes go to `docs/knowledge-deposits.md`; fix loops go to `docs/fix-loops/`.

## Where to find things

| What | Where |
|---|---|
| ACs and NFRs → specs map | `specs/app_spec.md` §6–7 |
| Agents, skills, commands, hooks index | `AGENTS.md` |
| Harness behaviour and local adaptations | `docs/harness/harness-overview.md` |
| Harness quality rules (function ≤ 50 lines, file ≤ 300 lines, typing) | `.claude/skills/code-gen/SKILL.md` |
| Human steering for `/auto` | `.claude/program.md` |
