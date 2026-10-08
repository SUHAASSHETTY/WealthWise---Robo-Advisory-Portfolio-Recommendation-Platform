"""Schemas for Asset Classes API (admin_versioning_spec §4, AC-10)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    is_active: bool
    display_order: int
    created_at: datetime


class AssetClassCreateIn(BaseModel):
    code: str
    name: str
    display_order: int


class AssetClassPatchIn(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    display_order: int | None = None
