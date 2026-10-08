"""Request/response models for /api/v1/admin/{risk-policies,template-versions} (admin_versioning_spec §4)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.policy import PolicyStatus


class DefinitionUpdate(BaseModel):
    definition: dict[str, Any]


class VersionSummary(BaseModel):
    id: str
    version_no: int
    status: PolicyStatus
    published_at: datetime | None


class VersionDetail(VersionSummary):
    created_at: datetime
    definition: dict[str, Any]
