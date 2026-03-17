"""Модуль приложения."""
#!/usr/bin/env python3

# region Imports

from decimal import Decimal

from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException

from wallet_service.application.router import wallet_router
from wallet_service.application.util import (
    CreationFailedError,
    DatabaseOperationalError,
    InvalidAmountError,
    WalletError,
    WalletNotFoundError,
)

# endregion


wallet_application = FastAPI(
    title='Wallet Service',
    description='API для управления кошельками',
    version='1.0.0',
    json_encoders={Decimal: lambda d: float(d) if d else 0.0}
)


wallet_application.include_router(wallet_router)



# region Exception handlers

# TODO: Позднее доделаю до адекватного
# вида (ну хотя бы до маппинга по status_code)


@wallet_application.exception_handler(WalletNotFoundError)
async def wallet_not_found_handler(request, exc: WalletNotFoundError):
    """Обработчик ошибки обнаружения кошелька"""
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail='Кошелёк не найден'
    )


@wallet_application.exception_handler(WalletError)
async def wallet_error_handler(request, exc: WalletError):
    """Обработчик ошибок кошелька"""
    exc_content = str(exc).lower()

    if 'уже существует' in exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc) from exc

    elif 'не удалось создать' in exc_content:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, exc
        ) from exc


@wallet_application.exception_handler(InvalidAmountError)
async def invalid_amount_handler(request, exc: InvalidAmountError):
    """Обработчик ошибок суммы операции"""
    exc_content = str(exc).lower()

    if 'недостаточно средств' in exc_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    elif '' in exc_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@wallet_application.exception_handler(DatabaseOperationalError)
async def operational_error_handler(request, exc: DatabaseOperationalError):
    """Обработчик ошибок взаимодействия с базой данных"""
    exc_content = str(exc).lower()

    if 'кошелёк заблокирован' in exc_content:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Кошелёк заблокирован, повторите запрос позже'
        ) from exc

    elif 'неизвестныый тип' in exc_content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc)

    elif 'изменён другим запросом' in exc_content:
        raise HTTPException(
            status.HTTP_409_CONFLICT, exc
        )


@wallet_application.exception_handler(CreationFailedError)
async def creation_error_handler(request, exc: CreationFailedError):
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, exc) from exc
# endregion
