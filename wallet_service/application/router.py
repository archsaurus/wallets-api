"""Основной маршрутизатор сервиса."""

# region Imports
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_service.application.crud import (
    create_wallet,
    delete_wallet,
    get_wallet,
    update_wallet_balance,
)
from wallet_service.application.database import get_async_session
from wallet_service.application.models import Wallet
from wallet_service.application.schemas import (
    DeletionResponse,
    OperationType,
    WalletResponse,
)
from wallet_service.application.util import (
    MAX_AMOUNT,
    CreationFailedError,
    InvalidAmountError,
    NotImplementedOperationError,
    WalletNotFoundError,
    validate_amount,
)

# endregion


ROUTER_LEVEL_ALLOWED_UPDATE_OPTIONS = frozenset({
    OperationType.WITHDRAW,
    OperationType.DEPOSIT
})


wallet_router = APIRouter(prefix='/api/v1/wallets')


async def get_wallet_or_404(
    session: AsyncSession,
    wallet_uuid: uuid.UUID
) -> Wallet:
    wallet = await get_wallet(
        wallet_uuid=wallet_uuid,
        session=session
    )

    if not wallet:
        raise WalletNotFoundError('Кошелёк не найден')

    return wallet


@wallet_router.get(
    '/{wallet_uuid}',
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {'description': 'Кошелек не найден'}
    }
)
async def get_wallet_balance(
    wallet_uuid: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> WalletResponse:
    """Получить информацию о кошельке."""
    return await get_wallet_or_404(session, uuid.UUID(wallet_uuid))


async def perform_operation(
    wallet_uuid: uuid.UUID,
    operation_type: OperationType,
    amount: Decimal,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> WalletResponse:
    """Реализация обработчка операций изменения баласна по заданию."""
    if operation_type not in ROUTER_LEVEL_ALLOWED_UPDATE_OPTIONS:
        raise NotImplementedOperationError(
            f'Операция {operation_type} запрещена'
            ' на уровне маршрутизатора приложения'
        )

    wallet = await get_wallet_or_404(session, uuid.UUID(wallet_uuid))

    amount = validate_amount(amount)

    try:
        await update_wallet_balance(
            session, wallet.uuid, amount, operation_type
        )

        return WalletResponse(
            uuid=wallet.uuid,
            balance=wallet.balance
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Сумма должна быть '
            f'положительным числом меньше {MAX_AMOUNT}'
        ) from exc


@wallet_router.post(
    '/{wallet_uuid}/operation',
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            'description': 'Кошелек не найден'
        },
        status.HTTP_409_CONFLICT: {
            'description': 'Сумма операции должна быть положительной'
        }
    }
)
async def restless_post_operation(
    wallet_uuid: str,
    operation_type: OperationType,
    amount: Decimal,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> WalletResponse:
    """Реализация обработчка операций изменения баласна по заданию."""
    return await perform_operation(
        wallet_uuid, operation_type, amount, session
    )


@wallet_router.post(
    '/{wallet_uuid}/withdraw',
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            'description': 'Кошелек не найден'
        },
        status.HTTP_409_CONFLICT: {
            'description': 'Сумма операции должна быть положительной'
        }
    }
)
async def perform_withdraw(
    wallet_uuid: str,
    amount: Decimal,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> WalletResponse:
    """Списание средств со счёта."""
    return await perform_operation(
        wallet_uuid=wallet_uuid,
        operation_type=OperationType.WITHDRAW,
        amount=amount,
        session=session
    )


@wallet_router.post(
    '/{wallet_uuid}/deposit',
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_404_NOT_FOUND: {
            'description': 'Кошелек не найден'
        },
        status.HTTP_409_CONFLICT: {
            'description': 'Сумма операции должна быть положительной'
        }
    }
)
async def perform_deposit(
    wallet_uuid: str,
    amount: Decimal,
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> WalletResponse:
    """Зачисление средств на счёт."""
    return await perform_operation(
        wallet_uuid=wallet_uuid,
        operation_type=OperationType.DEPOSIT,
        amount=amount,
        session=session
    )


@wallet_router.post(
    '',
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            'description': 'Ошибка генерации/ингетрации записи UUID'
        },
    }
)
async def perform_creation(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> WalletResponse:
    """Создать новый кошелёк с нулевым балансом."""
    try:
        wallet = await create_wallet(
            wallet_uuid=uuid.uuid4(),
            session=session
        )

        if wallet is None:
            raise CreationFailedError('Кошелёк с таким UUID уже существует')

        return WalletResponse(
            uuid=wallet.uuid,
            balance=wallet.balance
        )

    except Exception as exc:
        raise CreationFailedError(
            'Ошибка генерации/ингетрации записи UUID'
        ) from exc


@wallet_router.delete(
    path='/{wallet_uuid}',
    response_model=DeletionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            'description': 'Кошелек не найден'
        },
        status.HTTP_409_CONFLICT: {
            'description': 'Баланс должен быть нулевым'
        }
    }
)
async def perform_deletion(
    wallet_uuid: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DeletionResponse:
    """Удалить кошелёк"""
    wallet = await get_wallet_or_404(session, uuid.UUID(wallet_uuid))

    if wallet.balance != Decimal('0.0'):
        raise InvalidAmountError('Баланс должен быть нулевым')

    await delete_wallet(
        wallet_uuid=uuid.UUID(wallet_uuid),
        session=session
    )

    return DeletionResponse(uuid=wallet_uuid, timestamp=datetime.now())
