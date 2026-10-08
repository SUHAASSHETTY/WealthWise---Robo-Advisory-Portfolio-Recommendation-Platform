"""Risk policy versions: questionnaire, points, band thresholds, caps (admin_versioning_spec §3)."""

from app.repositories.base import Base
from app.repositories.guards import protect_published_versions
from app.repositories.models._versioned import VersionedPolicyMixin


class RiskPolicyVersion(VersionedPolicyMixin, Base):
    __tablename__ = "risk_policy_versions"


protect_published_versions(RiskPolicyVersion)
