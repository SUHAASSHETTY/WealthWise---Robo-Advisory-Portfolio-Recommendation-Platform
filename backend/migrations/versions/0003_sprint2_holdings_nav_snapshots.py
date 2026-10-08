"""Sprint 2 schema and seed: holdings, nav_prices, goal_progress_snapshots.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_AT = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
NAV_DATE_2026_01_15 = date(2026, 1, 15)


def upgrade() -> None:
    # 1. Create tables
    op.create_table(
        "holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("asset_class_code", sa.String(length=20), nullable=False),
        sa.Column("units", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_class_code"], ["asset_classes.code"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "asset_class_code", name="uq_holdings_customer_asset_class"),
    )
    with op.batch_alter_table("holdings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_holdings_customer_id"), ["customer_id"], unique=False)

    op.create_table(
        "nav_prices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_class_code", sa.String(length=20), nullable=False),
        sa.Column("nav_date", sa.Date(), nullable=False),
        sa.Column("nav", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_class_code"], ["asset_classes.code"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_class_code", "nav_date", name="uq_nav_prices_asset_date"),
    )

    op.create_table(
        "goal_progress_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("nav_date", sa.Date(), nullable=False),
        sa.Column("total_value", sa.String(length=40), nullable=False),
        sa.Column("funding_share_pct", sa.String(length=40), nullable=False),
        sa.Column("current_goal_value", sa.String(length=40), nullable=False),
        sa.Column("percent_complete", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("goal_progress_snapshots", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_goal_progress_snapshots_goal_id"), ["goal_id"], unique=False)

    # 2. Seed initial NAV prices for 2026-01-15
    nav_table = sa.table(
        "nav_prices",
        sa.column("id", sa.String),
        sa.column("asset_class_code", sa.String),
        sa.column("nav_date", sa.Date),
        sa.column("nav", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        nav_table,
        [
            {
                "id": str(uuid.uuid4()),
                "asset_class_code": "EQUITY",
                "nav_date": NAV_DATE_2026_01_15,
                "nav": "150.0000",
                "created_at": SEEDED_AT,
            },
            {
                "id": str(uuid.uuid4()),
                "asset_class_code": "DEBT",
                "nav_date": NAV_DATE_2026_01_15,
                "nav": "25.0000",
                "created_at": SEEDED_AT,
            },
            {
                "id": str(uuid.uuid4()),
                "asset_class_code": "GOLD",
                "nav_date": NAV_DATE_2026_01_15,
                "nav": "60.0000",
                "created_at": SEEDED_AT,
            },
            {
                "id": str(uuid.uuid4()),
                "asset_class_code": "CASH",
                "nav_date": NAV_DATE_2026_01_15,
                "nav": "1.0000",
                "created_at": SEEDED_AT,
            },
        ],
    )

    # 3. Seed initial holdings for synthetic customers
    holdings_table = sa.table(
        "holdings",
        sa.column("id", sa.String),
        sa.column("customer_id", sa.String),
        sa.column("asset_class_code", sa.String),
        sa.column("units", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    c_alice = "00000000-0000-4000-8000-00000000c001"
    c_bob = "00000000-0000-4000-8000-00000000c002"
    c_carol = "00000000-0000-4000-8000-00000000c003"
    c_frank = "00000000-0000-4000-8000-00000000c004"
    c_grace = "00000000-0000-4000-8000-00000000c005"

    seed_holdings = [
        # Alice: 400 equity, 1000 debt, 150 gold, 6000 cash (exact AC-05.1 example)
        {"id": str(uuid.uuid4()), "customer_id": c_alice, "asset_class_code": "EQUITY", "units": "400.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_alice, "asset_class_code": "DEBT", "units": "1000.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_alice, "asset_class_code": "GOLD", "units": "150.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_alice, "asset_class_code": "CASH", "units": "6000.0000", "updated_at": SEEDED_AT},
        # Bob
        {"id": str(uuid.uuid4()), "customer_id": c_bob, "asset_class_code": "EQUITY", "units": "100.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_bob, "asset_class_code": "DEBT", "units": "500.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_bob, "asset_class_code": "GOLD", "units": "50.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_bob, "asset_class_code": "CASH", "units": "2000.0000", "updated_at": SEEDED_AT},
        # Carol
        {"id": str(uuid.uuid4()), "customer_id": c_carol, "asset_class_code": "EQUITY", "units": "200.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_carol, "asset_class_code": "DEBT", "units": "400.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_carol, "asset_class_code": "GOLD", "units": "50.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_carol, "asset_class_code": "CASH", "units": "1000.0000", "updated_at": SEEDED_AT},
        # Frank
        {"id": str(uuid.uuid4()), "customer_id": c_frank, "asset_class_code": "EQUITY", "units": "500.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_frank, "asset_class_code": "DEBT", "units": "800.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_frank, "asset_class_code": "GOLD", "units": "100.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_frank, "asset_class_code": "CASH", "units": "5000.0000", "updated_at": SEEDED_AT},
        # Grace
        {"id": str(uuid.uuid4()), "customer_id": c_grace, "asset_class_code": "EQUITY", "units": "600.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_grace, "asset_class_code": "DEBT", "units": "1200.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_grace, "asset_class_code": "GOLD", "units": "200.0000", "updated_at": SEEDED_AT},
        {"id": str(uuid.uuid4()), "customer_id": c_grace, "asset_class_code": "CASH", "units": "8000.0000", "updated_at": SEEDED_AT},
    ]
    op.bulk_insert(holdings_table, seed_holdings)


def downgrade() -> None:
    op.drop_table("goal_progress_snapshots")
    op.drop_table("nav_prices")
    op.drop_table("holdings")
