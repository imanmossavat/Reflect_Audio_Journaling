"""add reflection_scope column to chat

Revision ID: a3d9e2c1b4f7
Revises: f8c6b7d0e1a2
Create Date: 2026-06-23 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d9e2c1b4f7'
down_revision: Union[str, Sequence[str], None] = 'f8c6b7d0e1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat') as batch_op:
        batch_op.add_column(sa.Column('reflection_scope', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat') as batch_op:
        batch_op.drop_column('reflection_scope')
