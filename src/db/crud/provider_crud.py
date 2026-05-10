"""
CRUD cho ProviderConfig — Fernet-encrypted credentials via Supabase.

Dùng supabase-py client (SERVICE_ROLE_KEY). Tất cả hàm đồng bộ (sync).
"""
import json
from typing import Any, Optional

from src.db import supabase_client as sc
from src.modules.credential_vault import decrypt, encrypt


def set_provider_config(
    provider_name: str,
    config_dict: dict[str, Any],
    *,
    user_id: str = "default_user",
) -> dict[str, Any]:
    """Upsert provider config (encrypted)."""
    encrypted = encrypt(json.dumps(config_dict))

    # Kiểm tra tồn tại
    existing = sc.fetch_one(sc.TABLE_PROVIDER_CONFIGS, {
        "user_id": user_id,
        "provider_name": provider_name,
    })

    if existing:
        return sc.update_by_id(sc.TABLE_PROVIDER_CONFIGS, existing["id"], {
            "config_json": encrypted,
            "active": True,
        })
    else:
        return sc.insert(sc.TABLE_PROVIDER_CONFIGS, {
            "user_id": user_id,
            "provider_name": provider_name,
            "config_json": encrypted,
            "active": True,
        })


def list_provider_configs(
    *,
    user_id: str = "default_user",
) -> list[str]:
    """Lấy danh sách provider names đang active."""
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_PROVIDER_CONFIGS).select(
        "provider_name"
    ).eq("user_id", user_id).eq("active", True).execute()
    return [row["provider_name"] for row in (result.data or [])]


def get_provider_config(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> Optional[dict[str, Any]]:
    """Lấy và decrypt config của một provider."""
    config = sc.fetch_one(sc.TABLE_PROVIDER_CONFIGS, {
        "user_id": user_id,
        "provider_name": provider_name,
        "active": True,
    })
    if not config:
        return None
    return json.loads(decrypt(config["config_json"]))


def delete_provider_config(
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> bool:
    """Xóa provider config."""
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_PROVIDER_CONFIGS).delete().eq(
        "user_id", user_id
    ).eq("provider_name", provider_name).execute()
    return bool(result.data)
