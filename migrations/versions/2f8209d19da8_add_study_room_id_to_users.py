"""add_study_room_id_to_users

Revision ID: 2f8209d19da8
Revises: 1c4e34586a6a
Create Date: 2025-05-15 12:24:21.348036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f8209d19da8'
down_revision: Union[str, None] = '1c4e34586a6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
