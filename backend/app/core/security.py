"""Roles and stub-token authentication (NFR-04).

Stub tokens are **synthetic, development-only** credentials for the seeded demo users. They are disabled
with WEALTHWISE_STUB_AUTH_ENABLED=false; the JWT login in app_spec §5.5 replaces them in a later phase.
"""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    ADVISOR = "ADVISOR"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class Principal:
    username: str
    role: Role


_STUB_PRINCIPALS: dict[str, Principal] = {
    "stub-token-alice": Principal("alice.customer", Role.CUSTOMER),
    "stub-token-bob": Principal("bob.customer", Role.CUSTOMER),
    "stub-token-carol": Principal("carol.customer", Role.CUSTOMER),
    "stub-token-frank": Principal("frank.customer", Role.CUSTOMER),
    "stub-token-grace": Principal("grace.customer", Role.CUSTOMER),
    "stub-token-dan": Principal("dan.advisor", Role.ADVISOR),
    "stub-token-erin": Principal("erin.admin", Role.ADMIN),
}


def resolve_stub_token(token: str, *, enabled: bool) -> Principal | None:
    """Return the principal for a stub token, or None if unknown or stub auth is disabled."""
    if not enabled:
        return None
    return _STUB_PRINCIPALS.get(token)
