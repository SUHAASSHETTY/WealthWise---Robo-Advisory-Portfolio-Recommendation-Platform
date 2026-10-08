# Knowledge Deposits & Encodings

This document captures recurring failure modes, architectural anti-patterns, and domain hazards encountered across the development of WealthWise, along with the automated rule, hook, skill, or test into which each lesson was permanently encoded.

---

## Catalog of Encoded Lessons

### 1. Floating-Point Arithmetic in Financial Precision (NFR-01)
- **Failure Mode:** Using Python `float` or JavaScript `Number` for asset quantities, NAV values, percentage allocations, or drift calculations leads to cumulative rounding inaccuracies (e.g. `0.1 + 0.2 = 0.30000000000000004`), breaking invariant checks.
- **Encoded Rule:** `specs/app_spec.md` §5.1, root `CLAUDE.md` Rule 6.
- **Enforcing Hook:** `.claude/hooks/no-float-money-check.js` (blocks any `float` types or float literals in domain/services).
- **Architecture Test:** `tests/architecture/test_no_float_money.py`.
- **System Pattern:** All backend money/percentages use `decimal.Decimal` with string constructors (`Decimal("100.00")`), database storage via `DecimalText`, and frontend representation via fixed-point formatted strings.

---

### 2. Allocation Matrices Not Summing to Exactly 100.00% (AC-02, AC-10)
- **Failure Mode:** Manually drafted templates or migration rows having subtle discrepancies (e.g. 99.99% or 100.01%), causing recommendations or rebalancing to generate unbalanced portfolios.
- **Encoded Rule:** `specs/recommendation_spec.md` §2.4, `specs/admin_versioning_spec.md`.
- **Enforcing Hook:** `.claude/hooks/allocation-sum-invariant-check.js` (performs integer hundredths summation across all asset class allocations in PreToolUse).
- **Enforcing Skill:** `.claude/skills/allocation-template-resolver/SKILL.md`.
- **Domain Guard:** `app.domain.template_version_validator.parse_template_version` raises `PolicyInvalid`.

---

### 3. Mutating Published Policy Versions or Approved Migrations (NFR-02, AC-10)
- **Failure Mode:** Editing already-published template definitions or past Alembic migrations in-place, which corrupts historical auditability and breaks in-flight customer version pinning.
- **Encoded Rule:** `specs/admin_versioning_spec.md`, root `CLAUDE.md` Rule 4.
- **Enforcing Hook:** `.claude/hooks/template-immutability-check.js` (blocks edits to locked migrations or `PUBLISHED` template JSON files).
- **Database Listener:** `backend/app/repositories/guards.py` `protect_append_only` listener on SQLAlchemy ORM models.
- **Architecture Test:** `tests/architecture/test_published_templates_immutable.py` and `tests/architecture/test_append_only_tables.py`.

---

### 4. PII & Financial Holdings Leaking into System Logs (NFR-03)
- **Failure Mode:** Logging client names, emails, raw PAN identifiers, or customer portfolio monetary values in stdout logs or exception traces.
- **Encoded Rule:** `specs/app_spec.md` §5.6, root `CLAUDE.md` Rule 7.
- **Enforcing Hook:** `.claude/hooks/pii-redaction-check.js` (blocks logging or print calls referencing forbidden field names).
- **Logging Formatter:** `backend/app/core/logging.py` `StrictJsonFormatter` allow-lists only safe keys (`customer_id`, `line_count`, `duration_ms`, `correlation_id`).

---

### 5. Non-Deterministic System Clock Invocations
- **Failure Mode:** Invoking `datetime.now()` or `date.today()` inside pure domain policies or service functions, making goal horizon calculations and drift test runs non-reproducible across timezones and execution dates.
- **Encoded Rule:** Root `CLAUDE.md` Determinism rule.
- **Enforcing Pattern:** Injected `Clock` dependency protocol (`AnchoredClock` for tests and deterministic replay, `SystemClock` for production runtime).

---

### 6. Layering Violations & Upward Imports (API → Repository Direct Access)
- **Failure Mode:** FastAPI routers directly querying SQLAlchemy repositories or domain rules importing HTTP models.
- **Encoded Rule:** Root `CLAUDE.md` Stack & Layout.
- **Enforcing Gate:** `backend/.importlinter` / `lint-imports` contract suite and `tests/architecture/test_layering.py`.
- **Architecture Hierarchy:** Strict unidirectional dependency flow: `api` → `services` → `repositories` → `domain` (with pure domain containing zero I/O).
