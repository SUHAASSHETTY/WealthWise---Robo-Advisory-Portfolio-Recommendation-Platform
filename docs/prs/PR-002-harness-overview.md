# PR-002: Harness overview

**Branch:** `chore/harness-overview` → `main`
**Merge strategy:** `git merge --no-ff`

## Summary

Adds `docs/harness/harness-overview.md`, a working reference for the Claude Harness Engine v1 installed in `.claude/`. It's based on a full read of every file under `.claude/` and `docs/harness/`. It covers:

- the 7 base agents: purpose, when they run, and their tools;
- every command and skill, with exact invocations for starting a sprint (`/auto`), running the evaluator (`/evaluate`, `/review`), and the 6-gate ratchet with its 3-attempt self-healing loop;
- all 15 wired hooks: trigger event and what they block, including which ones run *after* the action;
- where sprint contracts, evaluator reports and state files are written, and which of them are committed;
- how the evaluator and design-critic use Playwright MCP;
- every GitHub or remote assumption and stack mismatch, with the local-first adaptation planned for each.

This PR documents only. No Harness files are modified and no application code is added.

## Files changed

| File | Change |
|---|---|
| `docs/harness/harness-overview.md` | **Added.** The Harness reference and adaptation plan. |
| `docs/prs/PR-002-harness-overview.md` | **Added.** This PR description. |

## Key findings for review

1. **Playwright tool names don't match.** The stock evaluator and design-critic allowlist `mcp__plugin_playwright_playwright__*`, but our `.mcp.json` exposes `mcp__playwright__*`. We'll need a project evaluator agent or the Playwright plugin.
2. **The layer hooks won't see our code.** They only inspect `src/{types,config,repository,service,api}`. With `backend/app/{domain,services,repositories,api}` they pass everything. Layering will be enforced with import-linter and architecture tests instead.
3. **The two commit gates fire after the commit.** `pre-commit-gate` and `sprint-contract-gate` are PostToolUse hooks, so they report after `git commit` has already run. Our real gates are the local `.git/hooks/pre-commit` main block, CI, and PR review.
4. **Tooling assumes uv and Docker.** The hooks and gates call `uv run`, but we use Poetry. The default verification mode is Docker, and we'll use `local`.
5. **Evidence files aren't committed.** `.claude/state/` is git-ignored, so iteration logs, failures and learned rules need mirroring into `docs/` or a narrow ignore exception.
6. **GitHub-only steps.** `/fix-issue` (`gh issue`, `gh pr create`) and the `settings.json` allow rules (`git push`, `gh`) need a local-first workflow: issue files, PR docs and `--no-ff` merges.
7. **Don't run `/scaffold`.** It would re-copy `.claude/` and run `git init` again. Its project-specific steps will be done by hand in a later PR.

## Verification

- `git diff --stat main -- .claude` and `git status --porcelain .claude` both print nothing; `.claude/` is unchanged since the foundation commit, which was verified identical to the original with `diff -r`.
- `git diff main...chore/harness-overview --stat` touches only the two files above.
- All file paths, tool names, thresholds and hook events cited in the overview were checked against the source files.

## Review checklist

- [ ] All 7 agents covered: purpose, trigger, tools
- [ ] Commands and skills listed with exact invocation; sprint start, evaluator and ratchet/self-healing explained
- [ ] All 15 hooks covered: event, matcher, block behaviour
- [ ] Sprint contract and evaluator report locations documented
- [ ] Playwright MCP usage documented, including the tool-name mismatch
- [ ] GitHub and remote assumptions listed, each with an adaptation
- [ ] No files under `.claude/` modified
- [ ] No application code included
