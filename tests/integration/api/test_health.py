"""NFR-07 — health endpoint returns 200 within 1 second of a successful startup."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_ok_with_database_connected(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected"}


def test_health_responds_within_one_second_of_startup(settings: Settings) -> None:
    started = time.perf_counter()
    with TestClient(create_app(settings)) as fresh_client:
        response = fresh_client.get("/health")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 1.0


def test_health_returns_503_when_database_is_unreachable() -> None:
    broken = Settings(_env_file=None, database_url="sqlite:////nonexistent-wealthwise-dir/never.db")
    with TestClient(create_app(broken)) as broken_client:
        response = broken_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "db": "unreachable"}


def test_health_needs_no_authentication(client: TestClient) -> None:
    response = client.get("/health", headers={})

    assert response.status_code == 200
