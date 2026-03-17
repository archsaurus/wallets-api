""" Модуль CRUD-операций взаимодействия с целевой базой данных."""

# region Imports
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_service.application.models import Wallet
from wallet_service.application.schemas import OperationType
from wallet_service.application.util import (
    DatabaseOperationalError,
    InvalidAmountError,
    WalletError,
    WalletNotFoundError,
    validate_amount,
)

# endregion

_ALLOWED_UPDATE_OPTIONS = frozenset({
    OperationType.WITHDRAW,
    OperationType.DEPOSIT
})

# region Retries
MAX_RETRIES = 3
RETRY_DELAY = 0.1


async def _with_retry[T](fn: Callable[..., Awaitable[T]], *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await fn(*args, **kwargs)

        except OperationalError:
            if attempt == MAX_RETRIES:
                raise

            await asyncio.sleep(RETRY_DELAY * attempt)
# endregion


# region CRUD
async def _get_wallet_for_update(
    session: AsyncSession,
    wallet_uuid: UUID,
) -> Wallet:
    """Возвращает обёртку кошелька под row‑level lock'ом.

        Returns:
            Wallet: DTO запрашиваемого кошелька

        Raises:
            WalletNotFoundError: Если запись не найдена
    """
    stmt = (
        select(Wallet)
        .where(Wallet.uuid == wallet_uuid)
        .with_for_update(nowait=False)  # SELECT FOR UPDATE
        #                                 без обработки deadlock'ов
    )

    result = await session.execute(stmt)

    wallet = result.scalar_one_or_none()

    if wallet is None:
        raise WalletNotFoundError(f'Кошелёк {wallet_uuid} не найден')

    return wallet


async def create_wallet(
    session: AsyncSession,
    wallet_uuid: UUID,
) -> Wallet:
    """Атомарно создаёт новый кошелёк с нулевым балансом."""
    try:
        wallet = Wallet(uuid=wallet_uuid, balance=Decimal('0.00'))

        session.add(wallet)

        await session.flush()
        await session.refresh(wallet)

        await session.commit()
        return wallet

    except IntegrityError as exc:
        raise WalletError(f'Кошелёк {wallet_uuid} уже существует') from exc

    except SQLAlchemyError as exc:
        raise WalletError('Не удалось создать кошелёк') from exc


async def get_wallet(
    session: AsyncSession,
    wallet_uuid: UUID
) -> Wallet:
    """Возвращает объект Wallet или None."""
    return await session.get(Wallet, wallet_uuid)


async def update_wallet_balance(
    session: AsyncSession,
    wallet_uuid: UUID,
    amount: Decimal,
    operation_type: OperationType
) -> Wallet:
    """Безопасно (атомарно + plock) изменяет текущий баланс кошелька.

        Returns:
            Wallet: обёртка созданного кошелька
        Raises:
            InvalidAmountError: Недостаточно средств
            NotImplementedError: Неизвестная операция или операция ещё не \
                реализована.
    """
    if operation_type not in _ALLOWED_UPDATE_OPTIONS:
        raise DatabaseOperationalError(
            f'Неизвестный тип операции {operation_type}'
        )

    valid_amount = validate_amount(amount)

    try:
        wallet = await _with_retry(
            _get_wallet_for_update,
            session,
            wallet_uuid
        )

    except OperationalError as exc:
        raise DatabaseOperationalError(
            'Кошелёк заблокирован, повторите запрос позже'
        ) from exc

    match operation_type:
        case OperationType.DEPOSIT:
            wallet.balance += valid_amount

        case OperationType.WITHDRAW:
            if wallet.balance < valid_amount:
                raise InvalidAmountError('Недостаточно средств')

            wallet.balance -= valid_amount

        case _:
            raise NotImplementedError(
                f'Операция типа {operation_type!r} ещё не реализована'
            )

    await session.flush()
    await session.refresh(wallet)
    await session.commit()

    return wallet


async def delete_wallet(
    session: AsyncSession,
    wallet_uuid: UUID,
    require_zero_balance: bool = True,
) -> Any:
    """Безопасно (атомарно + plock) удаляет кошельёк.

        Raises:
            InvalidAmountError: \
                При противоречии бизнес-логике (ненулевой баланс).
            DatabaseOperationalError: \
                Кошелёк в обработке другим запросом на момент попытки удаления.
    """
    wallet = await _get_wallet_for_update(session, wallet_uuid)

    if require_zero_balance and wallet.balance != Decimal('0'):
        raise InvalidAmountError(
            f'Баланс кошелька {wallet_uuid} не нулевой: ({wallet.balance})'
        )

    if require_zero_balance:
        del_stmt = delete(Wallet).where(
            Wallet.uuid == wallet_uuid,
            Wallet.balance == Decimal('0')
        )
    else:
        del_stmt = delete(Wallet).where(Wallet.uuid == wallet_uuid)

    result = await session.execute(del_stmt)
    if result.rowcount == 0:
        raise DatabaseOperationalError(
            'Кошелёк был изменён другим запросом, удаление отменено'
        )

    await session.commit()
    return result
# endregion
