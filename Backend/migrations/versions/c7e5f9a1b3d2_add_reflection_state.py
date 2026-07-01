"""add reflection_state table

Revision ID: c7e5f9a1b3d2
Revises: b6d4e5f7a9c1
Create Date: 2026-07-01 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e5f9a1b3d2'
down_revision: Union[str, Sequence[str], None] = 'b6d4e5f7a9c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'reflection_state',
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.Column('focus', sa.JSON(), nullable=False),
        sa.Column('gist', sa.JSON(), nullable=False),
        sa.Column('open_thread', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ),
        sa.PrimaryKeyConstraint('chat_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('reflection_state')
