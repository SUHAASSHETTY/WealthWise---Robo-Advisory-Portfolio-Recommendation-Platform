"""Holdings and drift service layer (holdings_spec §4, AC-05)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.drift_policy import HoldingInput, HoldingLine, compute_drift, value_holdings
from app.domain.policy import PolicyStatus
from app.repositories import holding_repository, nav_repository, recommendation_repository
from app.repositories.customer_repository import active_asset_class_codes
from app.repositories.models.template_version import TemplateVersion
from app.services.errors import ServiceError


@dataclass(frozen=True)
class HoldingsView:
    """Full holdings and drift view returned to customer."""

    nav_date: date
    total_value: Decimal
    has_target: bool
    recommendation_id: str | None
    template_version_no: int | None
    drift_threshold_pct: Decimal | None
    portfolio_breached: bool
    lines: Sequence[HoldingLine]


def get_holdings(session: Session, customer_id: str) -> HoldingsView:
    """Fetch customer holdings, value against latest NAVs, and calculate drift."""
    nav_date, nav_map = nav_repository.get_latest_navs(session)
    if nav_date is None or not nav_map:
        raise ServiceError(409, "NAV_NOT_LOADED", "No NAV prices have been loaded.")

    active_classes = active_asset_class_codes(session)
    customer_holdings = {
        h.asset_class_code: h.units for h in holding_repository.list_for_customer(session, customer_id)
    }

    inputs = [
        HoldingInput(asset_class=code, units=customer_holdings.get(code, Decimal("0.0000"))) for code in active_classes
    ]

    latest_rec = recommendation_repository.latest_for_customer(session, customer_id)
    if latest_rec is not None:
        target_map: dict[str, Decimal] | None = {code: pct for code, pct in latest_rec.allocation}
        tpl_version = session.scalar(
            select(TemplateVersion).where(
                TemplateVersion.version_no == latest_rec.template_version_no,
                TemplateVersion.status == PolicyStatus.PUBLISHED,
            )
        )
        if tpl_version is not None and "drift_threshold_pct" in tpl_version.definition:
            threshold: Decimal | None = Decimal(str(tpl_version.definition["drift_threshold_pct"]))
        else:
            threshold = Decimal("5.00")
        tpl_ver_no: int | None = latest_rec.template_version_no
        rec_id: str | None = latest_rec.id
    else:
        target_map = None
        threshold = None
        rec_id = None
        tpl_ver_no = None

    valued = value_holdings(inputs, nav_map)
    report = compute_drift(valued, target=target_map, threshold=threshold)

    return HoldingsView(
        nav_date=nav_date,
        total_value=report.total_value,
        has_target=report.has_target,
        recommendation_id=rec_id,
        template_version_no=tpl_ver_no,
        drift_threshold_pct=report.drift_threshold_pct,
        portfolio_breached=report.portfolio_breached,
        lines=report.lines,
    )
