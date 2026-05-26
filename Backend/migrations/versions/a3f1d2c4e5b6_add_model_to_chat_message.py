"""add model column to chat_message

Revision ID: a3f1d2c4e5b6
Revises: 702551264b82
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1d2c4e5b6'
down_revision: Union[str, Sequence[str], None] = '702551264b82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.add_column(sa.Column('model', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('chat_message') as batch_op:
        batch_op.drop_column('model')
