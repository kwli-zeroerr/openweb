"""Add is_default_for_all_users column to tool table

Revision ID: add_tool_default_for_all_users
Revises: add_knowledge_log_table
Create Date: 2025-11-06 20:55:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_tool_default_for_all_users'
down_revision = 'add_ticket_verification_fields'
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        inspector = inspect(bind)
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    
    # Add is_default_for_all_users if it doesn't exist
    # Use Boolean type, default to False
    if not _has_column(bind, "tool", "is_default_for_all_users"):
        # For SQLite, Boolean is stored as INTEGER (0 or 1)
        # For PostgreSQL and others, Boolean is native
        op.add_column("tool", sa.Column("is_default_for_all_users", sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    # Safe no-op: column removal is optional and can break on SQLite
    pass

