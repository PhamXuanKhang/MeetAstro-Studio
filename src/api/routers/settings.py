"""
Router: /api/v1/settings - manage provider configs.

GET    /settings/providers           List provider names
POST   /settings/providers/{name}    Set/update provider config
DELETE /settings/providers/{name}    Delete provider config
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_supabase
from src.db.crud.provider_crud import (
    delete_provider_config,
    list_provider_configs,
    set_provider_config,
)
from supabase import Client

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderConfigPayload(BaseModel):
    config: dict
    user_id: str = "default_user"


@router.get("/providers")
async def list_providers(
    supabase: Annotated[Client, Depends(get_supabase)],
    user_id: str = "default_user",
) -> dict:
    """List active provider names."""
    providers = list_provider_configs(user_id=user_id)
    return {"providers": providers}


@router.post("/providers/{provider_name}")
async def set_provider(
    provider_name: str,
    payload: ProviderConfigPayload,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> dict:
    """Add or update provider config (encrypted)."""
    set_provider_config(
        provider_name, payload.config, user_id=payload.user_id
    )
    return {"message": f"Provider '{provider_name}' saved."}


@router.delete("/providers/{provider_name}")
async def delete_provider(
    provider_name: str,
    supabase: Annotated[Client, Depends(get_supabase)],
    user_id: str = "default_user",
) -> dict:
    """Delete provider config."""
    deleted = delete_provider_config(provider_name, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Provider '{provider_name}' not found."
        )
    return {"message": f"Provider '{provider_name}' deleted."}
