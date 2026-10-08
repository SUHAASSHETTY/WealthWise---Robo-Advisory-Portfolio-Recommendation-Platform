"""AC-10 / NFR-08 (admin_versioning_spec §2.1): PUBLISHED template versions are immutable.

ORM-level proof on an in-memory SQLite schema: update and delete of a PUBLISHED TemplateVersion raise
PublishedVersionMutation; a DRAFT may be edited and published, after which it is frozen too.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.db import build_engine, build_session_factory
from app.domain.policy import PolicyStatus
from app.repositories.base import Base
from app.repositories.errors import PublishedVersionMutation
from app.repositories.models.template_version import TemplateVersion

SEED_FILE = Path(__file__).resolve().parents[2] / "backend" / "app" / "seed" / "policies" / "template_v1.json"
PUBLISHED_AT = datetime(2026, 4, 1, 9, 30, tzinfo=UTC)


def _seed_definition() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    definition: dict[str, Any] = data["definition"]
    return definition


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = build_engine("sqlite://")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with build_session_factory(engine)() as sess:
        yield sess


def _add_version(session: Session, version_no: int, status: PolicyStatus) -> TemplateVersion:
    row = TemplateVersion(version_no=version_no, status=status, definition=_seed_definition())
    if status is PolicyStatus.PUBLISHED:
        row.published_at = PUBLISHED_AT
    session.add(row)
    session.commit()
    return row


def _stored_definition(engine: Engine, version_no: int) -> dict[str, Any]:
    with build_session_factory(engine)() as fresh:
        stmt = select(TemplateVersion.definition).where(TemplateVersion.version_no == version_no)
        stored: dict[str, Any] = fresh.execute(stmt).scalar_one()
        return stored


@pytest.mark.ac("AC-10")
def test_ac_10_updating_published_version_raises_and_leaves_row_unchanged(engine: Engine, session: Session) -> None:
    """AC-10.3: editing a PUBLISHED template's definition is rejected; the stored row is untouched."""
    row = _add_version(session, 1, PolicyStatus.PUBLISHED)
    original = _seed_definition()
    edited = copy.deepcopy(original)
    edited["templates"]["MODERATE"]["EQUITY"] = "55.00"
    edited["templates"]["MODERATE"]["DEBT"] = "30.00"
    row.definition = edited

    with pytest.raises(PublishedVersionMutation):
        session.flush()
    session.rollback()

    assert _stored_definition(engine, 1) == original


@pytest.mark.ac("AC-10")
def test_ac_10_deleting_published_version_raises(engine: Engine, session: Session) -> None:
    """AC-10.3: a PUBLISHED template version cannot be deleted."""
    row = _add_version(session, 1, PolicyStatus.PUBLISHED)
    session.delete(row)

    with pytest.raises(PublishedVersionMutation):
        session.flush()
    session.rollback()

    with build_session_factory(engine)() as fresh:
        assert fresh.query(TemplateVersion).count() == 1


@pytest.mark.ac("AC-10")
def test_ac_10_unpublishing_a_published_version_raises(engine: Engine, session: Session) -> None:
    """AC-10.3: PUBLISHED -> DRAFT is not a valid transition."""
    row = _add_version(session, 1, PolicyStatus.PUBLISHED)
    row.status = PolicyStatus.DRAFT

    with pytest.raises(PublishedVersionMutation):
        session.flush()


@pytest.mark.ac("AC-10")
def test_ac_10_draft_can_be_edited_then_published_then_frozen(engine: Engine, session: Session) -> None:
    """AC-10.1/AC-10.3: a DRAFT is editable and publishable (DRAFT -> PUBLISHED); afterwards edits raise."""
    draft = _add_version(session, 2, PolicyStatus.DRAFT)
    edited = _seed_definition()
    edited["drift_threshold_pct"] = "4.00"
    draft.definition = edited
    session.commit()
    assert _stored_definition(engine, 2)["drift_threshold_pct"] == "4.00"

    draft.status = PolicyStatus.PUBLISHED
    draft.published_at = PUBLISHED_AT
    session.commit()

    frozen = copy.deepcopy(edited)
    frozen["drift_threshold_pct"] = "6.00"
    draft.definition = frozen
    with pytest.raises(PublishedVersionMutation):
        session.flush()
    session.rollback()
    assert _stored_definition(engine, 2)["drift_threshold_pct"] == "4.00"
