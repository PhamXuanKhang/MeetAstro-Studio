"""
Router: /api/v1/settings - manage provider configs.

GET    /settings/providers           List provider names
GET    /settings/providers/{name}    Get provider status
POST   /settings/providers/{name}    Set/update provider config
DELETE /settings/providers/{name}    Delete provider config
"""
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.api.deps import get_supabase
from src.db.crud.provider_crud import (
    delete_provider_config,
    get_provider_config_status,
    list_provider_configs,
    set_provider_config,
)
from supabase import Client

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_unavailable() -> HTTPException:
    """Return a safe API error without exposing secrets or backend internals."""
    return HTTPException(
        status_code=503,
        detail="Provider settings service is unavailable. Check Supabase connectivity.",
    )


class ProviderConfigPayload(BaseModel):
    """Provider config payload.

    Supports both the existing generic shape:
      {"config": {...}, "user_id": "..."}

    and the flatter UI/contract-friendly shape:
      {"api_key": "...", "config_data": {...}, "user_id": "..."}
    """

    model_config = ConfigDict(extra="allow")

    config: Optional[dict[str, Any]] = None
    api_key: Optional[str] = None
    config_data: dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"

    def to_config_dict(self) -> dict[str, Any]:
        """Build the encrypted config payload without logging or exposing secrets."""
        if self.config is not None:
            return self.config

        data = self.model_dump(exclude={"config", "user_id"}, exclude_none=True)
        extra = self.model_extra or {}
        for key, value in extra.items():
            if key != "user_id":
                data[key] = value
        return data


@router.get("/providers")
async def list_providers(
    supabase: Annotated[Client, Depends(get_supabase)],
    user_id: str = "default_user",
) -> dict:
    """List active provider names."""
    try:
        providers = list_provider_configs(user_id=user_id)
        return {"providers": providers}
    except Exception as exc:
        raise _settings_unavailable() from exc


@router.get("/providers/{provider_name}")
async def get_provider(
    provider_name: str,
    supabase: Annotated[Client, Depends(get_supabase)],
    user_id: str = "default_user",
) -> dict:
    """Return provider configuration status without returning plaintext secrets."""
    try:
        return get_provider_config_status(provider_name, user_id=user_id)
    except Exception as exc:
        raise _settings_unavailable() from exc


@router.post("/providers/{provider_name}")
async def set_provider(
    provider_name: str,
    payload: ProviderConfigPayload,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> dict:
    """Add or update provider config (encrypted)."""
    config = payload.to_config_dict()
    if not config:
        raise HTTPException(status_code=400, detail="Provider config is required.")

    try:
        set_provider_config(
            provider_name, config, user_id=payload.user_id
        )
        return get_provider_config_status(provider_name, user_id=payload.user_id)
    except Exception as exc:
        raise _settings_unavailable() from exc


@router.delete("/providers/{provider_name}")
async def delete_provider(
    provider_name: str,
    supabase: Annotated[Client, Depends(get_supabase)],
    user_id: str = "default_user",
) -> dict:
    """Delete provider config."""
    try:
        deleted = delete_provider_config(provider_name, user_id=user_id)
    except Exception as exc:
        raise _settings_unavailable() from exc

    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Provider '{provider_name}' not found."
        )
    return {"message": f"Provider '{provider_name}' deleted."}
