"""Add new tables for architecture migration: file_version, knowledge_file_link, source_system

Revision ID: d3465c10ebfe
Revises: add_tool_default_for_groups
Create Date: 2025-11-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "d3465c10ebfe"
down_revision = "add_tool_default_for_groups"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    """Check if a table exists"""
    try:
        inspector = inspect(bind)
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    """Create three new tables for architecture migration"""
    bind = op.get_bind()
    
    # 1. Create file_version table (文件版本管理表)
    if not _table_exists(bind, "file_version"):
        op.create_table(
            "file_version",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("file_id", sa.String(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("meta", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        
        # Create index on file_id for faster lookups
        op.create_index(
            "ix_file_version_file_id",
            "file_version",
            ["file_id"],
            unique=False
        )
        
        # Create composite index on file_id and version_number
        op.create_index(
            "ix_file_version_file_id_version",
            "file_version",
            ["file_id", "version_number"],
            unique=False
        )
    
    # 2. Create knowledge_file_link table (知识库-文件关联表，N:M)
    if not _table_exists(bind, "knowledge_file_link"):
        op.create_table(
            "knowledge_file_link",
            sa.Column("knowledge_id", sa.String(), nullable=False),
            sa.Column("file_id", sa.String(), nullable=False),
            sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("knowledge_id", "file_id", name="pk_knowledge_file"),
        )
        
        # Create indexes for faster lookups
        op.create_index(
            "ix_knowledge_file_link_knowledge_id",
            "knowledge_file_link",
            ["knowledge_id"],
            unique=False
        )
        
        op.create_index(
            "ix_knowledge_file_link_file_id",
            "knowledge_file_link",
            ["file_id"],
            unique=False
        )
        
        # Create index on is_indexed for filtering indexed files
        op.create_index(
            "ix_knowledge_file_link_is_indexed",
            "knowledge_file_link",
            ["is_indexed"],
            unique=False
        )
    
    # 3. Create source_system table (外部系统溯源表)
    if not _table_exists(bind, "source_system"):
        op.create_table(
            "source_system",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("api_key_hash", sa.Text(), nullable=False),
            sa.Column("meta", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        
        # Create unique index on api_key_hash for lookups
        op.create_index(
            "ix_source_system_api_key_hash",
            "source_system",
            ["api_key_hash"],
            unique=True
        )
        
        # Create index on name for searching
        op.create_index(
            "ix_source_system_name",
            "source_system",
            ["name"],
            unique=False
        )


def downgrade():
    """Drop the three new tables"""
    bind = op.get_bind()
    
    # Drop indexes first, then tables
    
    # Drop source_system table
    if _table_exists(bind, "source_system"):
        op.drop_index("ix_source_system_name", table_name="source_system")
        op.drop_index("ix_source_system_api_key_hash", table_name="source_system")
        op.drop_table("source_system")
    
    # Drop knowledge_file_link table
    if _table_exists(bind, "knowledge_file_link"):
        op.drop_index("ix_knowledge_file_link_is_indexed", table_name="knowledge_file_link")
        op.drop_index("ix_knowledge_file_link_file_id", table_name="knowledge_file_link")
        op.drop_index("ix_knowledge_file_link_knowledge_id", table_name="knowledge_file_link")
        op.drop_table("knowledge_file_link")
    
    # Drop file_version table
    if _table_exists(bind, "file_version"):
        op.drop_index("ix_file_version_file_id_version", table_name="file_version")
        op.drop_index("ix_file_version_file_id", table_name="file_version")
        op.drop_table("file_version")

