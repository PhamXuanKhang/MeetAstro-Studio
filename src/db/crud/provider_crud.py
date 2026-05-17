"""
CRUD for provider_configs via Supabase.

Current Supabase schema:
  id, user_id, provider_name, api_key, config_data, created_at, updated_at

Secrets are Fernet-encrypted before writing to the api_key column. Non-secret
provider metadata is stored in config_data.
"""
from __future__ import annotations

from typing import Any, Optional

from src.db import supabase_client as sc
from src.modules.credential_vault import decrypt, encrypt


_SECRET_FIELD_NAMES = ("api_key", "apiKey", "apikey", "token", "api_token", "apiToken")


def _mask_secret(value: Any) -> Optional[str]:
    """Return a short secret preview without exposing the plaintext key."""
    if not isinstance(value, str) or not value:
        return None
    visible = min(4, len(value))
    return f"...{value[-visible:]}"


def _extract_secret(config_dict: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
    """Split a provider config into plaintext secret and non-secret metadata."""
    config_data = dict(config_dict)

    nested_config_data = config_data.pop("config_data", None)
    if isinstance(nested_config_data, dict):
        config_data.update(nested_config_data)

    for key in _SECRET_FIELD_NAMES:
        value = config_data.pop(key, None)
        if isinstance(value, str) and value:
            return value, config_data

    return None, config_data


def _fetch_provider_config_row(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> Optional[dict[str, Any]]:
    """Fetch one provider row without assuming DB uniqueness is perfect."""
    client = sc.get_supabase_client()
    result = (
        client.table(sc.TABLE_PROVIDER_CONFIGS)
        .select("*")
        .eq("user_id", user_id)
        .eq("provider_name", provider_name)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def set_provider_config(
    provider_name: str,
    config_dict: dict[str, Any],
    *,
    user_id: str = "default_user",
) -> dict[str, Any]:
    """Upsert provider config, encrypting secret fields before persistence."""
    secret, config_data = _extract_secret(config_dict)
    encrypted_api_key = encrypt(secret) if secret else None

    data: dict[str, Any] = {
        "provider_name": provider_name,
        "user_id": user_id,
        "config_data": config_data,
    }
    if encrypted_api_key is not None:
        data["api_key"] = encrypted_api_key

    existing = _fetch_provider_config_row(provider_name, user_id=user_id)
    if existing:
        return sc.update_by_id(sc.TABLE_PROVIDER_CONFIGS, existing["id"], data)
    return sc.insert(sc.TABLE_PROVIDER_CONFIGS, data)


def list_provider_configs(
    *,
    user_id: str = "default_user",
) -> list[str]:
    """List configured provider names for a user."""
    client = sc.get_supabase_client()
    result = (
        client.table(sc.TABLE_PROVIDER_CONFIGS)
        .select("provider_name")
        .eq("user_id", user_id)
        .execute()
    )
    return [row["provider_name"] for row in (result.data or [])]


def get_provider_config(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> Optional[dict[str, Any]]:
    """Return provider config with decrypted api_key for server-side use only."""
    row = _fetch_provider_config_row(provider_name, user_id=user_id)
    if not row:
        return None

    config = dict(row.get("config_data") or {})
    encrypted_api_key = row.get("api_key")
    if encrypted_api_key:
        config["api_key"] = decrypt(encrypted_api_key)
    return config


def get_provider_config_status(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> dict[str, Any]:
    """Return provider configuration status without exposing plaintext secrets."""
    row = _fetch_provider_config_row(provider_name, user_id=user_id)
    if not row:
        return {
            "provider_name": provider_name,
            "is_configured": False,
            "masked_key": None,
        }

    masked_key = None
    encrypted_api_key = row.get("api_key")
    if encrypted_api_key:
        try:
            masked_key = _mask_secret(decrypt(encrypted_api_key))
        except Exception:
            masked_key = None

    return {
        "provider_name": provider_name,
        "is_configured": True,
        "masked_key": masked_key,
    }


def delete_provider_config(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> bool:
    """Delete provider config."""
    client = sc.get_supabase_client()
    result = (
        client.table(sc.TABLE_PROVIDER_CONFIGS)
        .delete()
        .eq("user_id", user_id)
        .eq("provider_name", provider_name)
        .execute()
    )
    return bool(result.data)
