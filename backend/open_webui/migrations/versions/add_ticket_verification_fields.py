"""Add verification_score and verification_checklist to ticket table

Revision ID: add_ticket_verification_fields
Revises: add_knowledge_log_table
Create Date: 2025-11-05 09:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_ticket_verification_fields'
down_revision = 'add_knowledge_log_table'
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
    
    # Add verification_score if it doesn't exist
    if not _has_column(bind, "ticket", "verification_score"):
        op.add_column("ticket", sa.Column("verification_score", sa.Integer(), nullable=True))
    
    # Add verification_checklist if it doesn't exist
    # In SQLite, JSONField is stored as TEXT
    if not _has_column(bind, "ticket", "verification_checklist"):
        op.add_column("ticket", sa.Column("verification_checklist", sa.Text(), nullable=True))


def downgrade():
    # Safe no-op: column removal is optional and can break on SQLite
    pass

