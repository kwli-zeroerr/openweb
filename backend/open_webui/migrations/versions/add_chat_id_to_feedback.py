"""Add chat_id column to feedback if missing

Revision ID: add_chat_id_to_feedback
Revises: add_ticket_table
Create Date: 2025-10-31

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# Revision identifiers, used by Alembic.
revision = "add_chat_id_to_feedback"
down_revision = "add_ticket_table"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    try:
        inspector = inspect(bind)
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    if not _has_column(bind, "feedback", "chat_id"):
        op.add_column("feedback", sa.Column("chat_id", sa.Text(), nullable=True))


def downgrade():
    # Safe no-op: column removal is optional and can break on SQLite
    pass


