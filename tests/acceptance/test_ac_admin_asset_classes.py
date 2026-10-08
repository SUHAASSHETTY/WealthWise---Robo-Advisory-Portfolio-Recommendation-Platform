"""AC-10 — Admin asset classes management acceptance tests (admin_versioning_spec §2.5, §4)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.clock import AnchoredClock
from app.core.config import Settings

ADMIN = {"Authorization": "Bearer stub-token-erin"}
ALICE = {"Authorization": "Bearer stub-token-alice"}
DAN = {"Authorization": "Bearer stub-token-dan"}
BASE = "/api/v1/admin/asset-classes"


@pytest.fixture
def api(settings: Settings) -> Iterator[TestClient]:
    from app.main import create_app

    clock = AnchoredClock(datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC))
    with TestClient(create_app(settings, clock=clock)) as test_client:
        yield test_client


@pytest.mark.ac("AC-10")
def test_admin_list_asset_classes(api: TestClient) -> None:
    """Admin can list all seeded asset classes in display order."""
    res = api.get(BASE, headers=ADMIN)
    assert res.status_code == 200
    classes = res.json()
    assert len(classes) == 4
    codes = [c["code"] for c in classes]
    assert codes == ["EQUITY", "DEBT", "GOLD", "CASH"]
    assert all(c["is_active"] is True for c in classes)


@pytest.mark.ac("AC-10")
def test_admin_create_asset_class(api: TestClient) -> None:
    """Admin can create a new asset class; duplicate code returns 409 ASSET_CLASS_EXISTS."""
    payload = {"code": "CRYPTO", "name": "Crypto Assets", "display_order": 5}
    res = api.post(BASE, headers=ADMIN, json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["code"] == "CRYPTO"
    assert body["name"] == "Crypto Assets"
    assert body["display_order"] == 5
    assert body["is_active"] is True

    # Duplicate code
    dup = api.post(BASE, headers=ADMIN, json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "ASSET_CLASS_EXISTS"


@pytest.mark.ac("AC-10")
def test_admin_patch_asset_class_rename_and_order(api: TestClient) -> None:
    """Admin can patch name and display order of an asset class."""
    res = api.patch(f"{BASE}/GOLD", headers=ADMIN, json={"name": "Precious Metals & Gold", "display_order": 10})
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == "GOLD"
    assert body["name"] == "Precious Metals & Gold"
    assert body["display_order"] == 10


@pytest.mark.ac("AC-10")
def test_deactivating_in_use_asset_class_returns_409(api: TestClient) -> None:
    """AC-10.9 / §2.5 — Deactivating a class referenced by the active template version
    returns 409 ASSET_CLASS_IN_USE.
    """
    res = api.patch(f"{BASE}/EQUITY", headers=ADMIN, json={"is_active": False})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ASSET_CLASS_IN_USE"

    # Verify equity is still active
    classes = api.get(BASE, headers=ADMIN).json()
    equity = next(c for c in classes if c["code"] == "EQUITY")
    assert equity["is_active"] is True


@pytest.mark.ac("AC-10")
def test_asset_class_routes_reject_non_admin(api: TestClient) -> None:
    """AC-10.8 — Customer and advisor cannot access admin asset class endpoints."""
    for token in (ALICE, DAN):
        assert api.get(BASE, headers=token).status_code == 403
        assert api.post(BASE, headers=token, json={"code": "TEST", "name": "Test"}).status_code == 403
        assert api.patch(f"{BASE}/GOLD", headers=token, json={"is_active": False}).status_code == 403
