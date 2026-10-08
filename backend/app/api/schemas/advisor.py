"""Schemas for Advisor Workbench API (advisor_workbench_spec §4, AC-09)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.goals import GoalOut
from app.api.schemas.holdings import HoldingsResponse
from app.api.schemas.rebalancing import RebalanceProposalOut
from app.api.schemas.recommendations import RecommendationOut


class AdvisorCustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    display_name: str
    effective_band: str | None = None
    band_source: str | None = None
    portfolio_breached: bool
    open_rebalance_id: str | None = None


class CustomerInfoOut(BaseModel):
    id: str
    display_name: str
    kyc_verified: bool


class RiskProfileSummaryOut(BaseModel):
    band: str | None = None
    source: str | None = None
    as_of: datetime | None = None


class AdvisorCustomerPortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer: CustomerInfoOut
    risk_profile: RiskProfileSummaryOut
    goals: list[GoalOut] = Field(default_factory=list)
    holdings: HoldingsResponse
    latest_recommendation: RecommendationOut | None = None
    open_rebalance: RebalanceProposalOut | None = None


class RiskOverrideIn(BaseModel):
    new_band: str
    reason_code: str
    note: str


class RiskOverrideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    override_id: str
    previous_band: str
    new_band: str
    reason_code: str
    actor_user_id: str
    created_at: datetime


class ManualAllocationItemIn(BaseModel):
    asset_class: str
    target_pct: str


class ManualRecommendationIn(BaseModel):
    allocation: list[ManualAllocationItemIn]
    note: str


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    occurred_at: datetime
    action: str
    actor_role: str
    actor_user_id: str | None = None
    entity_type: str
    entity_id: str
    details: dict[str, object] = Field(default_factory=dict)
