"""Add knowledge_log table

Revision ID: add_knowledge_log_table
Revises: add_chat_id_to_feedback
Create Date: 2025-10-31

"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "add_knowledge_log_table"
down_revision = "add_chat_id_to_feedback"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("knowledge_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column("user_email", sa.String(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_id", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("knowledge_log")


