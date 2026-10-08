# Sprint 1 contract: evaluation environment

The contract JSON schema forbids extra keys, so these preconditions live here.

- **Mode:** lean (no design critic). Verification mode: `local` (Harness overview §8.1f).
- **Fresh database:**
  ```bash
  cd backend && rm -f eval.db && WEALTHWISE_DATABASE_URL=sqlite:///./eval.db poetry run alembic upgrade head
  ```
- **Backend:**
  ```bash
  cd backend && WEALTHWISE_DATABASE_URL=sqlite:///./eval.db WEALTHWISE_STUB_AUTH_ENABLED=true \
    WEALTHWISE_FIXED_CLOCK=2026-01-15T09:00:00Z poetry run uvicorn app.main:app --port 8000 --no-access-log
  ```
- **Frontend:** not in scope this sprint (no story touches `frontend/`); `playwright_checks` is intentionally empty. If the generator modifies `frontend/`, the evaluator runs the existing shell smoke test as a regression check.
- **Fixed seed IDs:** risk policy v1 `00000000-0000-4000-8000-000000000201`, template v1 `00000000-0000-4000-8000-000000000101`, frank goal `…0f0001` (2030-01-15, P1), grace goal B `…0b0001` (2028-06-30, P1), grace goal A `…0a0001` (2040-01-01, P2).
- **Ordering:** api checks are **ordered and stateful** (api-001 … api-062). Run them in id order against one fresh DB, with the fixed clock above. `capture` entries (JSONPath) feed later `{placeholders}`, which are substituted in `path`, `body`, `expected_body` and assertions in `description`. Bodies written as `"<…>"` are instructions: build them from the referenced captured value (api-052: the captured draft definition with only `bands` replaced).
- **Answer sets:** ANS_16, ANS_0, ANS_28, ANS_20, ANS_CAP24 as in specs/stories/E2-S1.md; the literal answers are inlined in each check body.
- **Body matching:** `expected_body` is a **subset match** (every listed key/value must be present and equal; extra keys allowed; listed arrays must match exactly, element by element). `description` assertions are **binding**: "EXACTLY N entries", ordering, "id MUST differ", the absence of a `points` key, and the AC-10.4 violation text are all checked; a failed description assertion fails the check.
- **Test-suite gate:** `architecture_checks.layering` includes `cd backend && poetry run pytest ../tests -m ac`; it is the only verification for the pure-domain scenarios (AC-01.3, 01.5 100x, 01.7 UPDATE guard, 02.3, 02.4, 04.2, 04.5, 10.3).
