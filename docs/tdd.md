# Test-driven development in WealthWise

**Audience:** engineers and agents generating WealthWise code. **Applies to:** every production change (root `CLAUDE.md`, Phase workflow step 3).

## The cycle

Every behaviour starts as a failing test that cites the spec scenario it proves.

1. **Red.** Write the test from the spec's Given–When–Then. Tag it `@pytest.mark.ac("AC-NN")`, name it `test_ac_NN_…`, and cite the scenario `AC-NN.k` in the docstring. Copy expected values **verbatim** from the spec. Run it and confirm it fails **for the right reason**:
   - a missing module or function on the very first run; or
   - an assertion failure against a minimal interface stub.

   An `ImportError` from a misconfigured path is *not* a valid red: fix the harness and re-run.
2. **Green.** Write the minimum production code that passes. No behaviour beyond what the tests demand.
3. **Refactor.** Improve names, structure and types without changing behaviour. Re-run the same tests; they must stay green. Run `ruff`, `mypy --strict` and `lint-imports` too.
4. **Record.** Paste the real red, green and refactor output into [docs/tdd-log.md](tdd-log.md), and summarise it in the phase review. **Never invent output.**

Rules that make the cycle trustworthy:
- **Fix the code, never the test** (Harness self-healing rule). A test changes only when its spec changes, or when the test itself is wrong. In that case, say so explicitly in the log, as entry TDD-003 does.
- **Decimal only.** Expected values are `Decimal("…")` or exact strings, with no float tolerances.
- **Only real boundaries get mocks:** the clock, I/O and external services. Domain logic never does.

## Worked example: AC-02 allocation-sum invariant

**Spec:** `specs/recommendation_spec.md`:
- §2.1 lists the v1 templates;
- §2.4 is the invariant: every allocation sums to **exactly** `Decimal("100.00")`, and each value is 2 dp within [0.00, 100.00];
- AC-02.4: a corrupted MODERATE row summing to 99.99 must raise `AllocationSumError`.

**Test file:** `tests/unit/domain/allocation/test_templates.py`. Its tests were written before any of `app/domain/allocation/` existed:

```python
@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    ("band", "asset_class", "value", "message"),
    [
        ("MODERATE", "CASH", "4.99", "MODERATE sum=99.99"),
        ("AGGRESSIVE", "GOLD", "7.51", "AGGRESSIVE sum=100.01"),
    ],
)
def test_ac_02_corrupted_template_raises_allocation_sum_error(band, asset_class, value, message):
    """AC-02.4 — a template row that does not sum to 100.00 is rejected."""
    with pytest.raises(AllocationSumError, match=message):
        parse_template_set(_with(band, asset_class, value))
```

The other tests in the file cover:
- the v1 templates parse to exact Decimals summing to 100.00;
- values below 0, above 100, or with more than 2 dp are rejected;
- float input raises `TypeError`;
- an empty band is rejected.

### Red #1: the module doesn't exist (`cd backend && poetry run pytest ../tests/unit/domain/allocation/test_templates.py --no-cov`)

```
==================================== ERRORS ====================================
_______ ERROR collecting tests/unit/domain/allocation/test_templates.py ________
ImportError while importing test module '/Users/suhaas/Desktop/wealthwise/tests/unit/domain/allocation/test_templates.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
../tests/unit/domain/allocation/test_templates.py:9: in <module>
    from app.domain.allocation.templates import AllocationSumError, parse_template_set
E   ModuleNotFoundError: No module named 'app.domain.allocation'
=========================== short test summary info ============================
ERROR ../tests/unit/domain/allocation/test_templates.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.05s
exit=2
```

The first attempt failed with `No module named 'app'`. That was the **wrong** red: pytest wasn't putting `backend/` on `sys.path` when given explicit `../tests` paths. The harness was fixed (a root `pytest.ini` with `pythonpath = backend`) before the run above. See TDD-001 in the log.

### Red #2: an interface stub that parses but doesn't validate

```python
class AllocationSumError(ValueError):
    """An allocation violates the exact-100.00 invariant."""

def parse_template_set(templates):
    return {band: {cls: Decimal(str(v)) for cls, v in row.items()} for band, row in templates.items()}
```

Real output, trimmed to the first failure plus the verbatim summary:

```
.FFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
_ test_ac_02_corrupted_template_raises_allocation_sum_error[MODERATE-CASH-4.99-MODERATE sum=99.99] _
...
        """AC-02.4 — a template row that does not sum to 100.00 is rejected."""
>       with pytest.raises(AllocationSumError, match=message):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE AllocationSumError

../tests/unit/domain/allocation/test_templates.py:46: Failed
...
=========================== short test summary info ============================
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_corrupted_template_raises_allocation_sum_error[MODERATE-CASH-4.99-MODERATE sum=99.99]
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_corrupted_template_raises_allocation_sum_error[AGGRESSIVE-GOLD-7.51-AGGRESSIVE sum=100.01]
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_each_percentage_must_be_two_dp_within_0_and_100[-5.00-outside]
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_each_percentage_must_be_two_dp_within_0_and_100[100.01-outside]
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_each_percentage_must_be_two_dp_within_0_and_100[7.505-2 decimal places]
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_float_percentage_is_rejected
FAILED ../tests/unit/domain/allocation/test_templates.py::test_ac_02_empty_band_is_rejected
7 failed, 1 passed in 0.02s
exit=1
```

Every invariant test fails for the right reason: `DID NOT RAISE`. Only the happy path passes, which is expected because the stub parses valid input.

### Green: minimum implementation

`app/domain/money.py` gained `to_decimal`, which rejects float and bool. `app/domain/allocation/templates.py` now parses each value, checks for ≤ 2 dp and the [0, 100] range, and compares the sum with `Decimal("100")`:

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/suhaas/Desktop/wealthwise
configfile: pytest.ini
plugins: cov-7.1.0, anyio-4.15.1
collected 23 items

../tests/unit/domain/allocation/test_templates.py ........               [ 34%]
../tests/unit/domain/test_money.py ...............                       [100%]

============================== 23 passed in 0.02s ==============================
exit=0
```

### Refactor: same behaviour, better structure

The green version needed two `# type: ignore` comments and mixed parsing with the sum rule. The refactor:
- splits `parse_percentage(band, asset_class, raw)` from `validate_allocation(band, allocation)`. The latter is reused later for recommendations and manual allocations (AC-09.8);
- replaces the exponent check with `value != value.quantize(CENT)`;
- types the input as `str | int | Decimal`;
- reports the sum through `q2`.

```
.......................                                                  [100%]
23 passed in 0.01s
exit=0
```

After the refactor, `mypy app/domain` (strict) reports `Success: no issues found in 4 source files`, and ruff passes once line length and import order are fixed.

### Where the invariant is enforced afterwards

| Layer | Check |
|---|---|
| Domain | `parse_template_set` / `validate_allocation` (this example) |
| Architecture test | `tests/architecture/test_allocation_sum_invariant.py` validates every PUBLISHED seed template |
| Editor-time hook | `.claude/hooks/allocation-sum-invariant-check.js` blocks seed or template writes whose rows don't sum to 100.00 |
