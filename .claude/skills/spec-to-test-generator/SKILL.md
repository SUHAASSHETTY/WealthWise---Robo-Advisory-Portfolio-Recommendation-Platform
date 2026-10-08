---
name: spec-to-test-generator
description: Turn WealthWise spec acceptance criteria (AC-NN.k Given–When–Then scenarios) into tagged, layer-appropriate tests — pytest markers, naming, file placement, worked-example parametrisation and Playwright titles. Use before writing any test for an AC.
---

# Spec → Test Generator

Every AC scenario `AC-NN.k` in `specs/*_spec.md` must have at least one test. `/ac-coverage-check` fails the phase otherwise.

## Step 1: locate the scenario

The AC → spec map is in `specs/app_spec.md` §6. Each scenario is a bold `**AC-NN.k Title.**` bullet with **Given / When / Then** sub-bullets.

## Step 2: pick the layer

| Scenario talks about… | Test layer | Folder |
|---|---|---|
| Pure calculation (scores, allocations, drift, quantities, progress) | Unit | `tests/unit/domain/<module>/` |
| Persistence, append-only and immutability guards | Integration (repositories) | `tests/integration/repositories/` |
| A use case's final state or row counts | Integration (services) | `tests/integration/services/` |
| HTTP status, response body or roles | Acceptance (API) | `tests/acceptance/test_ac_<feature>.py` |
| A structural rule (NFR-08, layering) | Architecture | `tests/architecture/` |
| A UI flow | E2E | `frontend/e2e/<feature>.spec.ts` |

Prefer **one unit test plus one acceptance test** for calculation ACs: the unit test proves the formula, and the acceptance test proves the wiring.

## Step 3: name and tag

```python
import pytest

@pytest.mark.ac("AC-04")
def test_ac_04_horizon_adjustment_moves_20_points_for_48_month_goal() -> None:
    """AC-04.1 — MODERATE, clock 2026-01-15, goal 2030-01-15 → 30/55/10/5, H_36_59."""
```

- Marker `ac("AC-NN")`, registered in `backend/pyproject.toml`.
- Name prefix `test_ac_NN_`, then the behaviour in words.
- The docstring cites the exact scenario ID `AC-NN.k`.
- **Playwright:** `test('AC-05: holdings table shows drift per asset class', …)`.

## Step 4: map Given / When / Then → Arrange / Act / Assert

| GWT | Test code |
|---|---|
| **Given** | Fixtures and factories with the spec's exact values (synthetic Alice, Bob, Carol); a fixed `Clock` |
| **When** | One call (domain function, service method or HTTP request) |
| **Then** | Assert **every** value in the Then clause, using `Decimal("…")` or string equality for JSON, plus row counts for append-only effects |

## Step 5: worked examples → parametrise verbatim

```python
@pytest.mark.ac("AC-04")
@pytest.mark.parametrize(("band", "months", "rule", "expected"), [
    ("MODERATE", 120, "H_84_PLUS", ("50.00", "35.00", "10.00", "5.00")),
    ("MODERATE", 48, "H_36_59", ("30.00", "55.00", "10.00", "5.00")),
    ("AGGRESSIVE", 24, "H_12_35", ("45.00", "45.00", "7.50", "2.50")),
    ("CONSERVATIVE", 24, "H_12_35", ("0.00", "80.00", "10.00", "10.00")),
    ("AGGRESSIVE", 6, "H_0_11", ("0.00", "15.00", "7.50", "77.50")),
])
def test_ac_04_worked_examples(band, months, rule, expected, template_v1) -> None:
    """AC-04.2 — recommendation_spec §2.3 rows."""
```

**Never recompute expected values in the test.** Copy them from the spec. If the spec value looks wrong, stop and raise a spec change.

## Step 6: red before green

1. Write the test and run it: `cd backend && poetry run pytest ../tests/<path>::<test> -q`. It must **fail for the right reason** (assertion or ImportError of the not-yet-written function).
2. Paste the red output into the phase review, implement, re-run green, and paste that too.

## Checklist per AC

- [ ] Every `AC-NN.k` has at least one test that cites it in the docstring
- [ ] Every value in the Then clause is asserted, with Decimal or string comparison and no float tolerance
- [ ] Error scenarios assert the exact error code (`422 OPTION_INVALID`, …) **and** that no rows were written
- [ ] Append-only scenarios assert the row count and the guard exception
