"""journal text made nullable for non processed upload

Revision ID: 43a1a25a9495
Revises: 7bb8a711c1a6
Create Date: 2026-03-23 15:27:39.206757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43a1a25a9495'
down_revision: Union[str, Sequence[str], None] = '7bb8a711c1a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('journal', sa.Column('text_new', sa.TEXT(), nullable=True))
    op.drop_column('journal', 'text')
    op.alter_column('journal', 'text_new', new_column_name='text')


def downgrade() -> None:
    op.add_column('journal', sa.Column('text_new', sa.TEXT(), nullable=False, server_default=''))
    op.drop_column('journal', 'text')
    op.alter_column('journal', 'text_new', new_column_name='text')
