"""Sprint 3 schema: risk_band_overrides, rebalancing_recommendations, rebalancing_lines, rebalancing_decisions, stub_orders.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DAN_ADVISOR_USER_ID = "00000000-0000-4000-8000-00000000a101"
ALICE_CUSTOMER_ID = "00000000-0000-4000-8000-00000000c001"
BOB_CUSTOMER_ID = "00000000-0000-4000-8000-00000000c002"
CAROL_CUSTOMER_ID = "00000000-0000-4000-8000-00000000c003"


def upgrade() -> None:
    # 1. Create risk_band_overrides
    op.create_table(
        "risk_band_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("previous_band", sa.String(length=16), nullable=False),
        sa.Column("new_band", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("actor_role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("risk_band_overrides", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_risk_band_overrides_customer_id"), ["customer_id"], unique=False)

    # 2. Create rebalancing_recommendations
    op.create_table(
        "rebalancing_recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("based_on_recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("template_version_id", sa.String(length=36), nullable=False),
        sa.Column("nav_date", sa.Date(), nullable=False),
        sa.Column("total_value", sa.String(length=40), nullable=False),
        sa.Column("drift_threshold_pct", sa.String(length=40), nullable=False),
        sa.Column("post_trade_cash", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["based_on_recommendation_id"], ["recommendations.id"]),
        sa.ForeignKeyConstraint(["template_version_id"], ["template_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rebalancing_recommendations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_rebalancing_recommendations_customer_id"), ["customer_id"], unique=False
        )

    # 3. Create rebalancing_lines
    op.create_table(
        "rebalancing_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rebalancing_recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("asset_class_code", sa.String(length=20), nullable=False),
        sa.Column("current_value", sa.String(length=40), nullable=False),
        sa.Column("current_pct", sa.String(length=40), nullable=True),
        sa.Column("target_pct", sa.String(length=40), nullable=True),
        sa.Column("drift_pct", sa.String(length=40), nullable=True),
        sa.Column("target_value", sa.String(length=40), nullable=True),
        sa.Column("nav", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.String(length=40), nullable=True),
        sa.Column("trade_value", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["asset_class_code"], ["asset_classes.code"]),
        sa.ForeignKeyConstraint(["rebalancing_recommendation_id"], ["rebalancing_recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rebalancing_lines", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_rebalancing_lines_rebalancing_recommendation_id"),
            ["rebalancing_recommendation_id"],
            unique=False,
        )

    # 4. Create rebalancing_decisions
    op.create_table(
        "rebalancing_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rebalancing_recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rebalancing_recommendation_id"], ["rebalancing_recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rebalancing_recommendation_id", name="uq_rebalancing_decisions_recommendation"),
    )

    # 5. Create stub_orders
    op.create_table(
        "stub_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rebalancing_recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("asset_class_code", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.String(length=40), nullable=False),
        sa.Column("nav", sa.String(length=40), nullable=False),
        sa.Column("trade_value", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_class_code"], ["asset_classes.code"]),
        sa.ForeignKeyConstraint(["rebalancing_recommendation_id"], ["rebalancing_recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("stub_orders", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_stub_orders_rebalancing_recommendation_id"),
            ["rebalancing_recommendation_id"],
            unique=False,
        )

    # 6. Assign dan.advisor to Alice, Bob, Carol
    customers = sa.table(
        "customers",
        sa.column("id", sa.String),
        sa.column("advisor_user_id", sa.String),
    )
    op.execute(
        customers.update()
        .where(customers.c.id.in_([ALICE_CUSTOMER_ID, BOB_CUSTOMER_ID, CAROL_CUSTOMER_ID]))
        .values(advisor_user_id=DAN_ADVISOR_USER_ID)
    )


def downgrade() -> None:
    op.drop_table("stub_orders")
    op.drop_table("rebalancing_decisions")
    op.drop_table("rebalancing_lines")
    op.drop_table("rebalancing_recommendations")
    op.drop_table("risk_band_overrides")
