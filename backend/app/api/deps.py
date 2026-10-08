"""Request-scoped dependencies: DB session and the role-based authentication boundary (NFR-04)."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import Settings
from app.core.security import Principal, Role, resolve_stub_token
from app.services.customer_resolver import customer_id_for

_bearer = HTTPBearer(auto_error=False)


def get_settings_from_app(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHENTICATED", "message": "A valid bearer token is required."},
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> Principal:
    if credentials is None:
        raise _unauthenticated()
    principal = resolve_stub_token(credentials.credentials, enabled=settings.stub_auth_enabled)
    if principal is None:
        raise _unauthenticated()
    return principal


def require_role(*roles: Role) -> Callable[..., Principal]:
    """Dependency factory: authenticate, then allow only the given roles (403 FORBIDDEN_ROLE otherwise)."""
    allowed = frozenset(roles)

    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN_ROLE", "message": "This role may not access this resource."},
            )
        return principal

    return dependency


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


DbSession = Annotated[Session, Depends(get_db)]
CurrentClock = Annotated[Clock, Depends(get_clock)]
CustomerPrincipal = Annotated[Principal, Depends(require_role(Role.CUSTOMER))]
AdminPrincipal = Annotated[Principal, Depends(require_role(Role.ADMIN))]


def current_customer_id(principal: CustomerPrincipal, session: DbSession) -> str:
    """The caller's customer id, resolved from the token — never from a path parameter (NFR-04)."""
    return customer_id_for(session, principal)


CurrentCustomerId = Annotated[str, Depends(current_customer_id)]
