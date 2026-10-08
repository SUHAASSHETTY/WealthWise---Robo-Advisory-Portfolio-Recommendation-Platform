"""FastAPI application factory.

Run locally: `cd backend && WEALTHWISE_STUB_AUTH_ENABLED=true poetry run uvicorn app.main:app --reload --port 8000
--no-access-log` (the correlation-ID middleware already writes JSON request logs; uvicorn's access log would bypass
the PII allow-list).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import correlation_id_middleware
from app.api.routers import (
    admin_asset_classes,
    admin_nav,
    admin_risk_policies,
    admin_template_versions,
    advisor,
    auth,
    goals,
    health,
    holdings,
    rebalancing,
    recommendations,
    risk_profile,
)
from app.core.clock import AnchoredClock, Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import build_engine, build_session_factory
from app.core.logging import configure_logging


def _clock_for(settings: Settings, clock: Clock | None) -> Clock:
    if clock is not None:
        return clock
    return AnchoredClock(settings.fixed_clock) if settings.fixed_clock else SystemClock()


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(settings.database_url)
        app.state.session_factory = build_session_factory(engine)
        yield
        engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.clock = _clock_for(settings, clock)
    app.middleware("http")(correlation_id_middleware)
    register_error_handlers(app)
    app.include_router(health.router)
    for module in (
        auth,
        risk_profile,
        recommendations,
        holdings,
        goals,
        rebalancing,
        advisor,
        admin_asset_classes,
        admin_template_versions,
        admin_risk_policies,
        admin_nav,
    ):
        app.include_router(module.router)
    return app


app = create_app()
