"""NFR-04 — authentication boundary at the API layer; customer / advisor / admin roles are separated."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.deps import require_role
from app.core.config import Settings
from app.core.security import Principal, Role
from app.main import create_app

TOKENS = {
    Role.CUSTOMER: "stub-token-alice",
    Role.ADVISOR: "stub-token-dan",
    Role.ADMIN: "stub-token-erin",
}


def _probe_endpoint(role: Role) -> Callable[..., dict[str, str]]:
    # Bind the dependency eagerly: with postponed annotations FastAPI cannot see a loop variable.
    dependency = require_role(role)

    def endpoint(principal: Principal = Depends(dependency)) -> dict[str, str]:  # noqa: B008
        return {"role": principal.role.value}

    return endpoint


def _probe_router() -> APIRouter:
    router = APIRouter(prefix="/probe")
    for role in Role:
        router.add_api_route(f"/{role.value.lower()}", _probe_endpoint(role), methods=["GET"])
    return router


@pytest.fixture
def probe_client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.include_router(_probe_router())
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_token_is_401_with_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/auth/whoami")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_unknown_token_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/whoami", headers=_bearer("not-a-real-token"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_stub_token_resolves_to_user_and_role(client: TestClient) -> None:
    response = client.get("/api/v1/auth/whoami", headers=_bearer("stub-token-alice"))

    assert response.status_code == 200
    assert response.json() == {"username": "alice.customer", "role": "CUSTOMER"}


@pytest.mark.parametrize("caller", list(Role))
@pytest.mark.parametrize("route_role", list(Role))
def test_role_separation_matrix(probe_client: TestClient, caller: Role, route_role: Role) -> None:
    response = probe_client.get(f"/probe/{route_role.value.lower()}", headers=_bearer(TOKENS[caller]))

    if caller == route_role:
        assert response.status_code == 200
        assert response.json() == {"role": caller.value}
    else:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_stub_tokens_rejected_when_stub_auth_disabled(settings: Settings) -> None:
    disabled = settings.model_copy(update={"stub_auth_enabled": False})
    with TestClient(create_app(disabled)) as test_client:
        response = test_client.get("/api/v1/auth/whoami", headers=_bearer("stub-token-alice"))

    assert response.status_code == 401


def test_stub_auth_is_off_by_default() -> None:
    """Security review W1: public stub tokens must never be accepted unless explicitly enabled."""
    assert Settings(_env_file=None).stub_auth_enabled is False
