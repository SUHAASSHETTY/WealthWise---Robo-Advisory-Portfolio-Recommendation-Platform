"""AC-02 / NFR-08: every published template band and every stored recommendation sums to exactly Decimal("100.00").

Scans every seeded template file under backend/app/seed/policies/template_*.json (risk policies live alongside),
and every row of `recommendations` / `recommendation_allocations` after generating recommendations through the API.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from tests.fixtures.answer_sets import ANS_0, ANS_16, ANS_28, submission

from app.domain.allocation.templates import AllocationSumError, parse_template_set
from app.domain.policy import PolicyStatus

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
POLICY_DIR = BACKEND_DIR / "app" / "seed" / "policies"
EXACT_HUNDRED = Decimal("100.00")


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _published_template_files() -> list[Path]:
    return [p for p in sorted(POLICY_DIR.glob("template_*.json")) if _load(p).get("status") == PolicyStatus.PUBLISHED]


PUBLISHED_FILES = _published_template_files()


@pytest.mark.ac("AC-02")
def test_ac_02_at_least_one_published_template_is_seeded() -> None:
    """AC-02.3: the invariant scan is meaningful only if a PUBLISHED template exists."""
    assert PUBLISHED_FILES, f"no PUBLISHED template versions under {POLICY_DIR}"


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize("path", PUBLISHED_FILES, ids=lambda p: p.name)
def test_ac_02_every_published_band_sums_to_exactly_100(path: Path) -> None:
    """AC-02.3: each band of each PUBLISHED template parses and totals exactly Decimal('100.00')."""
    templates = _load(path)["definition"]["templates"]
    parsed = parse_template_set(templates)
    assert parsed, f"{path.name} defines no bands"
    for band, allocation in parsed.items():
        total = sum(allocation.values(), Decimal("0"))
        assert total == EXACT_HUNDRED, f"{path.name} {band} sums to {total}"
        assert all(isinstance(v, Decimal) for v in allocation.values())


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize("path", PUBLISHED_FILES, ids=lambda p: p.name)
def test_ac_02_every_band_has_the_same_asset_classes(path: Path) -> None:
    """AC-02.2: all bands in one template allocate across the identical asset-class set."""
    templates: dict[str, dict[str, str]] = _load(path)["definition"]["templates"]
    asset_sets = {band: frozenset(row) for band, row in templates.items()}
    expected = next(iter(asset_sets.values()))
    mismatched = {band: sorted(s) for band, s in asset_sets.items() if s != expected}
    assert not mismatched, f"{path.name}: expected {sorted(expected)}, got {mismatched}"


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize(
    "bad_row",
    [
        {"EQUITY": "50.00", "DEBT": "34.99", "GOLD": "10.00", "CASH": "5.00"},  # 99.99
        {"EQUITY": "75.00", "DEBT": "15.00", "GOLD": "7.50", "CASH": "2.51"},  # 100.01
        {"EQUITY": "50.001", "DEBT": "34.999", "GOLD": "10.00", "CASH": "5.00"},  # 3 dp
    ],
)
def test_ac_02_corrupted_template_is_rejected(bad_row: dict[str, str]) -> None:
    """AC-02.4 (red proof): a band that is not exactly 100.00 raises AllocationSumError."""
    with pytest.raises(AllocationSumError):
        parse_template_set({"MODERATE": bad_row})


@pytest.mark.ac("AC-02")
def test_ac_02_every_stored_recommendation_sums_to_exactly_100(client: TestClient) -> None:
    """AC-02.3 (NFR-08): after recommendations for every band, with and without goals, each STORED recommendation
    has exactly one row per active asset class, no negative target_pct, and rows summing to Decimal('100.00')."""
    from sqlalchemy import select

    from app.repositories import customer_repository
    from app.repositories.models import Recommendation, RecommendationAllocation

    rp1 = "00000000-0000-4000-8000-000000000201"
    for user, answers, body in [
        ("alice", ANS_16, {}),
        ("bob", ANS_0, {}),
        ("frank", ANS_28, {"goal_id": "00000000-0000-4000-8000-0000000f0001"}),
        ("grace", ANS_0, {}),
        ("grace", ANS_28, {"goal_id": "00000000-0000-4000-8000-0000000a0001"}),
    ]:
        headers = {"Authorization": f"Bearer stub-token-{user}"}
        sub = submission(rp1, answers)
        assert client.post("/api/v1/risk-profile/assessments", headers=headers, json=sub).is_success
        assert client.post("/api/v1/recommendations", headers=headers, json=body).status_code == 201

    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        active = sorted(customer_repository.active_asset_class_codes(session))
        rec_ids = list(session.scalars(select(Recommendation.id)))
        assert len(rec_ids) == 5
        for rec_id in rec_ids:
            rows = session.scalars(
                select(RecommendationAllocation).where(RecommendationAllocation.recommendation_id == rec_id)
            ).all()
            assert sorted(r.asset_class_code for r in rows) == active, rec_id
            assert all(isinstance(r.target_pct, Decimal) and r.target_pct >= Decimal("0.00") for r in rows), rec_id
            assert sum((r.target_pct for r in rows), Decimal("0")) == EXACT_HUNDRED, rec_id
