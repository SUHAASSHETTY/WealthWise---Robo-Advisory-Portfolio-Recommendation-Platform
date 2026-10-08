"""Maps exceptions to the error envelope {"error": {"code", "message", "details"}} (app_spec §5.7)."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.errors import ServiceError

_DEFAULT_CODES = {400: "BAD_REQUEST", 401: "UNAUTHENTICATED", 403: "FORBIDDEN_ROLE", 404: "NOT_FOUND", 409: "CONFLICT"}


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    code = str(detail.get("code", _DEFAULT_CODES.get(exc.status_code, "ERROR")))
    details = detail.get("details")
    body = _envelope(code, str(detail.get("message", "")), details if isinstance(details, dict) else None)
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [{"loc": list(err.get("loc", ())), "type": err.get("type")} for err in exc.errors()]
    return JSONResponse(status_code=422, content=_envelope("VALIDATION_FAILED", "Invalid request.", {"fields": fields}))


async def _service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceError)
    return JSONResponse(status_code=exc.status, content=_envelope(exc.code, exc.message, exc.details))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
