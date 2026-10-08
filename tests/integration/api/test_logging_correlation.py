"""NFR-06 — structured JSON logs with request correlation IDs; NFR-03 — allow-listed log keys only."""

from __future__ import annotations

import json
import logging
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.logging import ALLOWED_LOG_KEYS, configure_logging


def _json_lines(text: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def test_response_echoes_incoming_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "req-abc-123"})

    assert response.headers["X-Request-ID"] == "req-abc-123"


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health")

    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4


def test_unsafe_incoming_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "bad id with spaces\nand newline"})

    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4


def test_request_log_line_is_json_with_correlation_id(capsys: pytest.CaptureFixture[str], client: TestClient) -> None:
    client.get("/health", headers={"X-Request-ID": "req-log-1"})

    records = [r for r in _json_lines(capsys.readouterr().out) if r.get("message") == "request completed"]
    assert len(records) == 1
    record = records[0]
    assert record["correlation_id"] == "req-log-1"
    assert record["path_template"] == "/health"
    assert record["status_code"] == 200
    assert {"ts", "level", "logger", "message"} <= record.keys()
    assert set(record) - {"ts", "level", "logger", "message", "correlation_id"} <= ALLOWED_LOG_KEYS


def test_formatter_drops_keys_that_are_not_allow_listed(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    logging.getLogger("wealthwise.test").info(
        "customer signed in", extra={"customer_id": "c-001", "email": "alice@example.com"}
    )

    output = capsys.readouterr().out
    record = _json_lines(output)[-1]
    assert record["customer_id"] == "c-001"
    assert "email" not in record
    assert "alice@example.com" not in output


def test_request_log_uses_full_versioned_route_template(capsys: pytest.CaptureFixture[str], client: TestClient) -> None:
    """Found by the live smoke test: prefixed routes were logged without /api/v1."""
    client.get("/api/v1/auth/whoami", headers={"Authorization": "Bearer stub-token-dan", "X-Request-ID": "req-tpl"})

    records = [r for r in _json_lines(capsys.readouterr().out) if r.get("correlation_id") == "req-tpl"]
    assert [r["path_template"] for r in records if r.get("message") == "request completed"] == ["/api/v1/auth/whoami"]
