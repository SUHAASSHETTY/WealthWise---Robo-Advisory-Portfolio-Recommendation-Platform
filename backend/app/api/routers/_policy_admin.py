"""Builds the identical admin route set for each policy kind (admin_versioning_spec §4). ADMIN only."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import AdminPrincipal, CurrentClock, DbSession, require_role
from app.api.schemas.decimals import require_decimal_strings
from app.api.schemas.policy_versions import DefinitionUpdate, VersionDetail, VersionSummary
from app.core.security import Principal, Role
from app.services import policy_version_service as svc
from app.services.customer_resolver import user_id_for


def _actor(session: DbSession, principal: Annotated[Principal, Depends(require_role(Role.ADMIN))]) -> svc.Actor:
    return svc.Actor(user_id=user_id_for(session, principal), role=principal.role.value)


ActorDep = Annotated[svc.Actor, Depends(_actor)]


def add_policy_admin_routes(router: APIRouter, kind: svc.PolicyKind) -> None:
    def list_versions(_: AdminPrincipal, session: DbSession) -> list[VersionSummary]:
        return [VersionSummary.model_validate(r, from_attributes=True) for r in svc.list_versions(session, kind)]

    def get_version(version_id: str, _: AdminPrincipal, session: DbSession) -> VersionDetail:
        return VersionDetail.model_validate(svc.get_version(session, kind, version_id), from_attributes=True)

    def create_draft(actor: ActorDep, session: DbSession) -> VersionDetail:
        return VersionDetail.model_validate(svc.create_draft(session, kind, actor), from_attributes=True)

    def update_draft(version_id: str, body: DefinitionUpdate, actor: ActorDep, session: DbSession) -> VersionDetail:
        require_decimal_strings(body.definition)
        row = svc.update_draft(session, kind, version_id, body.definition, actor)
        return VersionDetail.model_validate(row, from_attributes=True)

    def delete_draft(version_id: str, actor: ActorDep, session: DbSession) -> Response:
        svc.delete_draft(session, kind, version_id, actor)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def publish(version_id: str, actor: ActorDep, session: DbSession, clock: CurrentClock) -> VersionSummary:
        return VersionSummary.model_validate(svc.publish(session, kind, version_id, actor, clock), from_attributes=True)

    router.add_api_route("", list_versions, methods=["GET"])
    router.add_api_route("/drafts", create_draft, methods=["POST"], status_code=status.HTTP_201_CREATED)
    router.add_api_route("/{version_id}", get_version, methods=["GET"])
    router.add_api_route("/{version_id}", update_draft, methods=["PUT"])
    router.add_api_route("/{version_id}", delete_draft, methods=["DELETE"], status_code=status.HTTP_204_NO_CONTENT)
    router.add_api_route("/{version_id}/publish", publish, methods=["POST"])
