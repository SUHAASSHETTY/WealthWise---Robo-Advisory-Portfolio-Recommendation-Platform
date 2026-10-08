"""Allocation template versions (admin_versioning_spec §3)."""

from app.repositories.base import Base
from app.repositories.guards import protect_published_versions
from app.repositories.models._versioned import VersionedPolicyMixin


class TemplateVersion(VersionedPolicyMixin, Base):
    __tablename__ = "template_versions"


protect_published_versions(TemplateVersion)
