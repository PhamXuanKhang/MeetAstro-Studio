"""
Router: /api/v1/settings - manage provider configs.

GET    /settings/providers           List provider names
POST   /settings/providers/{name}    Set/update provider config
DELETE /settings/providers/{name}    Delete provider config
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
    """Payload for setting provider config."""
    config: dict
    user_id: str = "default_user"


@router.get("/providers")
async def list_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = "default_user",
) -> dict:
    """List active provider names."""
    providers = await list_provider_configs(db, user_id=user_id)
    return {"providers": providers}


@router.post("/providers/{provider_name}")
async def set_provider(
    provider_name: str,
    payload: ProviderConfigPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Add or update provider config (encrypted)."""
    await set_provider_config(
        db, provider_name, payload.config, user_id=payload.user_id
    )
    return {"message": f"Provider '{provider_name}' saved."}


@router.delete("/providers/{provider_name}")
async def delete_provider(
    provider_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = "default_user",
) -> dict:
    """Delete provider config."""
    deleted = await delete_provider_config(db, provider_name, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Provider '{provider_name}' not found."
        )
    return {"message": f"Provider '{provider_name}' deleted."}
