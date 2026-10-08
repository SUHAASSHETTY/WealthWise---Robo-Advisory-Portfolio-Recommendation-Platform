"""All ORM models; importing this package registers every table on Base.metadata (used by Alembic)."""

from app.repositories.models.audit_event import AuditEvent
from app.repositories.models.goal import Goal
from app.repositories.models.goal_progress_snapshot import GoalProgressSnapshot
from app.repositories.models.holding import Holding
from app.repositories.models.nav_price import NavPrice
from app.repositories.models.rebalancing_decision import RebalancingDecision
from app.repositories.models.rebalancing_recommendation import RebalancingLine, RebalancingRecommendation
from app.repositories.models.recommendation import Recommendation, RecommendationAllocation
from app.repositories.models.reference import AssetClass, Customer, User
from app.repositories.models.risk_assessment import RiskAssessment
from app.repositories.models.risk_band_override import RiskBandOverride
from app.repositories.models.risk_policy_version import RiskPolicyVersion
from app.repositories.models.stub_order import StubOrder
from app.repositories.models.template_version import TemplateVersion

__all__ = [
    "AssetClass",
    "AuditEvent",
    "Customer",
    "Goal",
    "GoalProgressSnapshot",
    "Holding",
    "NavPrice",
    "RebalancingDecision",
    "RebalancingLine",
    "RebalancingRecommendation",
    "Recommendation",
    "RecommendationAllocation",
    "RiskAssessment",
    "RiskBandOverride",
    "RiskPolicyVersion",
    "StubOrder",
    "TemplateVersion",
    "User",
]
