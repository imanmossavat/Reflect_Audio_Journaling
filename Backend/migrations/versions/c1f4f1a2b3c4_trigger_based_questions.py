"""trigger-based questions

Revision ID: c1f4f1a2b3c4
Revises: 9b959c7aec0d
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1f4f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "9b959c7aec0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("question", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trigger_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("trigger_context", sa.JSON(), nullable=True))

    with op.batch_alter_table("scale_question", schema=None) as batch_op:
        batch_op.add_column(sa.Column("journal_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("trigger_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("trigger_context", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scale_question_journal_id_journal",
            "journal",
            ["journal_id"],
            ["id"],
        )
        batch_op.drop_column("tag_cluster_id")
        batch_op.drop_column("is_active")

    # Legacy rows can not always be deterministically mapped.
    # Keep nullable during migration and enforce on write paths.
    op.execute("UPDATE scale_question SET trigger_type = 'legacy' WHERE trigger_type IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("scale_question", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
        batch_op.add_column(sa.Column("tag_cluster_id", sa.Integer(), nullable=True))
        batch_op.drop_constraint("fk_scale_question_journal_id_journal", type_="foreignkey")
        batch_op.drop_column("trigger_context")
        batch_op.drop_column("trigger_type")
        batch_op.drop_column("journal_id")

    with op.batch_alter_table("question", schema=None) as batch_op:
        batch_op.drop_column("trigger_context")
        batch_op.drop_column("trigger_type")
