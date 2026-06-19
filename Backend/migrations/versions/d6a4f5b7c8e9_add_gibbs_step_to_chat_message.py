"""add gibbs_step column to chat_message

Revision ID: d6a4f5b7c8e9
Revises: c5f3e4d6a7b8
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a4f5b7c8e9'
down_revision: Union[str, Sequence[str], None] = 'c5f3e4d6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.add_column(sa.Column('gibbs_step', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.drop_column('gibbs_step')
