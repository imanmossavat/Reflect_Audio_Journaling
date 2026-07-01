"""add provenance and verified columns to source

Revision ID: b6d4e5f7a9c1
Revises: a3d9e2c1b4f7
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d4e5f7a9c1'
down_revision: Union[str, Sequence[str], None] = 'a3d9e2c1b4f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.add_column(
            sa.Column('provenance', sa.String(length=30), nullable=False, server_default='direct')
        )
        batch_op.add_column(
            sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('source') as batch_op:
        batch_op.drop_column('verified')
        batch_op.drop_column('provenance')
