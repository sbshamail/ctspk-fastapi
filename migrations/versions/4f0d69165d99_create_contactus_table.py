"""create contactus table

Revision ID: 4f0d69165d99
Revises: e548e5dce841
Create Date: 2025-11-26 13:39:43.842786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '4f0d69165d99'
down_revision: Union[str, Sequence[str], None] = 'e548e5dce841'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('contactus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('message', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('category', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Indexes for better query performance
        sa.Index('ix_contactus_name', 'name'),
        sa.Index('ix_contactus_email', 'email'),
        sa.Index('ix_contactus_is_processed', 'is_processed'),
        sa.Index('ix_contactus_created_at', 'created_at')
    )

    # Composite index for filtering unprocessed contacts
    op.create_index('idx_contactus_processed_created', 'contactus', ['is_processed', 'created_at'])

    # Full-text search index for search functionality
    op.execute("""
        CREATE INDEX idx_contactus_search_fts ON contactus
        USING gin(to_tsvector('english',
            COALESCE(name, '') || ' ' ||
            COALESCE(email, '') || ' ' ||
            COALESCE(subject, '') || ' ' ||
            COALESCE(message, '') || ' ' ||
            COALESCE(category, '')
        ))
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_contactus_search_fts', table_name='contactus')
    op.drop_index('idx_contactus_processed_created', table_name='contactus')
    op.drop_table('contactus')
