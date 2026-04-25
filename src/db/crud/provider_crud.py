"""
Async CRUD cho ProviderConfig — Fernet-encrypted credentials.

Tương đương src/modules/database.py set/list/delete_provider_config nhưng async + PostgreSQL.
"""
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProviderConfig
from src.modules.credential_vault import decrypt, encrypt


async def set_provider_config(
    db: AsyncSession,
    provider_name: str,
    config_dict: dict,
    *,
    user_id: str = "default_user",
) -> ProviderConfig:
    """Upsert provider config (encrypted). Tạo mới hoặc cập nhật."""
    import json

    encrypted = encrypt(json.dumps(config_dict))

    # Kiểm tra tồn tại
    stmt = select(ProviderConfig).where(
        ProviderConfig.user_id == user_id,
        ProviderConfig.provider_name == provider_name,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.config_json = encrypted
        existing.active = True
        await db.flush()
        await db.refresh(existing)
        return existing
    else:
        config = ProviderConfig(
            user_id=user_id,
            provider_name=provider_name,
            config_json=encrypted,
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
        return config


async def list_provider_configs(
    db: AsyncSession, *, user_id: str = "default_user"
) -> list[str]:
    """Lấy danh sách provider names đang active."""
    result = await db.execute(
        select(ProviderConfig.provider_name).where(
            ProviderConfig.user_id == user_id,
            ProviderConfig.active.is_(True),
        )
    )
    return [row[0] for row in result.all()]


async def get_provider_config(
    db: AsyncSession,
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> Optional[dict]:
    """Lấy và decrypt config của một provider."""
    import json

    result = await db.execute(
        select(ProviderConfig).where(
            ProviderConfig.user_id == user_id,
            ProviderConfig.provider_name == provider_name,
            ProviderConfig.active.is_(True),
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return None
    return json.loads(decrypt(config.config_json))


async def delete_provider_config(
    db: AsyncSession,
    provider_name: str,
    *,
    user_id: str = "default_user",
) -> bool:
    """Xóa provider config."""
    result = await db.execute(
        delete(ProviderConfig).where(
            ProviderConfig.user_id == user_id,
            ProviderConfig.provider_name == provider_name,
        )
    )
    return (result.rowcount or 0) > 0  # type: ignore[attr-defined]
