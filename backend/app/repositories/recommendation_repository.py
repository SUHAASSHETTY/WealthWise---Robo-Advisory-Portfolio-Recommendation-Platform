"""recommendations + recommendation_allocations data access (recommendation_spec §3). Append-only: add and list only,
no update or delete (NFR-02). Reads return the STORED rows with the pinned template version number.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.bands import RiskBand
from app.domain.policy import RecommendationSource
from app.repositories.models import AssetClass, Recommendation, RecommendationAllocation, TemplateVersion


@dataclass(frozen=True)
class RecommendationRecord:
    """A stored recommendation, its template version number and allocation rows in asset-class display order."""

    id: str
    source: RecommendationSource
    risk_band: RiskBand
    template_version_id: str
    template_version_no: int
    goal_id: str | None
    horizon_months: int | None
    horizon_rule: str
    as_of_date: date
    created_at: datetime
    allocation: tuple[tuple[str, Decimal], ...]


def _utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; every stored timestamp is UTC (app_spec §5.2)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def add(
    session: Session,
    *,
    customer_id: str,
    source: RecommendationSource,
    risk_band: RiskBand,
    risk_band_source_id: str,
    template_version_id: str,
    goal_id: str | None,
    horizon_months: int | None,
    horizon_rule: str,
    as_of_date: date,
    created_by: str,
    created_at: datetime,
    allocation: Sequence[tuple[str, Decimal]],
) -> Recommendation:
    """Insert one recommendation and its allocation rows in the caller's transaction (flushed for the id)."""
    row = Recommendation(
        customer_id=customer_id,
        source=source,
        risk_band=risk_band,
        risk_band_source_id=risk_band_source_id,
        template_version_id=template_version_id,
        goal_id=goal_id,
        horizon_months=horizon_months,
        horizon_rule=horizon_rule,
        as_of_date=as_of_date,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    session.add_all(
        RecommendationAllocation(recommendation_id=row.id, asset_class_code=code, target_pct=pct)
        for code, pct in allocation
    )
    session.flush()
    return row


def _allocations(session: Session, ids: Sequence[str]) -> dict[str, list[tuple[str, Decimal]]]:
    stmt = (
        select(RecommendationAllocation.recommendation_id, RecommendationAllocation.asset_class_code)
        .add_columns(RecommendationAllocation.target_pct)
        .join(AssetClass, AssetClass.code == RecommendationAllocation.asset_class_code)
        .where(RecommendationAllocation.recommendation_id.in_(ids))
        .order_by(AssetClass.display_order)
    )
    rows: dict[str, list[tuple[str, Decimal]]] = {rec_id: [] for rec_id in ids}
    for rec_id, code, pct in session.execute(stmt):
        rows[rec_id].append((code, pct))
    return rows


def list_for_customer(session: Session, customer_id: str, limit: int | None = None) -> list[RecommendationRecord]:
    """The customer's recommendations, newest first by (created_at, id)."""
    stmt = (
        select(Recommendation, TemplateVersion.version_no)
        .join(TemplateVersion, TemplateVersion.id == Recommendation.template_version_id)
        .where(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .limit(limit)
    )
    found = list(session.execute(stmt).tuples())
    allocations = _allocations(session, [rec.id for rec, _ in found])
    return [
        RecommendationRecord(
            id=rec.id,
            source=rec.source,
            risk_band=rec.risk_band,
            template_version_id=rec.template_version_id,
            template_version_no=version_no,
            goal_id=rec.goal_id,
            horizon_months=rec.horizon_months,
            horizon_rule=rec.horizon_rule,
            as_of_date=rec.as_of_date,
            created_at=_utc(rec.created_at),
            allocation=tuple(allocations[rec.id]),
        )
        for rec, version_no in found
    ]


def latest_for_customer(session: Session, customer_id: str) -> RecommendationRecord | None:
    newest = list_for_customer(session, customer_id, limit=1)
    return newest[0] if newest else None
