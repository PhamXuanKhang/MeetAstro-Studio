"""
Router: /api/v1/settings — quản lý provider configs.

GET    /settings/providers           Danh sách provider names
POST   /settings/providers/{name}    Set/update provider config
DELETE /settings/providers/{name}    Xóa provider config
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.db.crud.provider_crud import (
    delete_provider_config,
    list_provider_configs,
    set_provider_config,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderConfigPayload(BaseModel):
    config: dict
    user_id: str = "default_user"


@router.get("/providers")
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = "default_user",
) -> dict:
    """Danh sách provider names đang active."""
    providers = await list_provider_configs(db, user_id=user_id)
    return {"providers": providers}


@router.post("/providers/{provider_name}")
async def set_provider(
    provider_name: str,
    payload: ProviderConfigPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Thêm hoặc cập nhật provider config (encrypted)."""
    await set_provider_config(
        db, provider_name, payload.config, user_id=payload.user_id
    )
    return {"message": f"Provider '{provider_name}' đã được lưu."}


@router.delete("/providers/{provider_name}")
async def delete_provider(
    provider_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = "default_user",
) -> dict:
    """Xóa provider config."""
    deleted = await delete_provider_config(db, provider_name, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' không tồn tại.")
    return {"message": f"Provider '{provider_name}' đã được xóa."}
