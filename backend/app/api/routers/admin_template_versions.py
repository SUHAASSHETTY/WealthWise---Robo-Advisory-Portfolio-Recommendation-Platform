"""Admin: allocation template versions — draft, edit, publish (admin_versioning_spec §4, AC-10). ADMIN only."""

from fastapi import APIRouter

from app.api.routers import API_V1
from app.api.routers._policy_admin import add_policy_admin_routes
from app.services.policy_version_service import PolicyKind

router = APIRouter(prefix=f"{API_V1}/admin/template-versions", tags=["admin/template-versions"])

add_policy_admin_routes(router, PolicyKind.TEMPLATE)
