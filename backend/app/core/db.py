"""Database engine/session factory and the DecimalText column type (app_spec §5.1, NFR-01).

SQLite stores NUMERIC as REAL (binary float), so exact decimals are persisted as canonical TEXT instead.
"""

from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import Engine, String, create_engine
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.types import TypeDecorator


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


class DecimalText(TypeDecorator[Decimal]):
    """Stores a Decimal quantised to `scale` places as TEXT; refuses floats and other types."""

    impl = String(40)
    cache_ok = True

    def __init__(self, scale: int) -> None:
        super().__init__()
        self.scale = scale
        self._quantum = Decimal(1).scaleb(-scale)

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError(f"DecimalText requires Decimal, got {type(value).__name__}")
        return str(value.quantize(self._quantum, rounding=ROUND_HALF_EVEN))

    def process_result_value(self, value: str | None, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(value)
