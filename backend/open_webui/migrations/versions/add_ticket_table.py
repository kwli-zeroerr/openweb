"""Add ticket table

Revision ID: add_ticket_table
Revises: af906e964978
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_ticket_table'
down_revision = 'af906e964978'
branch_labels = None
depends_on = None


def upgrade():
    # Create ticket table
    op.create_table('ticket',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('user_name', sa.String(), nullable=False),
        sa.Column('user_email', sa.String(), nullable=False),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('assigned_to_name', sa.String(), nullable=True),
        sa.Column('task_requirements', sa.Text(), nullable=True),
        sa.Column('completion_criteria', sa.Text(), nullable=True),
        sa.Column('task_deadline', sa.BigInteger(), nullable=True),
        sa.Column('task_priority', sa.String(), nullable=True),
        sa.Column('required_files', sa.Text(), nullable=True),
        sa.Column('required_text', sa.Text(), nullable=True),
        sa.Column('required_images', sa.Text(), nullable=True),
        sa.Column('delivery_instructions', sa.Text(), nullable=True),
        sa.Column('delivery_files', sa.Text(), nullable=True),
        sa.Column('delivery_text', sa.Text(), nullable=True),
        sa.Column('delivery_images', sa.Text(), nullable=True),
        sa.Column('completion_status', sa.String(), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=True),
        sa.Column('source_feedback_id', sa.String(), nullable=True),
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.Column('resolved_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('ticket')

