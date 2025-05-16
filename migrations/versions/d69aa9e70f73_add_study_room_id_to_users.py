"""add_study_room_id_to_users

Revision ID: d69aa9e70f73
Revises: 2f8209d19da8
Create Date: 2025-05-15 12:33:15.149233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd69aa9e70f73'
down_revision: Union[str, None] = '2f8209d19da8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
