"""Customer rebalancing decisions (rebalancing_spec §3, AC-07, NFR-02)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.repositories.base import Base
from app.repositories.guards import protect_append_only
from app.repositories.models._columns import new_uuid, utcnow


class RebalancingDecision(Base):
    __tablename__ = "rebalancing_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rebalancing_recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("rebalancing_recommendations.id"), unique=True, nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # ACCEPTED | DISMISSED | EXPIRED
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(16), nullable=False)  # CUSTOMER | SYSTEM
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    recommendation: Mapped["RebalancingRecommendation"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "RebalancingRecommendation", back_populates="decision"
    )


protect_append_only(RebalancingDecision)
