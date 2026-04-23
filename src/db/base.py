"""
SQLAlchemy DeclarativeBase và engine factory cho PostgreSQL async.

Dùng create_async_engine với asyncpg driver.
"""
from typing import Optional, Type

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import Pool


class Base(DeclarativeBase):
    """Base class cho tất cả ORM models."""
    pass


def make_engine(postgres_url: str, poolclass: Optional[Type[Pool]] = None) -> AsyncEngine:
    """
    Tạo async engine từ POSTGRES_URL.

    URL format: postgresql+asyncpg://user:pass@host:port/dbname
    poolclass=NullPool dùng cho Celery workers để tránh cross-event-loop issues.
    """
    if not postgres_url:
        raise ValueError("POSTGRES_URL chưa được cấu hình.")
    url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    if poolclass is not None:
        return create_async_engine(url, echo=False, pool_pre_ping=True, poolclass=poolclass)
    return create_async_engine(
        url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
