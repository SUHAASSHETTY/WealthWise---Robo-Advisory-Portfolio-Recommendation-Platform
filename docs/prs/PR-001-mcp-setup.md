# PR-001: Configure Playwright MCP

**Branch:** `chore/mcp-setup` → `main`
**Merge strategy:** `git merge --no-ff`

## Summary

Registers the Playwright MCP server at the project level so Claude Code agents (in particular the Harness `evaluator` and `design-critic`) can drive a real browser to verify UI acceptance criteria. This satisfies the brief's requirement that Playwright MCP is configured in `.mcp.json` (§7.1, §8.1 item 7).

No application code is included.

## Files changed

| File | Change |
|---|---|
| `.mcp.json` | **Added.** Registers server `playwright` → `npx @playwright/mcp@latest`. |
| `docs/prs/PR-001-mcp-setup.md` | **Added.** This PR description. |

## Verification

- `python3 -m json.tool .mcp.json` parses without error.
- `git diff main...chore/mcp-setup --stat` touches only the two files above; no Harness files under `.claude/` modified.
- Server registration can be confirmed in a new Claude Code session with `/mcp` (expects `playwright` listed).

## Known issue (follow-up, not fixed here)

The Harness agents (`.claude/agents/evaluator.md`, `design-critic.md`) allowlist tools named `mcp__plugin_playwright_playwright__browser_*` — the naming used when Playwright MCP is provided by a **plugin**. A server registered in `.mcp.json` as `playwright` exposes tools as `mcp__playwright__browser_*`. Until reconciled, the evaluator may not be able to call the project-level server. Options, to be decided in a later PR without editing Harness originals in place:

1. Add project-specific agent variants (e.g. `wealthwise-evaluator`) whose tool list uses `mcp__playwright__*`, or
2. Rely on the Playwright plugin being installed so the `mcp__plugin_playwright_playwright__*` names resolve.

This will be documented in PR-002 (Harness overview).

## Review checklist

- [ ] `.mcp.json` is valid JSON and registers only the `playwright` server
- [ ] No secrets, tokens, or environment-specific paths in `.mcp.json`
- [ ] No files under `.claude/` changed
- [ ] No application code included
- [ ] Commit messages follow `chore:` convention
- [ ] Known tool-name mismatch acknowledged and tracked for follow-up
