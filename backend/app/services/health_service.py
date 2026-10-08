"""Health use case (app_spec §5.8, NFR-07)."""

import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories import health_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HealthStatus:
    healthy: bool

    @property
    def body(self) -> dict[str, str]:
        if self.healthy:
            return {"status": "ok", "db": "connected"}
        return {"status": "unavailable", "db": "unreachable"}


def check_health(session: Session) -> HealthStatus:
    try:
        health_repository.ping(session)
    except SQLAlchemyError:
        logger.warning("health check failed", extra={"outcome": "db_unreachable"})
        return HealthStatus(healthy=False)
    return HealthStatus(healthy=True)
