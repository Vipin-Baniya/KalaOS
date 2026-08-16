"""
KalaOS — Infrastructure: Async Database Client
================================================
SQLAlchemy 2.x async engine with:
- Connection pooling
- Session factory
- Health check
- Alembic-compatible base
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.models import *  # noqa: F401, F403

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,          # Re-validate stale connections
    pool_recycle=3600,           # Recycle connections every hour
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Declarative base for all ORM models ────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Dependency ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for injecting a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Lifecycle ──────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables. Use Alembic migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")


async def close_db() -> None:
    """Dispose engine connection pool on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed.")


# ── Health check ───────────────────────────────────────────────────────────

async def db_health() -> dict:
    """Return DB health for the /health endpoint."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        pool_status = engine.pool.status()
        return {
            "status": "healthy",
            "pool": pool_status,
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
