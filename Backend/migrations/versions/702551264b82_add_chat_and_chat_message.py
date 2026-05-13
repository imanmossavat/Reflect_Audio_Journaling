"""add chat and chat_message

Revision ID: 702551264b82
Revises: 30c3e3b5293a
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '702551264b82'
down_revision: Union[str, Sequence[str], None] = '30c3e3b5293a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'chat_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('scale_value', sa.Integer(), nullable=True),
        sa.Column('scale_max', sa.Integer(), nullable=True),
        sa.Column('scale_low_label', sa.String(), nullable=True),
        sa.Column('scale_high_label', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('chat_message')
    op.drop_table('chat')
