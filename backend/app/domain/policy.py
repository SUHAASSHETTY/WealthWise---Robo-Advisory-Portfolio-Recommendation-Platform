"""Policy-version lifecycle (admin_versioning_spec §2.1): DRAFT → PUBLISHED, published versions are immutable."""

from enum import StrEnum


class PolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class RecommendationSource(StrEnum):
    SYSTEM = "SYSTEM"
    ADVISOR_MANUAL = "ADVISOR_MANUAL"
