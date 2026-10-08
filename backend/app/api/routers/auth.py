"""Auth routes. `whoami` lets any authenticated role confirm its identity (NFR-04)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_role
from app.api.routers import API_V1
from app.core.security import Principal, Role

router = APIRouter(prefix=f"{API_V1}/auth", tags=["auth"])


class WhoAmI(BaseModel):
    username: str
    role: Role


@router.get("/whoami", response_model=WhoAmI)
def whoami(principal: Annotated[Principal, Depends(require_role(Role.CUSTOMER, Role.ADVISOR, Role.ADMIN))]) -> WhoAmI:
    return WhoAmI(username=principal.username, role=principal.role)
