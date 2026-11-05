"""Database engine and the per-request session.

Convention used across the backend: **services own the transaction**. A
service function that changes data calls `await db.commit()` itself before it
returns, so the data is saved before the HTTP response goes out. Anything not
committed is rolled back when the session closes.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_pre_ping=True,
    # A failed query's error names its values (a child's answer, a name); in production they are left
    # out of the error, and so out of the logs.
    hide_parameters=_settings.is_production,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one database session per request."""
    async with SessionLocal() as session:
        yield session
