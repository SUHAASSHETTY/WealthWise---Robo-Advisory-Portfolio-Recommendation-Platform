"""Shared pytest fixtures. App imports happen inside fixtures so pure domain tests stay importable alone."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from app.core.config import Settings


BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


@pytest.fixture(scope="session")
def migrated_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run `alembic upgrade head` once per test session on an empty SQLite file (schema + v1 seed)."""
    from alembic import command
    from alembic.config import Config

    db_path = tmp_path_factory.mktemp("migrated") / "template.db"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


@pytest.fixture
def migrated_db_copy(migrated_db_path: Path, tmp_path: Path) -> Path:
    """A private copy of the migrated database for one test."""
    target = tmp_path / "test.db"
    shutil.copyfile(migrated_db_path, target)
    return target


@pytest.fixture
def settings(migrated_db_copy: Path) -> Settings:
    from app.core.config import Settings

    return Settings(_env_file=None, database_url=f"sqlite:///{migrated_db_copy}", stub_auth_enabled=True)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(settings)) as test_client:
        yield test_client
