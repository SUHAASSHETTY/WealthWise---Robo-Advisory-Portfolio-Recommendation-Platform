"""Risk bands and their order (risk_profile_spec §2.2-2.3): CONSERVATIVE < MODERATE < AGGRESSIVE."""

from enum import StrEnum


class RiskBand(StrEnum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"

    @property
    def rank(self) -> int:
        return BAND_ORDER.index(self)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskBand):
            return NotImplemented
        return self.rank < other.rank


BAND_ORDER: tuple[RiskBand, ...] = (RiskBand.CONSERVATIVE, RiskBand.MODERATE, RiskBand.AGGRESSIVE)


def min_band(first: RiskBand, second: RiskBand) -> RiskBand:
    """The more conservative of two bands (used to apply caps)."""
    return first if first.rank <= second.rank else second
