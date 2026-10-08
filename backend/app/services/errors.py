"""Typed service errors mapped to the error envelope by app.api.errors (app_spec §5.7)."""

from typing import Any


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def not_found(code: str, message: str = "Not found.") -> ServiceError:
    return ServiceError(404, code, message)


def conflict(code: str, message: str, details: dict[str, Any] | None = None) -> ServiceError:
    return ServiceError(409, code, message, details)


def unprocessable(code: str, message: str, details: dict[str, Any] | None = None) -> ServiceError:
    return ServiceError(422, code, message, details)
