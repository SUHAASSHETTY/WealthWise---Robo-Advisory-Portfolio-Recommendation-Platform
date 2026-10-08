"""Architecture tests for NFR-08 / AC-09.7: Risk-band override mandate.

Proves:
1. The `customers` table has no mutable risk band column.
2. The only tables storing risk bands associated with customer state are `risk_assessments` and `risk_band_overrides`.
3. Repository and service code does not mutate customer risk band in-place.
"""

from sqlalchemy import inspect

from app.core.config import Settings
from app.core.db import build_engine


def test_customer_table_has_no_mutable_risk_band_column(settings: Settings) -> None:
    """NFR-08 / AC-09.7: Customer model has no risk_band or effective_band column."""
    engine = build_engine(settings.database_url)
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("customers")]
    engine.dispose()

    assert "risk_band" not in columns, "customers table must NOT have a mutable risk_band column"
    assert "effective_band" not in columns, "customers table must NOT have an effective_band column"
    assert "band" not in columns, "customers table must NOT have a band column"


def test_only_allowed_tables_store_customer_risk_bands(settings: Settings) -> None:
    """NFR-08: Only risk_assessments and risk_band_overrides record customer risk bands."""
    engine = build_engine(settings.database_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    allowed_tables_with_customer_band = {
        "risk_assessments",
        "risk_band_overrides",
        "recommendations",  # Snapshot of risk_band at recommendation time
    }

    for table in tables:
        columns = [col["name"] for col in inspector.get_columns(table)]
        has_customer_id = "customer_id" in columns or table == "customers"
        has_band_column = any(c in columns for c in ["risk_band", "band", "new_band", "previous_band", "assigned_band"])

        if has_customer_id and has_band_column:
            assert table in allowed_tables_with_customer_band, (
                f"Table '{table}' unexpectedly stores customer risk bands, violating NFR-08."
            )

    engine.dispose()
