# AGENTS.md: table of contents

An index only. The rules live in the linked files.

## Instructions (CLAUDE.md hierarchy)

- [CLAUDE.md](CLAUDE.md): root rules, stack, commands, workflow
- [backend/CLAUDE.md](backend/CLAUDE.md)
  - [backend/app/domain/CLAUDE.md](backend/app/domain/CLAUDE.md)
  - [backend/app/services/CLAUDE.md](backend/app/services/CLAUDE.md)
  - [backend/app/repositories/CLAUDE.md](backend/app/repositories/CLAUDE.md)
  - [backend/app/api/CLAUDE.md](backend/app/api/CLAUDE.md)
- [frontend/CLAUDE.md](frontend/CLAUDE.md)
- [tests/CLAUDE.md](tests/CLAUDE.md)
- [specs/CLAUDE.md](specs/CLAUDE.md)

## Specs

- [specs/app_spec.md](specs/app_spec.md): root spec, AC and NFR maps
- [specs/risk_profile_spec.md](specs/risk_profile_spec.md): AC-01
- [specs/recommendation_spec.md](specs/recommendation_spec.md): AC-02, AC-04
- [specs/holdings_spec.md](specs/holdings_spec.md): AC-05
- [specs/rebalancing_spec.md](specs/rebalancing_spec.md): AC-06, AC-07
- [specs/goal_tracker_spec.md](specs/goal_tracker_spec.md): AC-03, AC-08
- [specs/advisor_workbench_spec.md](specs/advisor_workbench_spec.md): AC-09
- [specs/admin_versioning_spec.md](specs/admin_versioning_spec.md): AC-10

## Agents (`.claude/agents/`)

- [planner](.claude/agents/planner.md)
- [generator](.claude/agents/generator.md)
- [evaluator](.claude/agents/evaluator.md)
- [design-critic](.claude/agents/design-critic.md)
- [security-reviewer](.claude/agents/security-reviewer.md)
- [test-engineer](.claude/agents/test-engineer.md)
- [ui-designer](.claude/agents/ui-designer.md)

## Commands (`.claude/commands/`)

- [scaffold](.claude/commands/scaffold.md)

## Skills (`.claude/skills/`)

- **Pipeline:** [brd](.claude/skills/brd/SKILL.md) · [spec](.claude/skills/spec/SKILL.md) · [design](.claude/skills/design/SKILL.md) · [build](.claude/skills/build/SKILL.md) · [auto](.claude/skills/auto/SKILL.md) · [implement](.claude/skills/implement/SKILL.md) · [evaluate](.claude/skills/evaluate/SKILL.md) · [review](.claude/skills/review/SKILL.md) · [test](.claude/skills/test/SKILL.md) · [deploy](.claude/skills/deploy/SKILL.md)
- **Maintenance:** [fix-issue](.claude/skills/fix-issue/SKILL.md) · [refactor](.claude/skills/refactor/SKILL.md) · [improve](.claude/skills/improve/SKILL.md) · [lint-drift](.claude/skills/lint-drift/SKILL.md)
- **Reference:** [architecture](.claude/skills/architecture/SKILL.md) · [code-gen](.claude/skills/code-gen/SKILL.md) · [testing](.claude/skills/testing/SKILL.md) · [evaluation](.claude/skills/evaluation/SKILL.md)

## Hooks (`.claude/hooks/`, wired in [.claude/settings.json](.claude/settings.json))

- **PreToolUse:** [enforce-length-pre](.claude/hooks/enforce-length-pre.js)
- **PostToolUse (Edit/Write):** [scope-directory](.claude/hooks/scope-directory.js) · [protect-env](.claude/hooks/protect-env.js) · [detect-secrets](.claude/hooks/detect-secrets.js) · [lint-on-save](.claude/hooks/lint-on-save.js) · [typecheck](.claude/hooks/typecheck.js) · [check-architecture](.claude/hooks/check-architecture.js) · [check-function-length](.claude/hooks/check-function-length.js) · [check-file-length](.claude/hooks/check-file-length.js) · [track-writes](.claude/hooks/track-writes.js)
- **PostToolUse (Bash):** [pre-commit-gate](.claude/hooks/pre-commit-gate.js) · [sprint-contract-gate](.claude/hooks/sprint-contract-gate.js)
- **Stop:** [require-review](.claude/hooks/require-review.js)
- **TaskCompleted:** [task-completed](.claude/hooks/task-completed.js)
- **TeammateIdle:** [teammate-idle-check](.claude/hooks/teammate-idle-check.js)

## MCP and plugin

- [.mcp.json](.mcp.json): Playwright MCP
- [.claude/.claude-plugin/plugin.json](.claude/.claude-plugin/plugin.json): Harness plugin manifest

## Reference docs

- [docs/business-case.md](docs/business-case.md)
- [docs/harness/harness-overview.md](docs/harness/harness-overview.md)
- [.claude/program.md](.claude/program.md) · [.claude/architecture.md](.claude/architecture.md)
- [docs/phase-reviews/](docs/phase-reviews/): phase reviews
- [docs/prs/](docs/prs/): earlier PR descriptions (PR-001…PR-003)
