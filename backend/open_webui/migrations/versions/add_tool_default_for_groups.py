"""Add default_for_group_ids column to tool table

Revision ID: add_tool_default_for_groups
Revises: add_tool_default_for_all_users
Create Date: 2025-01-XX XX:XX:XX.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'add_tool_default_for_groups'
down_revision = 'add_tool_default_for_all_users'
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
    
    # Add default_for_group_ids if it doesn't exist
    # Use JSON type to store array of group IDs
    if not _has_column(bind, "tool", "default_for_group_ids"):
        if bind.dialect.name == "sqlite":
            # SQLite uses TEXT for JSON
            op.add_column("tool", sa.Column("default_for_group_ids", sa.Text(), nullable=True, server_default="[]"))
        else:
            # PostgreSQL and others use JSON
            op.add_column("tool", sa.Column("default_for_group_ids", sa.JSON(), nullable=True, server_default="[]"))


def downgrade():
    # Safe no-op: column removal is optional and can break on SQLite
    pass

