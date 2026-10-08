"""E1-S1 / E1-S3 — `alembic upgrade head` builds the schema and the synthetic v1 seed (app_spec §5.9-5.10)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from tests.fixtures.policy_definitions import TEMPLATE_V1, V1_BANDS

EXPECTED_TABLES = {
    "alembic_version",
    "asset_classes",
    "users",
    "customers",
    "goals",
    "risk_policy_versions",
    "template_versions",
    "risk_assessments",
    "recommendations",
    "recommendation_allocations",
    "audit_events",
    "holdings",
    "nav_prices",
    "goal_progress_snapshots",
    "risk_band_overrides",
    "rebalancing_recommendations",
    "rebalancing_lines",
    "rebalancing_decisions",
    "stub_orders",
}


def test_upgrade_head_creates_every_sprint_1_table(migrated_db_path: Path) -> None:
    engine = create_engine(f"sqlite:///{migrated_db_path}")
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


@pytest.mark.ac("AC-10")
def test_ac_10_seed_has_exactly_one_published_v1_of_each_policy(migrated_db_path: Path) -> None:
    """AC-10.1 — v1 risk policy and v1 template are seeded PUBLISHED with fixed ids and spec content."""
    import json

    engine = create_engine(f"sqlite:///{migrated_db_path}")
    with engine.connect() as conn:
        rp = conn.execute(text("SELECT id, version_no, status, definition FROM risk_policy_versions")).all()
        tv = conn.execute(text("SELECT id, version_no, status, definition FROM template_versions")).all()

    assert [(r.id, r.version_no, r.status) for r in rp] == [("00000000-0000-4000-8000-000000000201", 1, "PUBLISHED")]
    assert [(r.id, r.version_no, r.status) for r in tv] == [("00000000-0000-4000-8000-000000000101", 1, "PUBLISHED")]
    assert json.loads(rp[0].definition)["bands"] == V1_BANDS
    assert json.loads(tv[0].definition) == TEMPLATE_V1


def test_seed_reference_data(migrated_db_path: Path) -> None:
    engine = create_engine(f"sqlite:///{migrated_db_path}")
    with engine.connect() as conn:
        classes = conn.execute(text("SELECT code, display_order, is_active FROM asset_classes ORDER BY display_order"))
        users = dict(conn.execute(text("SELECT username, role FROM users")).all())
        kyc = dict(
            conn.execute(
                text("SELECT u.username, c.kyc_verified FROM customers c JOIN users u ON u.id = c.user_id")
            ).all()
        )
        goals = conn.execute(text("SELECT id, target_date, priority, target_amount FROM goals ORDER BY id")).all()
        empty = {
            t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
            for t in ("risk_assessments", "recommendations", "audit_events")
        }

    assert [(c.code, c.display_order, bool(c.is_active)) for c in classes] == [
        ("EQUITY", 1, True),
        ("DEBT", 2, True),
        ("GOLD", 3, True),
        ("CASH", 4, True),
    ]
    assert users == {
        "alice.customer": "CUSTOMER",
        "bob.customer": "CUSTOMER",
        "carol.customer": "CUSTOMER",
        "frank.customer": "CUSTOMER",
        "grace.customer": "CUSTOMER",
        "dan.advisor": "ADVISOR",
        "erin.admin": "ADMIN",
    }
    assert {u: bool(v) for u, v in kyc.items()} == {
        "alice.customer": True,
        "bob.customer": True,
        "carol.customer": False,
        "frank.customer": True,
        "grace.customer": True,
    }
    assert [(g.id[-6:], g.target_date, g.priority) for g in goals] == [
        ("0a0001", "2040-01-01", 2),
        ("0b0001", "2028-06-30", 1),
        ("0f0001", "2030-01-15", 1),
    ]
    assert all(isinstance(Decimal(g.target_amount), Decimal) for g in goals)  # stored as decimal TEXT
    assert empty == {"risk_assessments": 0, "recommendations": 0, "audit_events": 0}
