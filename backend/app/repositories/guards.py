"""ORM guards that make published policy versions immutable (admin_versioning_spec §2.1, AC-10, NFR-08).

A DRAFT may be edited and published (DRAFT → PUBLISHED is the only transition). Once the *persisted*
status is PUBLISHED, any flush that updates or deletes the row raises PublishedVersionMutation.
"""

from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper

from app.domain.policy import PolicyStatus
from app.repositories.errors import AppendOnlyViolation, PublishedVersionMutation


def _persisted_status(target: Any) -> object:
    history = inspect(target).attrs.status.history
    return history.deleted[0] if history.deleted else target.status


def _block_update(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    if _persisted_status(target) == PolicyStatus.PUBLISHED:
        raise PublishedVersionMutation(f"{mapper.class_.__tablename__} v{target.version_no} is PUBLISHED")


def _block_delete(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    if _persisted_status(target) == PolicyStatus.PUBLISHED:
        raise PublishedVersionMutation(f"{mapper.class_.__tablename__} v{target.version_no} is PUBLISHED")


def protect_published_versions(model: type[Any]) -> None:
    """Register the immutability listeners on a versioned-policy model with `status` and `version_no`."""
    event.listen(model, "before_update", _block_update)
    event.listen(model, "before_delete", _block_delete)


def _block_append_only(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
    raise AppendOnlyViolation(f"{mapper.class_.__tablename__} is append-only")


def protect_append_only(model: type[Any]) -> None:
    """Register listeners that forbid any ORM UPDATE or DELETE on an insert-only model (NFR-02)."""
    event.listen(model, "before_update", _block_append_only)
    event.listen(model, "before_delete", _block_append_only)
