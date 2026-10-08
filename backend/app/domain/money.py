"""Fixed-point helpers (app_spec §5.1, NFR-01). Decimals are built from str/int only — never float."""

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal, InvalidOperation

CENT = Decimal("0.01")
UNIT_STEP = Decimal("0.0001")
HUNDRED = Decimal("100")


def to_decimal(value: str | int | Decimal) -> Decimal:
    """Convert to Decimal, rejecting floats and bools (which would carry binary rounding error)."""
    if isinstance(value, bool) or not isinstance(value, str | int | Decimal):
        raise TypeError(f"expected str, int or Decimal, got {type(value).__name__}")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{value!r} is not a decimal number") from exc


def q2(value: Decimal) -> Decimal:
    """Money / percent: 2 dp, banker's rounding (ROUND_HALF_EVEN)."""
    return value.quantize(CENT, rounding=ROUND_HALF_EVEN)


def q4_down(value: Decimal) -> Decimal:
    """Units / quantities: 4 dp, always rounded down so we never over-trade."""
    return value.quantize(UNIT_STEP, rounding=ROUND_DOWN)
