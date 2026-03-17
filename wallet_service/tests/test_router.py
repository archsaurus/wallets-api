"""Тесты роутера wallet_router."""
# region Imports
from contextlib import nullcontext
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_service.application import crud
from wallet_service.application.models import Wallet
from wallet_service.application.util import (
    MAX_AMOUNT,
    CreationFailedError,
    InvalidAmountError,
    WalletNotFoundError,
)

# endregion


# region Routes:
#    {'GET', 'HEAD'} /openapi.json
#    {'GET', 'HEAD'} /docs
#    {'GET', 'HEAD'} /docs/oauth2-redirect
#    {'GET', 'HEAD'} /redoc
#    {'GET'} /api/v1/wallets/{wallet_uuid}
#    {'POST'} /api/v1/wallets/{wallet_uuid}/operation
#    {'POST'} /api/v1/wallets/{wallet_uuid}/withdraw
#    {'POST'} /api/v1/wallets/{wallet_uuid}/deposit
#    {'POST'} /api/v1/wallets
#    {'DELETE'} /api/v1/wallets/{wallet_uuid}
# endregion


@pytest.mark.parametrize('route, expected_status', [
    ('/openapi.json', status.HTTP_200_OK),
    ('/docs', status.HTTP_200_OK),
    ('/docs/oauth2-redirect', status.HTTP_200_OK),
    ('/redoc', status.HTTP_200_OK),
])
def test_api_accessable(route, expected_status, async_client: TestClient):
    assert async_client.get(route).status_code == expected_status
    assert async_client.head(route).status_code == expected_status


# region 'GET' /api/v1/wallets/{wallet_uuid}
@pytest.mark.asyncio
async def test_get_wallet_success(
    async_client: TestClient,
    db_session: AsyncSession,
):
    wallet_uuid = uuid4()

    wallet = await crud.create_wallet(db_session, wallet_uuid)

    response = async_client.get(f'/api/v1/wallets/{wallet.uuid}')
    response_data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_data['uuid'] == str(wallet_uuid)
    assert response_data['balance'] == str(wallet.balance)


@pytest.mark.asyncio
async def test_get_wallet_not_found(
    async_client: TestClient,
    db_session: AsyncSession,
):
    wallet_uuid_404 = uuid4()

    with pytest.raises(WalletNotFoundError):
        async_client.get(f'/api/v1/wallets/{wallet_uuid_404}')

# endregion


# region 'POST' /api/v1/wallets
@pytest.mark.asyncio
async def test_create_wallet_success(async_client: TestClient):
    response = async_client.post('/api/v1/wallets/')
    response_data = response.json()

    assert response.status_code == 201
    assert response_data['balance'] == '0.00'


@pytest.mark.asyncio
async def test_create_wallet_failed(
    async_client: TestClient,
    db_session: AsyncSession
):
    existing_uuid = uuid4()

    await crud.create_wallet(db_session, existing_uuid)
    await db_session.commit()

    with patch('uuid.uuid4', return_value=existing_uuid):
        with pytest.raises(CreationFailedError):
            response = async_client.post('/api/v1/wallets/')

            assert \
                response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert 'генерации/ингетрации' in response.json()['detail']

# endregion


# region 'POST' /api/v1/wallets/{wallet_uuid}
@pytest.mark.asyncio
async def test_deposit_success(async_client: TestClient):
    create_response = async_client.post('/api/v1/wallets/')

    wallet_uuid = create_response.json()['uuid']

    response = async_client.post(
        f'/api/v1/wallets/{wallet_uuid}/deposit',
        params={
            'wallet_uuid': wallet_uuid,
            'amount': '50.00'
        }
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()['balance'] == '50.00'


@pytest.mark.asyncio
async def test_withdraw_success(async_client: TestClient):
    create_response = async_client.post('/api/v1/wallets/')

    wallet_uuid = create_response.json()['uuid']

    async_client.post(
        f'/api/v1/wallets/{wallet_uuid}/deposit',
        params={
            'wallet_uuid': wallet_uuid,
            'amount': '50.00'
        }
    )

    async_client.post(
        f'/api/v1/wallets/{wallet_uuid}/withdraw',
        params={
            'wallet_uuid': wallet_uuid,
            'amount': '30.00'
        }
    )


@pytest.mark.parametrize(
    'initial_balance, operation_amount, cm, expected_status', [
        ('0.00', '1000.00', nullcontext(), status.HTTP_202_ACCEPTED),
        (
            '10.00', '100000000.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции превышает установленный лимит'
            ), None
        ),
        (
            '100.00', '-100.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции должна быть положительной'
                ), None
        ),
    ]
)
@pytest.mark.asyncio
async def test_deposit_invalid_amount(
    initial_balance,
    operation_amount,
    cm,
    expected_status,
    async_client: TestClient,
):
    wallet_uuid = async_client.post('/api/v1/wallets/').json()['uuid']

    if Decimal(initial_balance) != Decimal('0.00'):
        async_client.post(
            f'/api/v1/wallets/{wallet_uuid}/deposit',
            params={
                'wallet_uuid': wallet_uuid,
                'amount': initial_balance
            }
        )

    with cm:
        async_client.post(
            f'/api/v1/wallets/{wallet_uuid}/deposit',
            params={
                'wallet_uuid': wallet_uuid,
                'amount': operation_amount
            }
        )


@pytest.mark.parametrize(
    'initial_balance, operation_amount, cm, expected_status', [
        (
            '1000.00', '00.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции должна быть положительной'
            ), None
        ),
        (
            '2000000.00', '1000001.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции превышает установленный лимит'
            ), None
        ),
        (
            '10.00', '10000.00',
            pytest.raises(
                InvalidAmountError,
                match='Недостаточно средств'
            ), None
        ),
        (
            '1000.00', -100.00,
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции должна быть положительной'
                ), None
        ),
    ]
)
@pytest.mark.asyncio
async def test_withdraw_invalid_amount(
    initial_balance,
    operation_amount,
    cm,
    expected_status,
    async_client: TestClient,
):
    wallet_uuid = async_client.post('/api/v1/wallets/').json()['uuid']

    initial_balance = Decimal(initial_balance)
    if initial_balance != 0:
        # Я прекрасно понимаю абсурдность такого способа задания начального
        # баланса. Однако, сумма операции ограничена на уровне crud-модуля,
        # потому, по крайней мере, пока что, оно останется здесь в таком виде.
        # Кстати говоря, прогон ВСЕХ тестов из-за этого
        # становмтся ВДВОЕ медленнее :(
        if initial_balance > MAX_AMOUNT:
            quotient = initial_balance // MAX_AMOUNT
            remainder = initial_balance % MAX_AMOUNT

            for _ in range(int(quotient)):
                async_client.post(
                    f'/api/v1/wallets/{wallet_uuid}/deposit',
                    params={'wallet_uuid': wallet_uuid, 'amount': MAX_AMOUNT}
                )

            if remainder > 0:
                async_client.post(
                    f'/api/v1/wallets/{wallet_uuid}/deposit',
                    params={'wallet_uuid': wallet_uuid, 'amount': remainder}
                )

        else:
            async_client.post(
                f'/api/v1/wallets/{wallet_uuid}/deposit',
                params={
                    'wallet_uuid': wallet_uuid,
                    'amount': initial_balance
                }
            )

    with cm:
        async_client.post(
            f'/api/v1/wallets/{wallet_uuid}/withdraw',
            params={
                'wallet_uuid': wallet_uuid,
                'amount': operation_amount
            }
        )


@pytest.mark.parametrize(
    'operation_type, initial_balance, operation_amount, cm, expected_status', [
        (
            'DEPOSIT', '0.00', '1000.00',
            nullcontext(), status.HTTP_202_ACCEPTED
        ),
        (
            'DEPOSIT',  '0.00', '10000000.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции превышает установленный лимит'
            ), None
        ),
        (
            'DEPOSIT',  '0.00', '-10.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции должна быть положительной'
                ), None
        ),
        (
            'WITHDRAW', '0.00', 'AGFa',
            nullcontext(), status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        (
            'WITHDRAW', '0.00', '1000.00',
            pytest.raises(
                InvalidAmountError,
                match='Недостаточно средств'
            ),
            None
        ),
        (
            'WITHDRAW', '0.00', '-10.00',
            pytest.raises(
                InvalidAmountError,
                match='Сумма операции должна быть положительной'
            ), None
        ),
        (
            'TAKEAWAY', '0.00', '1000.00',
            nullcontext(),
            status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
    ]
)
@pytest.mark.asyncio
async def test_general_operation(
    operation_type,
    initial_balance,
    operation_amount,
    cm,
    expected_status,
    async_client: TestClient
):
    with cm:
        wallet_uuid = async_client.post('/api/v1/wallets/').json()['uuid']

        if Decimal(initial_balance) != Decimal('0.00'):
            async_client.post(
                f'/api/v1/wallets/{wallet_uuid}/operation',
                params={
                    'wallet_uuid': wallet_uuid,
                    'operation_type': 'DEPOSIT',
                    'amount': initial_balance
                }
            )

        response = async_client.post(
            f'/api/v1/wallets/{wallet_uuid}/operation',
            params={
                'wallet_uuid': wallet_uuid,
                'operation_type': operation_type,
                'amount': operation_amount
            }
        )

        assert response.status_code == expected_status

# endregion


# region 'DELETE' /api/v1/wallets/{wallet_uuid}
@pytest.mark.asyncio
async def test_delete_wallet_success(
    async_client: TestClient,
    db_session: AsyncSession
):
    create_response = async_client.post('/api/v1/wallets/')

    wallet_uuid = create_response.json()['uuid']

    deletion_response = async_client.delete(f'/api/v1/wallets/{wallet_uuid}')
    deletion_response_data = deletion_response.json()

    assert deletion_response.status_code == status.HTTP_200_OK
    assert deletion_response_data['uuid'] == wallet_uuid
    assert datetime.fromisoformat(
        deletion_response_data['timestamp']
    ) is not None


@pytest.mark.asyncio
async def test_delete_wallet_non_zero_balance(
    async_client: TestClient,
    db_session: AsyncSession,
    mock_wallet: callable
):
    create_response = async_client.post('/api/v1/wallets/')
    create_response_data = create_response.json()
    wallet = Wallet(
        uuid=UUID(create_response_data['uuid']),
        balance=Decimal(create_response_data['balance'])
    )
    wallet_uuid = str(wallet.uuid)

    async_client.post(
        f'/api/v1/wallets/{wallet_uuid}/operation',
        params={'operation_type': 'DEPOSIT', 'amount': '1000'}
    )

    with pytest.raises(InvalidAmountError):
        async_client.delete(f'/api/v1/wallets/{wallet_uuid}')


@pytest.mark.asyncio
async def test_delete_wallet_not_found(
    async_client: TestClient,
    mock_session: AsyncMock
):
    wallet_uuid = str(uuid4())

    with pytest.raises(WalletNotFoundError):
        async_client.delete(f'/api/v1/wallets/{wallet_uuid}')

# endregion
