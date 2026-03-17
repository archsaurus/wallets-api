"""initial_setup

Revision ID: 8c17b8252e06
Revises: 4255cd2ee301
Create Date: 2026-03-14 01:05:49.250315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c17b8252e06'
down_revision: Union[str, Sequence[str], None] = '4255cd2ee301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
