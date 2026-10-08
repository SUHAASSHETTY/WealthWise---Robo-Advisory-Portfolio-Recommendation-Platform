"""Sprint 1 synthetic seed: asset classes, v1 risk policy, v1 templates, users, 5 customers, goals.

Data migration (NFR-05, append-only): reads the immutable seed files under app/seed/ (v1 policies are PUBLISHED and
protected by the template-immutability hook) and inserts rows through lightweight table definitions — it never
imports application code, so later model changes cannot alter what this revision does.

Revision ID: 0002
Revises: 0001
"""

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DIR = Path(__file__).resolve().parents[2] / "app" / "seed"
SEEDED_AT = datetime(2025, 11, 1, 9, 0, tzinfo=UTC)


def _load(relative: str) -> Any:
    return json.loads((SEED_DIR / relative).read_text(encoding="utf-8"))


def _tables() -> dict[str, sa.TableClause]:
    s, b, i, d, dt = sa.String, sa.Boolean, sa.Integer, sa.Date, sa.DateTime
    col = sa.column
    return {
        "asset_classes": sa.table(
            "asset_classes",
            col("code", s),
            col("name", s),
            col("is_active", b),
            col("display_order", i),
            col("created_at", dt),
        ),
        "users": sa.table("users", col("id", s), col("username", s), col("role", s), col("created_at", dt)),
        "customers": sa.table(
            "customers",
            col("id", s),
            col("user_id", s),
            col("display_name", s),
            col("kyc_verified", b),
            col("created_at", dt),
        ),
        "goals": sa.table(
            "goals",
            col("id", s),
            col("customer_id", s),
            col("name", s),
            col("goal_type", s),
            col("target_amount", s),
            col("target_date", d),
            col("priority", i),
            col("funding_share_pct", s),
            col("created_at", dt),
            col("updated_at", dt),
        ),
    }


def _policy_table(name: str) -> sa.TableClause:
    c = sa.column
    return sa.table(
        name,
        c("id", sa.String),
        c("version_no", sa.Integer),
        c("status", sa.String),
        c("definition", sa.JSON),
        c("created_at", sa.DateTime),
        c("published_at", sa.DateTime),
    )


def _policy_row(policy_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": policy_id,
        "version_no": seed["version_no"],
        "status": seed["status"],
        "definition": seed["definition"],
        "created_at": SEEDED_AT,
        "published_at": SEEDED_AT,
    }


def upgrade() -> None:
    ref = _load("reference_data.json")
    t = _tables()
    ids = ref["policy_version_ids"]
    op.bulk_insert(
        t["asset_classes"], [{**a, "is_active": True, "created_at": SEEDED_AT} for a in ref["asset_classes"]]
    )
    op.bulk_insert(
        _policy_table("risk_policy_versions"),
        [_policy_row(ids["risk_policy_v1"], _load("policies/risk_policy_v1.json"))],
    )
    op.bulk_insert(
        _policy_table("template_versions"), [_policy_row(ids["template_v1"], _load("policies/template_v1.json"))]
    )
    op.bulk_insert(t["users"], [{**u, "created_at": SEEDED_AT} for u in ref["users"]])
    op.bulk_insert(t["customers"], [{**c, "created_at": SEEDED_AT} for c in ref["customers"]])
    op.bulk_insert(
        t["goals"],
        [
            {
                **g,
                "target_date": date.fromisoformat(g["target_date"]),
                "created_at": datetime.fromisoformat(g["created_at"]),
                "updated_at": datetime.fromisoformat(g["created_at"]),
            }
            for g in ref["goals"]
        ],
    )


def downgrade() -> None:
    for table in ("goals", "customers", "users", "template_versions", "risk_policy_versions", "asset_classes"):
        op.execute(sa.text(f"DELETE FROM {table}"))
