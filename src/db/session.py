"""
AsyncSession factory và FastAPI dependency get_db.

Sử dụng pattern: mỗi request nhận một session riêng, tự commit/rollback.
"""
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.config import get_settings
from src.db.base import make_engine

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# Worker engine dùng NullPool để tránh asyncpg connections bị bind vào event loop cũ.
_worker_engine: Optional[AsyncEngine] = None
_worker_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine() -> AsyncEngine:
    """Khởi tạo engine một lần (gọi trong lifespan FastAPI)."""
    global _engine, _session_factory
    settings = get_settings()
    _engine = make_engine(settings.postgres_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> "async_sessionmaker[AsyncSession]":
    """Trả về session factory dùng NullPool cho Celery workers.

    NullPool đảm bảo mỗi asyncio.run() tạo connections mới, không dùng lại
    connections từ event loop trước đó.
    """
    global _worker_engine, _worker_session_factory
    if _worker_session_factory is None:
        settings = get_settings()
        _worker_engine = make_engine(settings.postgres_url, poolclass=NullPool)
        _worker_session_factory = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _worker_session_factory


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Engine chưa được khởi tạo. Gọi init_engine() trước.")
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: cấp AsyncSession cho mỗi request."""
    if _session_factory is None:
        raise RuntimeError("Session factory chưa được khởi tạo.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
