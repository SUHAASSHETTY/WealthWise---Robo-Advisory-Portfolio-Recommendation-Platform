"""Advisor workbench service: assigned portfolio view, risk overrides,
manual recommendations, audit (advisor_workbench_spec §2-4, AC-09).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.security import Principal
from app.domain.advisor_override_rules import (
    AdvisorRuleValidationError,
    validate_manual_recommendation,
    validate_risk_override,
)
from app.domain.policy import RecommendationSource
from app.repositories import (
    asset_class_repository,
    audit_repository,
    customer_repository,
    policy_version_repository,
    rebalancing_repository,
    recommendation_repository,
    risk_assessment_repository,
    risk_override_repository,
)
from app.repositories.models.audit_event import AuditEvent
from app.repositories.models.risk_band_override import RiskBandOverride
from app.repositories.models.template_version import TemplateVersion
from app.services import goals_service, holdings_service, rebalancing_service, risk_profile_service
from app.services.errors import conflict, not_found, unprocessable
from app.services.holdings_service import HoldingsView
from app.services.rebalancing_service import RebalancingRecommendationView
from app.services.recommendation_service import RecommendationView

logger = logging.getLogger(__name__)

ACTION_OVERRIDDEN = "RISK_BAND_OVERRIDDEN"
ACTION_MANUAL_REC = "MANUAL_RECOMMENDATION_LOGGED"


@dataclass(frozen=True)
class AdvisorCustomerItemView:
    customer_id: str
    display_name: str
    effective_band: str | None
    band_source: str | None
    portfolio_breached: bool
    open_rebalance_id: str | None = None


@dataclass(frozen=True)
class CustomerDetailView:
    id: str
    display_name: str
    kyc_verified: bool


@dataclass(frozen=True)
class RiskProfileSummaryView:
    band: str | None
    source: str | None
    as_of: datetime | None


@dataclass(frozen=True)
class AdvisorCustomerPortfolioView:
    customer: CustomerDetailView
    risk_profile: RiskProfileSummaryView
    goals: Sequence[goals_service.GoalView]
    holdings: HoldingsView
    latest_recommendation: RecommendationView | None
    open_rebalance: RebalancingRecommendationView | None


@dataclass(frozen=True)
class RiskBandOverrideView:
    override_id: str
    previous_band: str
    new_band: str
    reason_code: str
    actor_user_id: str
    created_at: datetime


@dataclass(frozen=True)
class AuditEventItemView:
    occurred_at: datetime
    action: str
    actor_role: str
    actor_user_id: str | None
    entity_type: str
    entity_id: str
    details: dict[str, object]


def _check_assignment(session: Session, advisor_user_id: str, customer_id: str) -> None:
    cust = customer_repository.get_by_id(session, customer_id)
    if cust is None or cust.advisor_user_id != advisor_user_id:
        raise not_found("CUSTOMER_NOT_FOUND", "Customer not found.")


def list_assigned_customers(session: Session, advisor_user_id: str) -> list[AdvisorCustomerItemView]:
    """List all customers assigned to the advisor with portfolio status (AC-09)."""
    customers = customer_repository.list_assigned_customers_for_advisor(session, advisor_user_id)
    results: list[AdvisorCustomerItemView] = []

    for c in customers:
        eff = risk_profile_service.effective_band(session, c.id)
        holdings = holdings_service.get_holdings(session, c.id)
        open_rec = rebalancing_repository.get_open_for_customer(session, c.id)

        results.append(
            AdvisorCustomerItemView(
                customer_id=c.id,
                display_name=c.display_name,
                effective_band=eff.band.value if eff else None,
                band_source=eff.source if eff else None,
                portfolio_breached=holdings.portfolio_breached,
                open_rebalance_id=open_rec.id if open_rec else None,
            )
        )
    return results


def get_customer_portfolio(session: Session, advisor_user_id: str, customer_id: str) -> AdvisorCustomerPortfolioView:
    """Get assigned customer's full portfolio view (AC-09)."""
    _check_assignment(session, advisor_user_id, customer_id)
    cust = customer_repository.get_by_id(session, customer_id)
    assert cust is not None

    eff = risk_profile_service.effective_band(session, customer_id)
    goals = goals_service.list_goals(session, customer_id)
    holdings = holdings_service.get_holdings(session, customer_id)

    from app.services import recommendation_service

    latest_rec_view = recommendation_service.latest_for(session, customer_id)
    open_prop = rebalancing_repository.get_open_for_customer(session, customer_id)
    open_rebal_view = rebalancing_service._view_for(open_prop) if open_prop else None

    return AdvisorCustomerPortfolioView(
        customer=CustomerDetailView(id=cust.id, display_name=cust.display_name, kyc_verified=cust.kyc_verified),
        risk_profile=RiskProfileSummaryView(
            band=eff.band.value if eff else None,
            source=eff.source if eff else None,
            as_of=eff.as_of if eff else None,
        ),
        goals=goals,
        holdings=holdings,
        latest_recommendation=latest_rec_view,
        open_rebalance=open_rebal_view,
    )


def override_risk_band(
    session: Session,
    clock: Clock,
    principal: Principal,
    advisor_user_id: str,
    customer_id: str,
    new_band: str,
    reason_code: str,
    note: str,
) -> RiskBandOverrideView:
    """Submit risk band override, audit, and update customer effective band (AC-09.1-09.5)."""
    _check_assignment(session, advisor_user_id, customer_id)

    eff = risk_profile_service.effective_band(session, customer_id)
    if eff is None:
        raise conflict("RISK_PROFILE_REQUIRED", "Customer must complete a risk assessment before an override.")

    try:
        validate_risk_override(
            current_band=eff.band.value,
            new_band=new_band,
            reason_code=reason_code,
            note=note,
        )
    except AdvisorRuleValidationError as exc:
        raise unprocessable(exc.code, exc.message) from exc

    now = clock.now()
    override = RiskBandOverride(
        customer_id=customer_id,
        previous_band=eff.band.value,
        new_band=new_band,
        reason_code=reason_code,
        note=note.strip(),
        actor_user_id=advisor_user_id,
        actor_role="ADVISOR",
        created_at=now,
    )
    risk_override_repository.create(session, override)

    audit_repository.insert_audit_event(
        session,
        actor_user_id=advisor_user_id,
        actor_role=principal.role.value,
        action=ACTION_OVERRIDDEN,
        entity_type="risk_band_override",
        entity_id=override.id,
        details={"customer_id": customer_id, "reason_code": reason_code},
    )
    session.commit()

    logger.info(
        "risk band overridden",
        extra={
            "advisor_id": advisor_user_id,
            "customer_id": customer_id,
            "override_id": override.id,
            "reason_code": reason_code,
        },
    )

    return RiskBandOverrideView(
        override_id=override.id,
        previous_band=override.previous_band,
        new_band=override.new_band,
        reason_code=override.reason_code,
        actor_user_id=override.actor_user_id,
        created_at=override.created_at,
    )


@dataclass(frozen=True)
class ManualAllocationItem:
    asset_class: str
    target_pct: Decimal


def create_manual_recommendation(
    session: Session,
    clock: Clock,
    principal: Principal,
    advisor_user_id: str,
    customer_id: str,
    allocations: Sequence[ManualAllocationItem],
    note: str,
) -> RecommendationView:
    """Log advisor manual recommendation, becoming customer's target allocation (AC-09.8)."""
    _check_assignment(session, advisor_user_id, customer_id)

    eff = risk_profile_service.effective_band(session, customer_id)
    if eff is None:
        raise conflict("RISK_PROFILE_REQUIRED", "Customer must complete a risk assessment before a recommendation.")

    active_classes = asset_class_repository.list_active(session)
    active_codes = [ac.code for ac in active_classes]

    alloc_dicts = [{"asset_class": a.asset_class, "target_pct": a.target_pct} for a in allocations]
    try:
        validate_manual_recommendation(
            allocation=alloc_dicts,
            active_classes=active_codes,
            note=note,
        )
    except AdvisorRuleValidationError as exc:
        raise unprocessable(exc.code, exc.message) from exc

    active_template = policy_version_repository.active_published(session, TemplateVersion)
    if active_template is None:
        raise RuntimeError("No active published template version")

    now = clock.now()
    alloc_tuple = tuple((a.asset_class, a.target_pct) for a in allocations)
    rec = recommendation_repository.add(
        session,
        customer_id=customer_id,
        source=RecommendationSource.ADVISOR_MANUAL,
        risk_band=eff.band,
        risk_band_source_id=eff.source_id,
        template_version_id=active_template.id,
        goal_id=None,
        horizon_months=None,
        horizon_rule="MANUAL",
        as_of_date=now.date(),
        created_by=advisor_user_id,
        created_at=now,
        allocation=alloc_tuple,
    )

    audit_repository.insert_audit_event(
        session,
        actor_user_id=advisor_user_id,
        actor_role=principal.role.value,
        action=ACTION_MANUAL_REC,
        entity_type="recommendation",
        entity_id=rec.id,
        details={},
    )
    session.commit()

    logger.info("manual recommendation logged", extra={"customer_id": customer_id, "entity_id": rec.id})

    total = sum((a.target_pct for a in allocations), Decimal("0.00"))
    alloc_tuple = tuple((a.asset_class, a.target_pct) for a in allocations)

    return RecommendationView(
        id=rec.id,
        source=RecommendationSource.ADVISOR_MANUAL,
        risk_band=eff.band,
        template_version_no=active_template.version_no,
        goal_id=None,
        horizon_months=None,
        horizon_rule="MANUAL",
        as_of_date=now.date(),
        allocation=alloc_tuple,
        total_pct=total,
        created_at=now,
    )


def get_customer_audit(session: Session, advisor_user_id: str, customer_id: str) -> list[AuditEventItemView]:
    """Get audit trail for customer, newest first (AC-09.2)."""
    _check_assignment(session, advisor_user_id, customer_id)

    assessments = risk_assessment_repository.list_for_customer(session, customer_id)
    overrides = risk_override_repository.list_for_customer(session, customer_id)
    recs = recommendation_repository.list_for_customer(session, customer_id)
    goals = goals_service.list_goals(session, customer_id)
    rebal_recs = rebalancing_repository.list_for_customer(session, customer_id)

    entity_ids = {customer_id}
    entity_ids.update(a.id for a in assessments)
    entity_ids.update(o.id for o in overrides)
    entity_ids.update(r.id for r in recs)
    entity_ids.update(g.id for g in goals)
    entity_ids.update(r.id for r in rebal_recs)

    stmt = (
        select(AuditEvent)
        .where(AuditEvent.entity_id.in_(entity_ids))
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    )
    events = list(session.scalars(stmt))
    views: list[AuditEventItemView] = []
    for e in events:
        safe_details = {k: v for k, v in (e.details or {}).items() if k != "note"}
        views.append(
            AuditEventItemView(
                occurred_at=e.occurred_at,
                action=e.action,
                actor_role=e.actor_role,
                actor_user_id=e.actor_user_id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                details=safe_details,
            )
        )
    return views
