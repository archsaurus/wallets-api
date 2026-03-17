"""Модуль базовых моделей для работы с API"""

import uuid
from decimal import Decimal

from sqlalchemy import UUID, Numeric
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class Wallet(Base):  # type: ignore
    """Базовое представление кошелька"""

    __tablename__ = 'wallets'

    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),  # Работает для PostgreSQL, но на SQLite умирает,
        #                    # т.к. в SQLite нет нативного типа UUID.
        #                    # Нашёл костыль - использовать String(36) вместо
        #                    # нормального UUID, иначе SQLA отчаянно пытается
        #                    # вызвать у строки метод hex.
        default=uuid.uuid4,
        primary_key=True
    )

    balance: Mapped[Numeric] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0.00'),
        nullable=False
    )
