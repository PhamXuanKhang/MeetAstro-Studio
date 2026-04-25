"""
FastAPI dependency injection helpers.

get_db: AsyncSession cho mỗi request.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db as _get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Cấp AsyncSession từ session factory."""
    async for session in _get_db():
        yield session
