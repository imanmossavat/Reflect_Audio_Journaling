"""add reflection_goal column to chat

Revision ID: f8c6b7d0e1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8c6b7d0e1a2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat') as batch_op:
        batch_op.add_column(sa.Column('reflection_goal', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat') as batch_op:
        batch_op.drop_column('reflection_goal')
