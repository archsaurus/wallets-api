"""initial_setup

Revision ID: 7ffc6101ad13
Revises: 8c17b8252e06
Create Date: 2026-03-14 01:06:30.375148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ffc6101ad13'
down_revision: Union[str, Sequence[str], None] = '8c17b8252e06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
