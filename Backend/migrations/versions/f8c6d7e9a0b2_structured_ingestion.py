"""structured ingestion: source summary/derived_meta, source_tag origin, drop tag_cluster

Revision ID: f8c6d7e9a0b2
Revises: e7b5a6c9d0f1
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8c6d7e9a0b2'
down_revision: Union[str, Sequence[str], None] = 'e7b5a6c9d0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Per-note structured metadata produced during ingest enrichment.
    with op.batch_alter_table('source') as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('derived_meta', sa.JSON(), nullable=True))

    # Tag provenance: existing rows are manual ("user") by definition.
    with op.batch_alter_table('source_tag') as batch_op:
        batch_op.add_column(
            sa.Column('origin', sa.String(length=20), nullable=False, server_default='user')
        )

    # Drop the legacy, unused tag_cluster table and its FK on tag.
    with op.batch_alter_table('tag') as batch_op:
        batch_op.drop_column('tag_cluster_id')
    op.drop_table('tag_cluster')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'tag_cluster',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    with op.batch_alter_table('tag') as batch_op:
        batch_op.add_column(sa.Column('tag_cluster_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('source_tag') as batch_op:
        batch_op.drop_column('origin')

    with op.batch_alter_table('source') as batch_op:
        batch_op.drop_column('derived_meta')
        batch_op.drop_column('summary')
