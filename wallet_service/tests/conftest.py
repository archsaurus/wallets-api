"""Фикстуры для тестов сервиса управления кошельками."""

# region Imports
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wallet_service.application.database import get_async_session
from wallet_service.application.main import wallet_application
from wallet_service.application.models import Base, Wallet
from wallet_service.application.router import wallet_router

# endregion


@pytest_asyncio.fixture
async def mock_wallet() -> Wallet:
    """Фикстура принимает int, float, str, Decimal."""
    def _create(
        wallet_uuid: uuid.UUID = uuid.uuid4(),
        balance: any = 0
    ) -> Wallet:
        balance_decimal = Decimal(str(balance)) if isinstance(
            balance, (int, float, str, Decimal)
        ) else Decimal('0.00')

        return Wallet(
            uuid=wallet_uuid,
            balance=balance_decimal
        )

    return _create


@pytest_asyncio.fixture(scope='function')
async def async_client(db_session: AsyncSession) -> TestClient:
    """TestClient с dependency overrides."""
    app = FastAPI(
        title=wallet_application.title,
        description=wallet_application.description,
        version=wallet_application.version,
    )

    app.include_router(wallet_router)
    app.dependency_overrides[get_async_session] = lambda: db_session

    client = TestClient(app, raise_server_exceptions=True)

    yield client


@pytest_asyncio.fixture
async def mock_session() -> AsyncMock:
    """Возвращает простой MagicMock, имитирующий async‑SQLAlchemy сессию."""
    session = AsyncMock(spec=AsyncSession)

    session.get = AsyncMock(return_value=None)
    session.add = AsyncMock()

    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()

    session.execute = AsyncMock()

    return session


@pytest_asyncio.fixture(scope='function')
async def db_engine():
    """Тестовый движок для БД в RAM."""
    engine = create_async_engine(
        url='sqlite+aiosqlite:///:memory:',
        future=True
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope='function')
async def db_session(db_engine) -> AsyncSession:
    """Создает асинхронную сессию с транзакцией и автоматическим откатом."""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )()

    await async_session.begin()

    yield async_session

    await async_session.rollback()
    await async_session.close()
