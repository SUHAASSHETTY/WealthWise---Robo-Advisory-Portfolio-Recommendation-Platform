# Claude Harness Engine v1 — Overview for WealthWise

This is our working reference for the Harness installed in `.claude/`. It is written from a full read of every file under `.claude/` and `docs/harness/`, and it records how WealthWise will use the Harness, including where its built-in assumptions don't match our project.

> **Rule:** the Harness files in `.claude/` are kept byte-identical to the company original. We never edit them. Every adaptation below is made with **new, project-owned files** (our own agents, skills, hooks, `project-manifest.json`, CLAUDE.md files, docs) in later PRs.

Source documents: [`HARNESS_CLAUDE.md`](HARNESS_CLAUDE.md), [`HARNESS_README.md`](HARNESS_README.md), [`design.md`](design.md).

---

## 1. Mental model

The Harness is a **generator–evaluator loop with a ratchet**:

- **Generator** writes code and tests, and never judges its own work.
- **Evaluator** runs the app and checks a pre-agreed **sprint contract**. It never reads source code to decide whether something passes.
- **Ratchet:** quality metrics (tests, lint, coverage, architecture, evaluator verdict, design score) can only move forward. Coverage has a hard floor of 80%, and `.claude/state/coverage-baseline.txt` only goes up.
- **Self-healing:** on a FAIL, the failure is classified and a targeted fix is attempted up to 3 times. After the third failure the change is reverted, a learned rule is written, and the group is marked BLOCKED.
- **Session chaining:** `claude-progress.txt`, `features.json` and `.claude/state/learned-rules.md` let work resume in a fresh context window.

`.claude/program.md` is the human steering file. `/auto` re-reads it on every iteration, so editing it mid-run changes constraints.

---

## 2. Base agents (`.claude/agents/`)

| Agent | Purpose | When it runs | Tools |
|---|---|---|---|
| **planner** | Turns requirements into a BRD, stories, a dependency graph, the architecture, schemas, `features.json` and the component map | `/brd`, `/spec`, `/deploy` (runs as this agent); spawned by `/design`; spawned by `/auto` when an architecture amendment appears | Read, Write, Glob, Grep, Bash |
| **generator** | Implements stories using TDD; spawns one teammate per story (max 5 in parallel) in phases from a micro-DAG; proposes the sprint contract | `/implement` (runs as this agent); spawned by `/auto` for contract proposal, implementation and each self-heal attempt; spawned by `/review` to fix BLOCK findings | Read, Write, Edit, Glob, Grep, Bash, **Agent** (spawns teammates; needs `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, which `settings.json` sets) |
| **evaluator** | Skeptical verifier: finalizes the sprint contract, then runs a health check, Layer 1 (API via curl), Layer 2 (Playwright MCP) and Layer 3 (delegated to design-critic). Writes the verdict and failure JSON and updates `features.json` | `/evaluate` (runs as this agent); spawned by `/auto` (contract approval, gates 4–5) and by `/review` | Read, Write, Glob, Grep, Bash, Playwright MCP: `browser_navigate`, `browser_click`, `browser_fill_form`, `browser_snapshot`, `browser_take_screenshot`, `browser_press_key`, `browser_wait_for`, `browser_tabs`, `browser_close` |
| **design-critic** | Scores UI screenshots on Design Quality, Originality, Craft and Functionality (weighted). Plateau detection forces a design pivot | Evaluator Layer 3, and the `/auto` GAN design loop (Full mode, frontend groups only) | Read, Write, Bash, Playwright MCP: `browser_navigate`, `browser_click`, `browser_snapshot`, `browser_take_screenshot`, `browser_resize`, `browser_hover`, `browser_press_key`, `browser_close` |
| **security-reviewer** | OWASP-style scan for injection, auth bypass/IDOR, secrets, secrets in logs, SSRF, path traversal and CVEs. Severities are BLOCK, WARN and INFO | `/review` (concurrently with the evaluator); also the reviewer the `require-review` Stop hook asks for | Read, Write, Grep, Glob, Bash |
| **test-engineer** | Test plan, AC-mapped test cases, Playwright E2E specs and fixtures. Must not modify source code | `/test` (runs as this agent) | Read, Write, Edit, Glob, Grep, Bash |
| **ui-designer** | Self-contained React and Tailwind HTML mockups (CDN, realistic data, 375 px and 1280 px), plus `aesthetic-direction.md` | Spawned by `/design` concurrently with the planner | Read, Write, Glob, Grep, Bash |

Model tiering in the docs: Opus for the orchestrator, evaluator and design-critic; Sonnet for generator teammates and the security-reviewer. It is configured via `project-manifest.json`.

---

## 3. Commands and skills

There is **one command file**, `.claude/commands/scaffold.md`. Every other entry point is a **skill** in `.claude/skills/<name>/SKILL.md` invoked as `/<name>`. Because the skills live inside this project's `.claude/`, the short form works (`/auto`, not `/claude-harness-engine:auto`). Skills with `context: fork` run in a forked context. `agent:` in the frontmatter means the skill runs as that agent.

### Pipeline skills

| Invoke | Runs as | What it triggers | Writes |
|---|---|---|---|
| `/scaffold` | main | Asks about stack, project type, verification mode and plugins; writes `project-manifest.json` and `calibration-profile.json`; copies `.claude/` from the plugin source; creates the output dirs; writes `CLAUDE.md`, `design.md`, `init.sh`, `features.json` and `claude-progress.txt`; runs `git init` | See text. **Not used as-is by us** (see §8.3). |
| `/brd` | planner | Socratic five-dimension interview, then a BRD. Human gate | `specs/brd/brd.md` |
| `/spec <brd>` | planner | Epics, stories (`E{n}-S{n}`), dependency groups A/B/C… and features. Human gate | `specs/stories/*.md`, `specs/stories/dependency-graph.md`, `specs/features.json` |
| `/design` | main → planner + ui-designer concurrently | Architecture, OpenAPI and JSON schemas, component map, deployment plan, mockups, then a UI-to-API field validation. Human gate | `specs/design/*`, `specs/design/mockups/*` |
| `/build [brd] [--mode]` | main | The full pipeline: `/brd` → `/spec` → `/design` (each needs approval) → initialise state → `/auto` → generate README | Everything above |
| **`/auto [--mode full\|lean\|solo\|turbo] [--group X]`** | main (orchestrator) | **The sprint loop with the ratchet and self-healing** (§4) | Code via the generator, `sprint-contracts/`, `specs/reviews/`, state files, commits |
| `/implement <group>` | generator | Implements one group with an agent team, then runs the validation gate (tests, lint, types) | Code and tests |
| **`/evaluate <group>`** | evaluator | **Runs the evaluator** against `sprint-contracts/<group>.json` | `specs/reviews/evaluator-report.md`, `features.json` |
| `/review [story]` | main → evaluator + security-reviewer concurrently | Quality gate. BLOCK findings go to the generator to fix, for up to 3 cycles | `specs/reviews/evaluator-report.md`, `specs/reviews/security-review.md` |
| `/test [--plan-only\|--e2e-only]` | test-engineer | Test plan, cases, fixtures and Playwright specs; then `npx playwright test` | `specs/test_artefacts/*`, `e2e/*.spec.ts`, `playwright.config.ts` |
| `/deploy [--up]` | planner | Docker Compose, Dockerfiles, `.env.example` and `init.sh` | Root and `backend/`/`frontend/` files |
| `/fix-issue #n` | main | GitHub issue → branch → failing test → fix → commit → `gh pr create` | **Uses GitHub** (see §7) |
| `/refactor <path>` | main | Behaviour-preserving cleanup against the quality principles, one principle at a time | Code |
| `/improve <desc\|story>` | main | Story-driven behaviour change; updates tests and the story status | Story file and code |
| `/lint-drift [path] [--auto-fix]` | main | Entropy scan for duplication, naming, layer leaks, dead code and test-quality drift | `specs/reviews/drift-report.md` |

### Reference skills (read by agents, not run directly)

`architecture` (layer rules, folder layout, data modelling), `code-gen` (quality principles, logging, errors, FastAPI patterns; `references/api-integration-patterns.md`), `testing` (test layers, boundaries, test data; `references/playwright.md`, `references/test-data.md`), and `evaluation` (evaluator rules; `references/contract-schema.json`, `playwright-patterns.md`, `scoring-rubric.md`, `scoring-examples.md`).

### How to start a sprint

1. **Prerequisites for `/auto`:** `specs/stories/` with acceptance criteria, `specs/stories/dependency-graph.md`, `specs/design/` (including `api-contracts.md` and `component-map.md`), `features.json`, `claude-progress.txt` and `.claude/program.md`. `/auto` refuses to start if any of these is missing. `/build` produces them; we can also produce them through `/spec` and `/design`.
2. **Create a feature branch first.** `/auto` commits directly (`git add -A && git commit -m "feat: implement group X"`), and our local pre-commit hook blocks commits on `main`.
3. **Run `/auto --group A --mode lean`.** Use `full` to include the design-critic loop. `/auto` then:
   - **contract step 2:** the generator proposes `sprint-contracts/A.json`;
   - **contract step 3:** the evaluator finalises it (immutable from then on);
   - the generator team implements it;
   - the ratchet gate runs, followed by PASS handling or self-healing.

### How to run the evaluator

- **Standalone:** `/evaluate A`. It reads `sprint-contracts/A.json` and `project-manifest.json`, health-checks the app, runs Layers 1 to 3 and the architecture file checks, then writes `specs/reviews/evaluator-report.md` with a line `VERDICT: PASS` or `VERDICT: FAIL`.
- **With the security review:** `/review` runs the evaluator and the security-reviewer concurrently.
- **Inside `/auto`:** gates 4–5, run automatically.

---

## 4. The ratchet and self-healing loop (`/auto`)

**Each iteration:**

1. Re-read `program.md`, `learned-rules.md`, the last block of `claude-progress.txt`, `features.json` and the dependency graph.
2. Pick the next unfinished group.
3. Negotiate the contract (generator proposes, evaluator finalises).
4. The generator team implements the group, following the micro-DAG phases.
5. Check `specs/design/amendments/`. If there are new amendments, the planner updates the design.
6. Run the **ratchet gate**:

| # | Gate | Full | Lean | Solo | Turbo |
|---|---|---|---|---|---|
| 1 | Unit tests (`pytest`, `npm test`) | ✓ | ✓ | ✓ | per commit |
| 2 | Lint + types (ruff, mypy, eslint, tsc) | ✓ | ✓ | ✓ | per commit |
| 3 | Coverage ≥ baseline and ≥ 80% | ✓ | ✓ | ✓ | per commit |
| 4 | Architecture (`files_must_exist`, schema) | ✓ | ✓ | – | at end |
| 5 | Evaluator (API + Playwright) | ✓ | ✓ | – | at end |
| 6 | Design critic (GAN vision loop) | ✓ | – | – | at end |

A **fast lane** skips gates 4–6 when a commit contains only docs or lint changes.

**On PASS:**
1. Commit.
2. Set `features.json` → `passes: true`.
3. Append a session block to `claude-progress.txt`.
4. Append to `iteration-log.md`.
5. Raise `coverage-baseline.txt`.
6. Move to the next group.

**On FAIL (self-heal, up to 3 attempts):**
- **Diagnose:** using `superpowers:systematic-debugging`.
- **Classify** into one of 10 categories: lint, type, test, import, coverage, API, Playwright, design, Docker or architecture drift. Each has a fixed strategy, and the rule is "fix the code, never the test".
- **Spawn the generator** with `specs/reviews/eval-failures-NNN.json`, the strategy, all learned rules, and the accumulated `prior_attempts` so the same fix isn't tried twice.
- **Re-run only** the failed gate.

**After the 3rd failure:**
- Revert, scoped to the group's files per the component map.
- Log to `.claude/state/failures.md`.
- Extract a learned rule into `.claude/state/learned-rules.md` once a category repeats two or more times. Rules are never deleted and are injected verbatim into every agent prompt.
- Mark the group BLOCKED and move on.

**Stopping conditions:**
- A hard stop on an unfixable architecture violation, or after 50 iterations.
- Per-group escalation after 3 failures.
- Coverage regression after a commit, which triggers `git revert HEAD`.
- Success: all features pass and coverage is at or above the baseline.

---

## 5. Hooks (`.claude/settings.json` → `.claude/hooks/*.js`)

All hooks are run as `node .claude/hooks/<name>.js`, so they don't need the executable bit. The docs say "12 hooks"; `settings.json` actually wires **15**.

Exit code 2 means "block" in Claude Code. **Timing matters:** a `PreToolUse` hook can prevent an action, but a `PostToolUse` hook runs *after* the tool has already executed. Its "BLOCKED" output is feedback telling the agent to fix the result; it doesn't undo it.

| Hook | Event / matcher | What it checks | Effect |
|---|---|---|---|
| `enforce-length-pre` | **PreToolUse** Write\|Edit | Simulates the edit; the resulting code file would be over 300 lines (skips `migrations`, `node_modules`, `dist`, `build`, `.next`, `.d.ts`) | **Prevents the write** |
| `scope-directory` | PostToolUse Edit\|Write | File path is outside the project root (`/tmp` is allowed) | Block feedback |
| `protect-env` | PostToolUse Edit\|Write | Writes to `.env`, `.env.*` (`.env.example` is allowed) | Block feedback |
| `detect-secrets` | PostToolUse Edit\|Write | AWS, GitHub, Anthropic, OpenAI and Slack keys, private-key blocks, `user:pass@` connection strings, **SSN pattern**. Skips `.md`, `.env.example`, and `hooks/`, `evals/`, `templates/` paths | Block feedback |
| `lint-on-save` | PostToolUse Edit\|Write | `.py`: `uv run ruff check --fix` and `ruff format`. `.ts/.tsx`: `npx eslint --fix` (cwd = `backend/` or `frontend/`) | Auto-fix; prints errors; never blocks |
| `typecheck` | PostToolUse Edit\|Write | `.py`: `uv run mypy <file>`. `.ts/.tsx`: `npx tsc --noEmit` | Warns only |
| `check-architecture` | PostToolUse Edit\|Write | In `.py` files under `/src/<layer>/`, an import `src.<higher layer>` where layers are `types < config < repository < service < api` | Block feedback |
| `check-function-length` | PostToolUse Edit\|Write | Python and JS/TS functions over 50 lines warn; over 80 lines block | Block feedback |
| `check-file-length` | PostToolUse Edit\|Write | Code files over 200 lines warn; 300 or more block | Block feedback |
| `track-writes` | PostToolUse Edit\|Write | Records non-test production code writes to `.claude/state/pending-reviews.jsonl` | Info |
| `pre-commit-gate` | PostToolUse Bash (contains `git commit`) | Full architecture scan of `<root>/src/**/*.py` | Block feedback **after the commit has run** |
| `sprint-contract-gate` | PostToolUse Bash (contains `git commit`) | If `claude-progress.txt` has a `current_group` and `sprint-contracts/<group>.json` exists, then `specs/reviews/evaluator-report.md` must contain `VERDICT: PASS` | Block feedback **after the commit has run** |
| `require-review` | **Stop** | Production code was written this turn, and no reviewer agent (`clean-code-reviewer`, `security-reviewer`, `pr-review-toolkit:code-reviewer`, `code-review:code-review`, `performance-optimizer`) ran afterwards | **Prevents the turn from ending**; asks for the reviewers |
| `task-completed` | TaskCompleted | Architecture scan of `src/`; reminds to run `/review` | Info only |
| `teammate-idle-check` | TeammateIdle | Each touched `src/...` file has a matching test at `tests/<dir>/test_<name>.py` or `tests/<dir>/<Name>.test.tsx` | **Keeps the teammate working** until tests exist |

---

## 6. Where contracts, reports and state live

| Artifact | Path | Written by | Committed? |
|---|---|---|---|
| Sprint contract | `sprint-contracts/<group>.json` (schema: `.claude/skills/evaluation/references/contract-schema.json`; example: `.claude/templates/sprint-contract.json`) | Generator proposes, evaluator finalises | Yes. The brief requires it. |
| Evaluator report | `specs/reviews/evaluator-report.md` (`VERDICT:` line) | Evaluator | Yes. The brief requires `specs/reviews/`. |
| Structured failures | `specs/reviews/eval-failures-NNN.json` | Evaluator | Yes |
| Security review | `specs/reviews/security-review.md` | security-reviewer | Yes |
| Design scores | `specs/reviews/eval-scores.json` | design-critic | Yes |
| Drift report | `specs/reviews/drift-report.md` | `/lint-drift` | Yes |
| Feature status | `features.json` (root; `/spec` writes `specs/features.json`, see §8.4) | planner, evaluator | Yes |
| Session log | `claude-progress.txt` | `/build`, `/auto` | Yes |
| Iteration log, failures, learned rules, coverage baseline, pending reviews | `.claude/state/*` | `/auto`, hooks | **No.** `.gitignore` excludes `.claude/state/` (see §8.5). |

---

## 7. How the evaluator uses Playwright MCP

- **Layer 2 (functional):** for each `playwright_checks` entry in the contract, the evaluator drives a real browser through MCP tools:
  - `browser_navigate` → `browser_click` / `browser_fill_form` / `browser_press_key` → `browser_snapshot` (DOM assertions) and `browser_take_screenshot`.
  - It uses only semantic locators (`getByRole`, `getByLabel`, `getByText`) and never CSS, XPath or `waitForTimeout`.
  - It retries a timing failure once.
- **Layer 3 (visual):** the design-critic navigates, interacts, scrolls and uses `browser_resize` to 375 px and 1280 px to screenshot multiple states. It then scores against `calibration-profile.json`, or the defaults if that file is missing: weights 1.5/1.5/0.75/0.75, threshold 7, per-criterion minimum 5.
- **App URLs** come from `project-manifest.json`, using the `verification.mode` field:
  - `docker`: `docker compose`, with error context from `docker compose logs`;
  - `local`: start commands, with error context from the process logs;
  - `stub`: a mock server generated from the schema.
- **Tool naming caveat:** both agents allowlist tools named `mcp__plugin_playwright_playwright__*`, which is the naming used when Playwright comes from a **plugin**. The server we registered in `.mcp.json` (PR-001) is named `playwright`, so its tools appear as `mcp__playwright__*`. Unless the Playwright plugin is also installed, the stock evaluator and design-critic **won't be granted** the project MCP tools. See §8.1.

---

## 8. GitHub and remote assumptions, and other mismatches, with our adaptations

### 8.1 Mismatches that affect how WealthWise runs

| # | Harness assumption | Why it doesn't fit | Our adaptation (later PR, new files only) |
|---|---|---|---|
| 8.1a | Playwright tools are named `mcp__plugin_playwright_playwright__*` | Our `.mcp.json` exposes `mcp__playwright__*` | Add a project agent (e.g. `wealthwise-evaluator`) with the `mcp__playwright__*` tool names and the same instructions, **or** install the Playwright plugin. Decide in the agents PR. |
| 8.1b | Layer hooks look for `/src/{types,config,repository,service,api}/` and `src.*` imports | Our backend layout is `backend/app/{domain,services,repositories,api}`, so `check-architecture`, `pre-commit-gate` and `task-completed` will **silently pass everything** | Enforce layering with **import-linter** contracts and `tests/architecture/` (both required by the brief), plus a project hook such as `check-layering-wealthwise`. `architecture.md` says layers can be overridden via `project-manifest.json`, but **the hook code doesn't read it**. |
| 8.1c | `lint-on-save`, `typecheck`, the gates and the README use `uv run …` and `--cov=src` | We use **Poetry** and package `app` | Document the Poetry equivalents in the root `CLAUDE.md` and `program.md` steering; set `linter`/`typechecker` in `project-manifest.json`. A project hook can run `poetry run ruff`/`mypy`. |
| 8.1d | The testing skill says to use a real database in Docker, "not SQLite substitutes unless explicitly approved" | The stack is SQLite | Record explicit approval of SQLite in `CLAUDE.md` and `program.md`. |
| 8.1e | `pre-commit-gate` and `sprint-contract-gate` run as **PostToolUse** | They report after `git commit` has already run | Treat them as alarms only. The real gates are our `.git/hooks/pre-commit` (main block), CI, and the merge checklist in each PR doc. |
| 8.1f | Default `verification.mode` is `docker` | The brief wants a single local command; Docker isn't required | Use `"mode": "local"` in `project-manifest.json` (uvicorn + Vite start commands, `/health` endpoint). |
| 8.1g | `require-review` asks for `clean-code-reviewer`; `/implement`, `/refactor` and `/improve` spawn `code-reviewer` | Neither agent exists in the Harness | Add a project reviewer agent under one of those names, or satisfy the Stop hook with `security-reviewer`. |

### 8.2 GitHub and remote-dependent parts

| Where | Assumption | Local-first adaptation |
|---|---|---|
| `/fix-issue` | `gh issue view`, `gh issue comment`, `gh pr create`, `closes #n` | Use the same discipline without `gh`: keep the issue as `docs/issues/ISSUE-NNN.md`, branch `fix/<desc>`, red test → fix → commit, then a PR doc `docs/prs/PR-NNN-*.md` and `git merge --no-ff` after approval. Never run the `gh` steps. |
| `/lint-drift` | "create GitHub issues" for REFACTOR items | Write them to `specs/reviews/drift-report.md` and/or `docs/issues/`. |
| `settings.json` permissions | Pre-allows `git push:*`, `gh issue:*`, `gh pr:*` | Policy: never push, open PRs or run `gh` unless the user explicitly asks in that turn. We can't remove these allows without editing a Harness file; a project `.claude/settings.local.json` deny list is an option if the user wants it enforced. |
| `commit-commands` plugin | Provides `/commit-push-pr` | Don't use it. Use `/commit` only, on feature branches. |
| `code-review`, `pr-review-toolkit` plugins | Built around hosted PRs | Run their review agents on the local branch diff; record the findings in the PR doc. |
| `enabledPlugins` (8 from `claude-plugins-official`) and `superpowers:*` references in skills | Installed from an online marketplace | If not installed, those steps are skipped (the Harness says it "works without" Superpowers). Installing them is a user decision. |
| `HARNESS_README` and `plugin.json` homepage | `git clone https://github.com/...` | Not needed. The Harness is already vendored into `.claude/`. |
| `/scaffold` step 3 | Searches `~` for the plugin source and re-copies `.claude/` | **Don't run `/scaffold`** (see §8.3). |
| `/auto`, `/build` | Commit on the current branch | Always run them on a feature branch; finish with a PR doc and a `--no-ff` merge. |
| Brief §7.5 / §8.1 | GitLab CI with the Claude Code Action and a passing build on `main` | Add `.gitlab-ci.yml` in a later PR. It runs only once pushed to the Virtusa GitLab at submission. |

### 8.3 Scaffolding without `/scaffold`

`/scaffold` would re-copy `.claude/` (overwriting the files we keep identical) and run `git init` again. Instead, we'll perform only its project-specific steps by hand in a later PR:
- `project-manifest.json` (Python 3.12/FastAPI/Poetry/ruff/mypy/pytest; React/Vite/npm/eslint/tsc/vitest; SQLite; `verification.mode: local`);
- `calibration-profile.json` (consumer-facing or internal-tool preset);
- the output directories `specs/{brd,stories,design/mockups,design/amendments,reviews,test_artefacts}`, `sprint-contracts/` and `e2e/`;
- `init.sh` (or the single-command start the brief requires);
- `features.json` and `claude-progress.txt`.

### 8.4 Internal inconsistencies to keep in mind

- **`features.json` location:** root for the planner, evaluator and `/auto`, but `specs/features.json` for `/spec`. We'll **use the root `features.json`**.
- **Story file names:** `specs/stories/story-NNN.md` for the planner, generator and evaluator, but `E{n}-S{n}.md` for `/spec`, `/improve` and `/design`. We'll use `E{n}-S{n}.md`.
- **Learned rules path:** generator step 1 reads `docs/learned-rules.md`; everything else uses `.claude/state/learned-rules.md`.
- **TDD order:** `/implement` says "code first, tests after", which contradicts the mandatory TDD in `program.md` and `code-gen`. **TDD wins** (the brief scores red–green–refactor).
- **Function-length block limit:** `design.md` says over 100 lines; the hook enforces over 80.
- **design-critic PASS rule:** one place says all four scores must meet the threshold; elsewhere it says weighted average ≥ threshold *and* each score ≥ minimum. The weighted rule is the documented default.
- **Missing script:** `architecture.md` references `.claude/hooks/check-architecture.sh`, which doesn't exist (only the `.js` hook does).
- **Hook messages may not reach the agent:** the hooks write their messages to **stdout** and then exit 2. Claude Code shows **stderr** to the agent on exit 2, so the "BLOCKED: …" reason text may not reach it. Verify this when we add project hooks, and write our own hooks to stderr.

### 8.5 Evidence files hidden by `.gitignore`

`.gitignore` excludes `.claude/state/`, so `iteration-log.md`, `failures.md`, `learned-rules.md` and `coverage-baseline.txt` won't be committed. The brief scores this kind of evidence: fix-loop traces, knowledge deposits and the agent-led trail.

Our adaptation, in a later PR:
- mirror the relevant entries into `docs/fix-loops/`, `docs/knowledge-deposits.md` and post-mortems under `docs/`; or
- add narrow `!`-negation lines to our root `.gitignore`, which is a project file rather than a Harness file.

---

## 9. WealthWise workflow summary

1. **Specs first:** `specs/app_spec.md` plus the per-feature specs (with AC-01…AC-10 in Given–When–Then), then stories and design via `/spec` and `/design`, or hand-authored to the same output paths.
2. **For each sprint:** create a feature branch, run `/auto --group <X> --mode lean|full`, then:
   - commit the outputs `sprint-contracts/<X>.json` and `specs/reviews/*`;
   - write a PR doc in `docs/prs/`;
   - get user approval;
   - run `git checkout main && git merge --no-ff <branch>`.
3. **Planned sprint order (brief §8.2 #14):**
   1. risk profile + recommendation;
   2. holdings + drift;
   3. rebalancing + goal tracker.
4. **Project-specific additions** go in their own files: at least 2 agents, 3 skills, 2 commands, 2 hooks, an Agent SDK script in `scripts/`, our own `plugin.json`, and the layered CLAUDE.md files. The Harness originals stay untouched.
