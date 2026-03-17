"""Модуль Pydantic-схем"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

# from warnings import deprecated
from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Перечисление допустимых типов операций изменения баланса кошелька."""
    DEPOSIT = 'DEPOSIT'
    WITHDRAW = 'WITHDRAW'


# @deprecated
class WalletOperation(BaseModel):
    """DTO информации об операции"""
    operation_type: OperationType
    amount: Decimal


class WalletResponse(BaseModel):
    """DTO кошелька под тела ответов на CRUD-операции."""
    uuid: UUID
    balance: Decimal

    class Config:  # pylint: disable=C0115
        from_attributes = True


class DeletionResponse(BaseModel):
    """DTO информации об удалении кошелька."""
    uuid: UUID
    timestamp: datetime

    class Config:  # pylint: disable=C0115
        from_attributes = True
