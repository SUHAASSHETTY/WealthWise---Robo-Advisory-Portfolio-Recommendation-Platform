"""GET /health — public liveness + DB check (NFR-07)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.deps import DbSession
from app.services.health_service import check_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: DbSession) -> JSONResponse:
    result = check_health(session)
    return JSONResponse(status_code=200 if result.healthy else 503, content=result.body)
