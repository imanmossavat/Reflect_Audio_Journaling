"""from journal to source

Revision ID: 1f71e699b478
Revises: c1f4f1a2b3c4
Create Date: 2026-04-14 11:55:11.692950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f71e699b478'
down_revision: Union[str, Sequence[str], None] = 'c1f4f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "journal") and not _table_exists(inspector, "source"):
        op.rename_table("journal", "source")
        inspector = sa.inspect(bind)
    if _table_exists(inspector, "journal_tag") and not _table_exists(inspector, "source_tag"):
        op.rename_table("journal_tag", "source_tag")
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "source_tag", "journal_id") and not _column_exists(inspector, "source_tag", "source_id"):
        with op.batch_alter_table("source_tag") as batch_op:
            batch_op.alter_column(
                "journal_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="source_id",
            )
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "chunk", "journal_id") and not _column_exists(inspector, "chunk", "source_id"):
        with op.batch_alter_table("chunk") as batch_op:
            batch_op.alter_column(
                "journal_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="source_id",
            )
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "question", "journal_id") and not _column_exists(inspector, "question", "source_id"):
        with op.batch_alter_table("question") as batch_op:
            batch_op.alter_column(
                "journal_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="source_id",
            )
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "scale_question", "journal_id") and not _column_exists(inspector, "scale_question", "source_id"):
        with op.batch_alter_table("scale_question") as batch_op:
            batch_op.alter_column(
                "journal_id",
                existing_type=sa.Integer(),
                existing_nullable=True,
                new_column_name="source_id",
            )
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "scale_question"):
        with op.batch_alter_table("scale_question") as batch_op:
            batch_op.alter_column(
                "trigger_type",
                existing_type=sa.VARCHAR(length=100),
                nullable=False,
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "scale_question"):
        if _column_exists(inspector, "scale_question", "source_id") and not _column_exists(inspector, "scale_question", "journal_id"):
            with op.batch_alter_table("scale_question") as batch_op:
                batch_op.alter_column(
                    "source_id",
                    existing_type=sa.Integer(),
                    existing_nullable=True,
                    new_column_name="journal_id",
                )
            inspector = sa.inspect(bind)
        with op.batch_alter_table("scale_question") as batch_op:
            batch_op.alter_column(
                "trigger_type",
                existing_type=sa.VARCHAR(length=100),
                nullable=True,
            )

    if _column_exists(inspector, "question", "source_id") and not _column_exists(inspector, "question", "journal_id"):
        with op.batch_alter_table("question") as batch_op:
            batch_op.alter_column(
                "source_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="journal_id",
            )
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "chunk", "source_id") and not _column_exists(inspector, "chunk", "journal_id"):
        with op.batch_alter_table("chunk") as batch_op:
            batch_op.alter_column(
                "source_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="journal_id",
            )
        inspector = sa.inspect(bind)

    if _column_exists(inspector, "source_tag", "source_id") and not _column_exists(inspector, "source_tag", "journal_id"):
        with op.batch_alter_table("source_tag") as batch_op:
            batch_op.alter_column(
                "source_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
                new_column_name="journal_id",
            )
        inspector = sa.inspect(bind)

    if _table_exists(inspector, "source_tag") and not _table_exists(inspector, "journal_tag"):
        op.rename_table("source_tag", "journal_tag")
        inspector = sa.inspect(bind)
    if _table_exists(inspector, "source") and not _table_exists(inspector, "journal"):
        op.rename_table("source", "journal")
