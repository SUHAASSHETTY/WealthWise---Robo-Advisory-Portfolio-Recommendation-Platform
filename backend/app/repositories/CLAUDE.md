# backend/app/repositories/: persistence

SQLAlchemy 2.x models and repositories. This is the only layer that talks to the database.

## Allowed imports

`app.domain` (to map rows ↔ domain value objects) and `app.core` (`db`, `DecimalText`). Never `app.services` or `app.api`.

## Rules

- **Models** live in `models/` (one file per aggregate). **Repositories** are one class per aggregate, receive a `Session`, and return domain objects or typed rows, never raw dicts.
- **Column types:**
  - money and percent: `DecimalText(2)`;
  - units and NAV: `DecimalText(4)`;
  - **no `Float` or `Numeric` columns.** `tests/architecture/test_no_float_money.py` scans the models.
- **Append-only tables** (app_spec §5.3):
  - their repositories expose `add`/`get`/`list` only, with no `update` or `delete`;
  - `append_only.py` registers `before_update`/`before_delete` listeners that raise `AppendOnlyViolation` for those models.
- **Published policy versions:** a `before_update`/`before_delete` listener raises `PublishedVersionMutation` when the persisted `status` is `PUBLISHED` (admin_versioning §2.1).
- **No mutable band column.** A customer's risk band is never stored on `customers`; it is derived from `risk_assessments` and `risk_band_overrides` (NFR-08).
- **Constraints:** enums are SQL enums or CHECK constraints. Add a UNIQUE constraint wherever a spec says "one per…":
  - `rebalancing_decisions.rebalancing_recommendation_id`;
  - (`customer_id`, `asset_class_code`) on holdings;
  - (`asset_class_code`, `nav_date`) on NAV;
  - one DRAFT per policy type.
- **Every schema change ships with an Alembic revision** in the same phase. Don't edit revisions from approved phases. Seed and policy data go in as new rows.
- **No business logic** here: no drift, scoring or allocation maths.
- **Tests:** `tests/integration/repositories/`, including append-only and immutability guard tests.
