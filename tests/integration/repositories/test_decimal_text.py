"""NFR-01 — DecimalText persists exact decimals as TEXT on SQLite (Numeric would be stored as REAL)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select
from sqlalchemy.exc import StatementError

from app.core.clock import FixedClock, SystemClock
from app.core.db import DecimalText, build_engine

metadata = MetaData()
amounts = Table(
    "amounts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("money", DecimalText(2)),
    Column("units", DecimalText(4)),
)


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    eng = build_engine("sqlite://")
    metadata.create_all(eng)
    yield eng
    eng.dispose()


def test_decimal_round_trips_exactly_at_column_scale(engine) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as conn:
        conn.execute(insert(amounts).values(id=1, money=Decimal("100000.00"), units=Decimal("66.6666")))
        row = conn.execute(select(amounts.c.money, amounts.c.units)).one()

    assert row.money == Decimal("100000.00")
    assert row.units == Decimal("66.6666")
    assert isinstance(row.money, Decimal)


def test_value_is_quantised_half_even_to_column_scale(engine) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as conn:
        conn.execute(insert(amounts).values(id=2, money=Decimal("12.345"), units=None))
        stored = conn.exec_driver_sql("SELECT money, units FROM amounts WHERE id = 2").one()

    assert stored[0] == "12.34"
    assert stored[1] is None


def test_float_is_refused_at_bind_time(engine) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as conn, pytest.raises(StatementError, match="DecimalText requires Decimal"):
        conn.execute(insert(amounts).values(id=3, money=0.1))


def test_fixed_clock_is_deterministic_and_system_clock_is_utc() -> None:
    fixed = FixedClock(datetime(2026, 1, 15, 9, 30, tzinfo=UTC))

    assert fixed.today() == date(2026, 1, 15)
    assert fixed.now() == datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
    assert SystemClock().now().tzinfo is UTC
    assert isinstance(SystemClock().today(), date)
