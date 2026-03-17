"""Модуль настройки взаимодействия с базой данных"""

# region Imports
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wallet_service.config import settings

# endregion


engine: AsyncEngine = create_async_engine(
    max_overflow=settings.ALCHEMY_MAX_OVERFLOW,
    pool_size=settings.ALCHEMY_POOL_SIZE,
    url=settings.database_url_asyncpg,
    future=True,
    echo=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Каждый запрос получает свою AsyncSession, которая закрывается
        автоматически после выхода из генератора.
    """
    async with AsyncSessionLocal() as session:
        yield session
