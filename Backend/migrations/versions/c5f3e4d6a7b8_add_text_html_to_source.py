"""add text_html column to source

Revision ID: c5f3e4d6a7b8
Revises: b4e2d3c5f6a7
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5f3e4d6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b4e2d3c5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.add_column(sa.Column('text_html', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.drop_column('text_html')
