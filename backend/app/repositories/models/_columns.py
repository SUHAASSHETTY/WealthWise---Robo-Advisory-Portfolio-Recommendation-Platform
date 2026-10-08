"""Shared column helpers for ORM models."""

import uuid
from datetime import UTC, datetime


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(tz=UTC)
