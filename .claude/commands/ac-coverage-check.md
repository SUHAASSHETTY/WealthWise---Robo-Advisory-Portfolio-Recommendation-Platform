---
name: ac-coverage-check
description: List every WealthWise acceptance criterion (AC-01..AC-10) with its spec scenarios and the tests that reference it; FAIL if any AC has no test.
argument-hint: "[--strict]"
---

# /ac-coverage-check

Report AC → test traceability and fail when coverage is missing. This enforces the brief's rule that every AC has at least one test referencing its ID.

## Steps

1. Run the coverage scanner from the project root (pass `--strict` through if the user gave it):

   ```bash
   python3 scripts/ac_coverage.py $ARGUMENTS
   ```

   It reads the AC map in `specs/app_spec.md` §6 and the `**AC-NN.k**` scenarios in `specs/*_spec.md`. Then it scans:
   - `tests/**/test_*.py` for `@pytest.mark.ac("AC-NN")` functions, and cited `AC-NN.k` IDs;
   - `frontend/e2e/**/*.spec.ts` for `test('AC-NN: …')` titles.

2. Show the user the table exactly as printed. For each AC it gives the scenario count, test count, `OK` or `MISSING`, and the test list. With `--strict`, it also lists uncited scenarios.

3. Interpret the result:
   - **Exit code 0 / `RESULT: PASS`:** every AC has at least one test (and, with `--strict`, every scenario is cited).
   - **Exit code 1 / `RESULT: FAIL`:** list the `MISSING` ACs, and the uncited scenarios in strict mode. **The phase can't be approved** until they are covered. Point to `.claude/skills/spec-to-test-generator/SKILL.md` for how to add the tests.

4. If the user is preparing a phase review, paste the full output verbatim under "Real test output".

## Notes

- This checks **traceability**, not pass or fail. Run `cd backend && poetry run pytest -m ac` to execute the tagged tests.
- Never add a marker to an unrelated test just to make this pass. The marker must match what the test actually asserts.
