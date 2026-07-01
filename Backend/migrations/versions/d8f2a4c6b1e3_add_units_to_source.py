"""add units column to source

Revision ID: d8f2a4c6b1e3
Revises: c7e5f9a1b3d2
Create Date: 2026-07-01 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f2a4c6b1e3'
down_revision: Union[str, Sequence[str], None] = 'c7e5f9a1b3d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.add_column(sa.Column('units', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.drop_column('units')
