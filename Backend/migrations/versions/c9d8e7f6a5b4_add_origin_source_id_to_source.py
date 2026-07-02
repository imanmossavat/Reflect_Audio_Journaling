"""add origin_source_id column to source

Revision ID: c9d8e7f6a5b4
Revises: d8f2a4c6b1e3
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d8e7f6a5b4'
down_revision: Union[str, Sequence[str], None] = 'd8f2a4c6b1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.add_column(sa.Column('origin_source_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.drop_column('origin_source_id')
