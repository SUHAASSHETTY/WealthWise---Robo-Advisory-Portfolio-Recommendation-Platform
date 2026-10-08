# backend/: FastAPI service

Read the root `CLAUDE.md` first. This file adds backend-wide rules. Each `app/<layer>/CLAUDE.md` adds layer rules.

## Project shape

- A Poetry project: `backend/pyproject.toml`, Python 3.12. Run every tool from `backend/` with `poetry run …`.
- `app/main.py` creates the FastAPI app with an `@asynccontextmanager` lifespan (engine created, then disposed). Don't use `on_event`.
- `app/core/`:
  - `config.py`: pydantic-settings; all env vars documented in `backend/.env.example`;
  - `logging.py`: JSON formatter, allow-list filter, correlation-ID context;
  - `db.py`: engine, session factory, `DecimalText` TypeDecorator;
  - `security.py`: JWT, bcrypt;
  - `clock.py`: the `Clock` protocol and `SystemClock`.
- `migrations/`: Alembic. **Never edit a revision from an approved phase.** Add a new one. Hashes are locked in `migrations/LOCKED_HASHES.txt`.
- `app/seed/`: synthetic users, customers, holdings, goals, and `nav_series.csv`.

## Backend-wide rules

- **Decimal (NFR-01):**
  - all money, percent, units and NAV are `Decimal`;
  - DB columns use `DecimalText(scale)`, never `Float` or `Numeric` (SQLite stores Numeric as REAL);
  - Pydantic fields for decimals are `str` patterns at the boundary, converted to `Decimal` in the schema validator;
  - input as a JSON number returns `422 DECIMAL_MUST_BE_STRING`.
- **Errors:**
  - domain and service code raise typed exceptions from `app/domain/errors.py` or `app/services/errors.py`;
  - only `app/api/errors.py` maps them to HTTP and the error envelope;
  - no bare `except Exception` outside the top-level handler.
- **Logging (NFR-03/06):**
  - `logger = logging.getLogger(__name__)`; structured `extra={…}` only, with no f-string interpolation of data;
  - allowed keys are listed in `app/core/logging.py` (`ALLOWED_LOG_KEYS`), and anything else is dropped.
- **Time:** inject `Clock`. UTC timestamps everywhere; `DATE` columns for business dates.
- **IDs:** UUID4 for every entity.
- **Config:** no magic numbers in services. Policy numbers (points, thresholds, templates, drift threshold) come from the **active policy version**, never from constants. Operational settings come from `config.py`.
- **Size limits (Harness hooks):** files under 300 lines (warn at 200), functions ≤ 50 lines.

## Testing hookup

- The repo-root `pytest.ini` is the only pytest config: `pythonpath = backend`, `--import-mode=importlib`, the `ac(id)` marker, and `--cov=app --cov-report=xml:../coverage.xml`. Run with `poetry run pytest ../tests` (or explicit `../tests/...` paths) from `backend/`. A bare `poetry run pytest` collects nothing, because `testpaths` only applies when invoked from the rootdir.
- `pytest-cov` is a declared dev dependency; the coverage artefact `coverage.xml` is kept in the repo (brief §7.4).
- Import-linter contracts live in `backend/.importlinter` (run `poetry run lint-imports` from `backend/`):
  - layers `app.api > app.services > app.repositories > app.domain`;
  - `app.domain` is forbidden from importing `app.core`, `sqlalchemy`, `fastapi` and `pydantic`.
