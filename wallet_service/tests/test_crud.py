"""Модуль тестов CRUD-операций."""
# region Imports
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from wallet_service.application import crud
from wallet_service.application.schemas import OperationType
from wallet_service.application.util import (
    InvalidAmountError,
    WalletError,
    WalletNotFoundError,
)

# endregion


class TestGetWalletForUpdate:
    @pytest.mark.asyncio
    async def test_get_wallet_for_update_success(
        self, mock_session, mock_wallet
    ):
        mock_wallet = mock_wallet(10)

        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none = Mock(
            return_value=mock_wallet
        )

        mock_session.execute.return_value = mock_execute_result

        result = await crud._get_wallet_for_update(
            wallet_uuid=mock_wallet.uuid,
            session=mock_session
        )

        assert result == mock_wallet

    @pytest.mark.asyncio
    async def test_get_wallet_for_update_not_found(self, mock_session):
        wallet_uuid = uuid4()

        mock_execute_result = AsyncMock()
        mock_execute_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_execute_result

        with pytest.raises(WalletNotFoundError):
            await crud._get_wallet_for_update(
                wallet_uuid=wallet_uuid,
                session=mock_session
            )


class TestCreateWallet:
    @pytest.mark.asyncio
    async def test_create_wallet_success(self, mock_session, mock_wallet):
        mock_wallet = mock_wallet(0)

        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch(
            'wallet_service.application.models.Wallet',
            return_value=mock_wallet
        ):
            result = await crud.create_wallet(
                wallet_uuid=mock_wallet.uuid,
                session=mock_session
            )

            assert result.balance == mock_wallet.balance and \
                result.uuid == mock_wallet.uuid

    @pytest.mark.asyncio
    async def test_create_wallet_integrity_error(
        self, mock_session, mock_wallet
    ):
        mock_wallet = mock_wallet(0)

        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch(
            'wallet_service.application.models.Wallet',
            return_value=mock_wallet
        ):
            mock_session.flush.side_effect = IntegrityError(
                'duplicate', None, None
            )

            with pytest.raises(WalletError):
                await crud.create_wallet(mock_session, mock_wallet.uuid)


class GetWalletTest:
    @pytest.mark.asyncio
    async def test_get_wallet_exists_and_none(self, mock_session, mock_wallet):
        mock_wallet = mock_wallet(5)

        mock_session.get = AsyncMock(
            return_value=mock_wallet
        )

        wallet = await crud.get_wallet(mock_session, mock_wallet.uuid)

        assert wallet.uuid == mock_wallet.uuid

        mock_session.get = AsyncMock(return_value=None)
        wallet_none = await crud.get_wallet(mock_session, mock_wallet.uuid)

        assert wallet_none is None


class TestUpdateWallet:
    @pytest.mark.asyncio
    async def test_update_wallet_balance_deposit(
        self, mock_session, mock_wallet
    ):
        initial_wallet = mock_wallet(balance=10)

        with patch(
            'wallet_service.application.crud._with_retry',
            return_value=initial_wallet
        ):
            updated_wallet = await crud.update_wallet_balance(
                mock_session,
                initial_wallet.uuid,
                Decimal('5.00'),
                OperationType.DEPOSIT
            )

            assert updated_wallet.balance == Decimal('15.00')

    @pytest.mark.asyncio
    async def test_update_wallet_balance_withdraw_insufficient(
        self, mock_session, mock_wallet
    ):
        initial_wallet = mock_wallet(10)

        with patch(
            'wallet_service.application.crud._with_retry',
            return_value=initial_wallet
        ):
            with pytest.raises(InvalidAmountError):
                await crud.update_wallet_balance(
                    mock_session,
                    initial_wallet.uuid,
                    Decimal('20.00'),
                    OperationType.WITHDRAW
                )


class TestDeleteWallet:
    @pytest.mark.asyncio
    async def test_delete_wallet_success_zero_balance(
        self, mock_session, mock_wallet
    ):
        mock_wallet = mock_wallet(0)

        mock_session.execute.return_value.rowcount = 1

        with patch(
            'wallet_service.application.crud._get_wallet_for_update',
            return_value=mock_wallet
        ):
            result = await crud.delete_wallet(
                session=mock_session,
                wallet_uuid=mock_wallet.uuid
            )

            assert result.rowcount == 1

    @pytest.mark.asyncio
    async def test_delete_wallet_non_zero_balance(
        self, mock_session, mock_wallet
    ):
        mock_wallet = mock_wallet(balance=10)

        with patch(
            'wallet_service.application.crud._get_wallet_for_update',
            return_value=mock_wallet
        ):
            with pytest.raises(InvalidAmountError):
                await crud.delete_wallet(mock_session, mock_wallet.uuid)
