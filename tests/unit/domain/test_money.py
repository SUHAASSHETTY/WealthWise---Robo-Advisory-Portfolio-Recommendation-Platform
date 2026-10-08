"""NFR-01 — fixed-point helpers: Decimal only, explicit rounding, floats rejected."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.money import q2, q4_down, to_decimal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("12.50", Decimal("12.50")), ("100", Decimal("100")), (5, Decimal("5")), (Decimal("7.50"), Decimal("7.50"))],
)
def test_to_decimal_accepts_str_int_and_decimal(raw: str | int | Decimal, expected: Decimal) -> None:
    assert to_decimal(raw) == expected


@pytest.mark.parametrize("raw", [0.1, 7.5, True])
def test_to_decimal_rejects_float_and_bool(raw: object) -> None:
    with pytest.raises(TypeError):
        to_decimal(raw)  # type: ignore[arg-type]


def test_to_decimal_rejects_malformed_text() -> None:
    with pytest.raises(ValueError, match="not a decimal"):
        to_decimal("twelve")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("12.345", "12.34"), ("12.355", "12.36"), ("99.9999", "100.00"), ("62.2641", "62.26")],
)
def test_q2_rounds_half_even_to_two_places(value: str, expected: str) -> None:
    assert q2(Decimal(value)) == Decimal(expected)


@pytest.mark.parametrize(
    ("value", "expected"), [("66.666666", "66.6666"), ("16.66669", "16.6666"), ("400", "400.0000")]
)
def test_q4_down_never_rounds_up(value: str, expected: str) -> None:
    assert q4_down(Decimal(value)) == Decimal(expected)
