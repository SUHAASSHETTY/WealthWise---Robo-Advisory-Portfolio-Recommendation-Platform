"""Integration tests for holdings service layer (holdings_spec §4, AC-05)."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.repositories import holding_repository
from app.services import holdings_service
from app.services.errors import ServiceError

ALICE_ID = "00000000-0000-4000-8000-00000000c001"


@pytest.fixture
def session(settings: Settings) -> Iterator[Session]:
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    with factory() as sess:
        yield sess
    engine.dispose()


@pytest.mark.ac("AC-05")
def test_ac_05_holdings_service_nav_not_loaded_raises_409(settings: Settings) -> None:
    """AC-05: When no NAVs are loaded in DB, service raises 409 NAV_NOT_LOADED."""
    # Use empty in-memory DB without NAVs
    engine = build_engine("sqlite:///:memory:")
    from app.repositories.base import Base

    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory() as empty_session:
        with pytest.raises(ServiceError) as exc_info:
            holdings_service.get_holdings(empty_session, ALICE_ID)
        assert exc_info.value.status == 409
        assert exc_info.value.code == "NAV_NOT_LOADED"
    engine.dispose()


@pytest.mark.ac("AC-05")
def test_ac_05_holdings_service_success(session: Session) -> None:
    """AC-05.1: Alice holdings fetched via service returns exact valuation."""
    view = holdings_service.get_holdings(session, ALICE_ID)
    assert view.nav_date == date(2026, 1, 15)
    assert view.total_value == Decimal("100000.00")
    assert len(view.lines) == 4


@pytest.mark.ac("AC-05")
def test_ac_05_holding_repository_set_units(session: Session) -> None:
    """Holding repository upsert: update existing holding and insert new holding."""
    # Update existing
    h1 = holding_repository.set_units(session, ALICE_ID, "EQUITY_US", Decimal("350.0000"))
    assert h1.units == Decimal("350.0000")

    # Insert new
    h2 = holding_repository.set_units(session, ALICE_ID, "REAL_ESTATE", Decimal("50.0000"))
    assert h2.units == Decimal("50.0000")
    assert h2.asset_class_code == "REAL_ESTATE"
