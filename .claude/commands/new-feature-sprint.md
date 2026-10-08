---
name: new-feature-sprint
description: Run one WealthWise feature sprint end-to-end — spec check, sprint contract, TDD implementation by the owning domain agent, evaluation, AC coverage, phase review — then stop for approval.
argument-hint: "<phase-number> <feature> (e.g. 03 risk_profile)"
---

# /new-feature-sprint

Arguments: `$ARGUMENTS` gives `NN feature`, where `feature` names a `specs/<feature>_spec.md`.

## 0. Preconditions (stop if any fail)

- [ ] The human has put the repo on the branch they want for this phase. Claude never runs git write commands.
- [ ] `specs/<feature>_spec.md` exists and contains an `Acceptance criteria` section.
- [ ] The previous phase review in `docs/phase-reviews/` is marked APPROVED.

## 1. Git

Claude makes no git writes (root CLAUDE.md rule 3). All changes stay uncommitted for the human to branch, commit, merge and push.

## 2. Load context

Read:
- root `CLAUDE.md` and the layer CLAUDE.md files for every layer touched;
- `specs/app_spec.md` §5, and `specs/<feature>_spec.md` in full;
- the matching skill:

| Feature | Owning agent | Skill(s) |
|---|---|---|
| `risk_profile` | `risk-profiler-agent` | `risk-band-scorer` |
| `recommendation` | `recommendation-engine-agent` | `allocation-template-resolver`, `goal-progress-tracker` |
| `holdings`, `rebalancing` | `rebalancing-agent` | `drift-calculator`, `rebalancing-quantity-proposer` |
| `goal_tracker` | `generator` | `goal-progress-tracker` |
| `advisor_workbench`, `admin_versioning` | `generator` (+ `policy-version-validator-agent` for verification) | `allocation-template-resolver`, `risk-band-scorer` |

Every agent also reads `spec-to-test-generator` and `.claude/state/learned-rules.md`.

## 3. Sprint contract

Write `sprint-contracts/<feature>.json`, following `.claude/skills/evaluation/references/contract-schema.json`:
- `api_checks` for each API-level AC scenario;
- `playwright_checks` once the UI exists;
- `architecture_checks`.

Then have the `evaluator` agent finalise it. After that, it is immutable.

## 4. Implement (TDD)

Delegate to the owning agent from the table, with the AC scenario list and file scope. For each scenario:
1. Write the failing test and run it; capture the **red** output.
2. Implement.
3. Run again for **green**, then refactor.

Don't commit. Paste the red and green output into the phase review instead.

## 5. Verify

```bash
cd backend && poetry run pytest                  # full suite + coverage.xml
cd backend && poetry run ruff check . && poetry run mypy app && poetry run lint-imports
python3 scripts/ac_coverage.py                    # /ac-coverage-check
```

Run `/evaluate <feature>` if the app is runnable, so the evaluator writes `specs/reviews/evaluator-report.md`. Run `/review` for the security review too.

If something fails, self-heal up to 3 attempts using the Harness categories. **Never auto-revert.** After the 3rd failure, log to `.claude/state/failures.md` and stop.

## 6. Phase review and stop

Write `docs/phase-reviews/PHASE-NN-<feature>.md` with:
- Summary;
- Files changed;
- ACs covered (from `ac_coverage.py`);
- **Real test output** (red and green excerpts, the full pytest summary and the coverage total);
- Review checklist.

Leave everything uncommitted, then **stop** and wait for human approval.
