"""Columns shared by versioned policy tables (admin_versioning_spec §3)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.domain.policy import PolicyStatus
from app.repositories.models._columns import new_uuid, utcnow


class VersionedPolicyMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    version_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus, native_enum=False, length=16), nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    published_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Any, ...]:  # noqa: N805
        name = cls.__tablename__  # type: ignore[attr-defined]
        return (Index(f"uq_{name}_one_draft", "status", unique=True, sqlite_where=text("status = 'DRAFT'")),)
