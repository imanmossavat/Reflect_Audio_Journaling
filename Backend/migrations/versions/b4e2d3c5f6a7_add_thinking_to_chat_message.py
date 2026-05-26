"""add thinking column to chat_message

Revision ID: b4e2d3c5f6a7
Revises: a3f1d2c4e5b6
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e2d3c5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a3f1d2c4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.add_column(sa.Column('thinking', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.drop_column('thinking')
