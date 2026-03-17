"""Модуль вспомогательных функций"""

# region Imports
from decimal import Decimal, InvalidOperation
from typing import Any

# endregion


MAX_AMOUNT = Decimal('1000000.00')  # Максимальная сумма операции


# region Exceptions
class WalletError(Exception):
    ...


class WalletNotFoundError(WalletError):
    ...


class InvalidAmountError(Exception):
    ...


class DatabaseOperationalError(Exception):
    ...


class CreationFailedError(WalletError):
    ...


class NotImplementedOperationError(WalletError):
    ...

# endregion


def validate_amount(amount: Any) -> Decimal:
    """Проверяет, что сумма операции, - amount, - положительное число,
        не превышающее верхнюю границу MAX_AMOUNT типа Decimal
        или приводимо к нему.

        Returns:
            Decimal: приведённая к целевому типу сумма операции.
        Raises:
            TypeError: тип данных не является приводимым к Decimal.
            InvalidAmountError: сумма операции не является положительной.
            InvalidAmountError: сумма операции выше установленного лимита.
    """
    try:
        dec = Decimal(str(amount))
    except (InvalidOperation, TypeError) as exc:
        raise TypeError('Сумма операции должна быть числом') from exc

    if dec <= 0:
        raise InvalidAmountError(
            'Сумма операции должна быть положительной'
        )

    if dec > MAX_AMOUNT:
        raise InvalidAmountError(
            'Сумма операции превышает установленный лимит'
        )

    return dec.quantize(Decimal('0.01'))
