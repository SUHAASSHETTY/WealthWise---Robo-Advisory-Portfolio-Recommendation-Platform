"""Decimal inputs must be JSON strings (app_spec §5.1, NFR-01): a JSON number is rejected with 422."""

from typing import Any

from fastapi import HTTPException, status


def float_paths(value: Any, path: str = "$") -> list[str]:
    """JSONPath-ish locations of every float in a parsed JSON value."""
    if isinstance(value, float):
        return [path]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in float_paths(v, f"{path}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in float_paths(v, f"{path}[{i}]")]
    return []


def require_decimal_strings(value: Any) -> None:
    paths = float_paths(value)
    if paths:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DECIMAL_MUST_BE_STRING",
                "message": 'Decimal values must be JSON strings, e.g. "5.00".',
                "details": {"paths": paths},
            },
        )
