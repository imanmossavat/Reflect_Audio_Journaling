"""add sources column to chat_message

Revision ID: e7b5a6c9d0f1
Revises: d6a4f5b7c8e9
Create Date: 2026-06-19 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b5a6c9d0f1'
down_revision: Union[str, Sequence[str], None] = 'd6a4f5b7c8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.add_column(sa.Column('sources', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.drop_column('sources')
