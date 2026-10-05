# specs/: how to read and change specs

The specs are the source of truth (Spec-Is-Truth). Code is generated *from* them.

## Files

- `app_spec.md`: the root. System boundary, cross-cutting rules (Decimal, append-only, auth, logging, errors, health, migrations), and the AC and NFR maps.
- `<feature>_spec.md`: one per feature. Each has the same sections: **Purpose, Domain Rules, Data Model, API Contract, Acceptance Criteria, NFR Mapping**.
- Harness outputs live under this folder too: `brd/`, `stories/`, `design/`, `reviews/`, `test_artefacts/`. Those are generated artefacts, not hand-written specs.

## Rules for agents

1. **Never change behaviour in code that a spec doesn't describe.** If the code needs to differ, stop and change the spec first, and list the change under "Spec changes" in the phase review, before regenerating the code.
2. **AC IDs are stable.** `AC-01`…`AC-10` come from the brief and are never renumbered. Scenarios within an AC are `AC-NN.k`. Add new scenarios with the next `k`; never reuse a retired `k`.
3. **Every AC scenario needs a test** tagged with `@pytest.mark.ac("AC-NN")` (pytest) or titled `AC-NN: …` (Playwright). Untested scenarios block phase approval.
4. **Numbers in specs are normative.** Points, thresholds, template percentages, rounding modes and limits are exact. Code must take them from the active policy version, never hard-code a copy.
5. **Keep Given–When–Then concrete.** Use actual values, not "valid input".
6. **Changing a published policy value** (points, thresholds, templates) means a *new policy version* (see `admin_versioning_spec.md`), never an edit to v1.
7. **Cross-check after any spec edit:** the AC map and NFR map in `app_spec.md` still match, and every API route appears in the §8 summary.
