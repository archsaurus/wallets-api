from decimal import Decimal

import pytest

from wallet_service.application.util import (
    MAX_AMOUNT,
    InvalidAmountError,
    validate_amount,
)


@pytest.mark.parametrize(
    'amount, expected', [
        (10, Decimal('10.0')),
        (10.00, Decimal('10.0')),
        ('10.0', Decimal('10.0')),
        ('10', Decimal('10.0'))
    ]
)
def test_amaount_validation(amount, expected):
    assert validate_amount(amount) == expected


@pytest.mark.parametrize(
    'amount, exception_type, msg_part', [
        pytest.param(
            'AOIGUHnqiwong-391tiuj931', TypeError, 'должна быть числом',
            id='not-a-number'
        ),
        pytest.param(
            '0', InvalidAmountError, 'должна быть положительной',
            id='zero-amount-as-string'
        ),
        pytest.param(
            0, InvalidAmountError, 'должна быть положительной',
            id='zero-amount-as-int'
        ),
        pytest.param(
            MAX_AMOUNT*2, InvalidAmountError, 'превышает',
            id='exceeds-max-amount'
        ),
    ]
)
def test_validate_amount_exceptions(amount, exception_type, msg_part):
    with pytest.raises(exception_type, match=msg_part):
        validate_amount(amount)
