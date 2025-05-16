"""add_study_room_idddd

Revision ID: c207536b5eaf
Revises: d69aa9e70f73
Create Date: 2025-05-15 12:35:33.763494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c207536b5eaf'
down_revision: Union[str, None] = 'd69aa9e70f73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
