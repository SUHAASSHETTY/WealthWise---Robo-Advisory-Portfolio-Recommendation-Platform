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

- **WealthWise:** [risk-profiler-agent](.claude/agents/risk-profiler-agent.md) · [recommendation-engine-agent](.claude/agents/recommendation-engine-agent.md) · [rebalancing-agent](.claude/agents/rebalancing-agent.md) · [policy-version-validator-agent](.claude/agents/policy-version-validator-agent.md) · [archtest-author-agent](.claude/agents/archtest-author-agent.md) · [doc-writer](.claude/agents/doc-writer.md)
- **Harness:**
- [planner](.claude/agents/planner.md)
- [generator](.claude/agents/generator.md)
- [evaluator](.claude/agents/evaluator.md)
- [design-critic](.claude/agents/design-critic.md)
- [security-reviewer](.claude/agents/security-reviewer.md)
- [test-engineer](.claude/agents/test-engineer.md)
- [ui-designer](.claude/agents/ui-designer.md)

## Commands (`.claude/commands/`)

- **WealthWise:** [new-feature-sprint](.claude/commands/new-feature-sprint.md) · [ac-coverage-check](.claude/commands/ac-coverage-check.md) · [publish-template-version](.claude/commands/publish-template-version.md) · [rubric-audit](.claude/commands/rubric-audit.md)
- **Harness:** [scaffold](.claude/commands/scaffold.md)

## Skills (`.claude/skills/`)

- **WealthWise:** [risk-band-scorer](.claude/skills/risk-band-scorer/SKILL.md) · [allocation-template-resolver](.claude/skills/allocation-template-resolver/SKILL.md) · [drift-calculator](.claude/skills/drift-calculator/SKILL.md) · [rebalancing-quantity-proposer](.claude/skills/rebalancing-quantity-proposer/SKILL.md) · [goal-progress-tracker](.claude/skills/goal-progress-tracker/SKILL.md) · [spec-to-test-generator](.claude/skills/spec-to-test-generator/SKILL.md)

- **Pipeline:** [brd](.claude/skills/brd/SKILL.md) · [spec](.claude/skills/spec/SKILL.md) · [design](.claude/skills/design/SKILL.md) · [build](.claude/skills/build/SKILL.md) · [auto](.claude/skills/auto/SKILL.md) · [implement](.claude/skills/implement/SKILL.md) · [evaluate](.claude/skills/evaluate/SKILL.md) · [review](.claude/skills/review/SKILL.md) · [test](.claude/skills/test/SKILL.md) · [deploy](.claude/skills/deploy/SKILL.md)
- **Maintenance:** [fix-issue](.claude/skills/fix-issue/SKILL.md) · [refactor](.claude/skills/refactor/SKILL.md) · [improve](.claude/skills/improve/SKILL.md) · [lint-drift](.claude/skills/lint-drift/SKILL.md)
- **Reference:** [architecture](.claude/skills/architecture/SKILL.md) · [code-gen](.claude/skills/code-gen/SKILL.md) · [testing](.claude/skills/testing/SKILL.md) · [evaluation](.claude/skills/evaluation/SKILL.md)

## Hooks (`.claude/hooks/`, wired in [.claude/settings.json](.claude/settings.json))

- **WealthWise (PreToolUse):** [allocation-sum-invariant-check](.claude/hooks/allocation-sum-invariant-check.js) · [template-immutability-check](.claude/hooks/template-immutability-check.js) · [pii-redaction-check](.claude/hooks/pii-redaction-check.js) · [no-float-money-check](.claude/hooks/no-float-money-check.js)
  - Shared code: [lib/](.claude/hooks/lib/) · Tests: [run-wealthwise-hook-tests.js](.claude/hooks/tests/run-wealthwise-hook-tests.js) · Results: [docs/hooks-verification.md](docs/hooks-verification.md)
- **PreToolUse:** [enforce-length-pre](.claude/hooks/enforce-length-pre.js)
- **PostToolUse (Edit/Write):** [scope-directory](.claude/hooks/scope-directory.js) · [protect-env](.claude/hooks/protect-env.js) · [detect-secrets](.claude/hooks/detect-secrets.js) · [lint-on-save](.claude/hooks/lint-on-save.js) · [typecheck](.claude/hooks/typecheck.js) · [check-architecture](.claude/hooks/check-architecture.js) · [check-function-length](.claude/hooks/check-function-length.js) · [check-file-length](.claude/hooks/check-file-length.js) · [track-writes](.claude/hooks/track-writes.js)
- **PostToolUse (Bash):** [pre-commit-gate](.claude/hooks/pre-commit-gate.js) · [sprint-contract-gate](.claude/hooks/sprint-contract-gate.js)
- **Stop:** [require-review](.claude/hooks/require-review.js)
- **TaskCompleted:** [task-completed](.claude/hooks/task-completed.js)
- **TeammateIdle:** [teammate-idle-check](.claude/hooks/teammate-idle-check.js)

## MCP and plugin

- [.mcp.json](.mcp.json): Playwright MCP
- [plugin.json](plugin.json): WealthWise substrate plugin manifest (hooks: [wealthwise-hooks.json](.claude/hooks/wealthwise-hooks.json))
- [.claude/.claude-plugin/plugin.json](.claude/.claude-plugin/plugin.json): Harness plugin manifest

## Scripts

- [scripts/ac_coverage.py](scripts/ac_coverage.py): AC → test traceability
- [scripts/agent_sdk_review.py](scripts/agent_sdk_review.py): Claude Agent SDK spec-vs-code review → [specs/reviews/](specs/reviews/)

## Reference docs

- [docs/business-case.md](docs/business-case.md)
- [docs/harness/harness-overview.md](docs/harness/harness-overview.md)
- [.claude/program.md](.claude/program.md) · [.claude/architecture.md](.claude/architecture.md)
- [docs/phase-reviews/](docs/phase-reviews/): phase reviews
- [docs/prs/](docs/prs/): earlier PR descriptions (PR-001…PR-003)
