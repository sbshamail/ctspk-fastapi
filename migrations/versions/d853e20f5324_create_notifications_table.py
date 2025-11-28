"""create notifications table

Revision ID: d853e20f5324
Revises: 6c7a7a59a0c4
Create Date: 2025-11-27 21:58:49.855322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd853e20f5324'
down_revision: Union[str, Sequence[str], None] = '6c7a7a59a0c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('message', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Key
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),

        # Indexes for better query performance
        sa.Index('ix_notifications_user_id', 'user_id'),
        sa.Index('ix_notifications_is_read', 'is_read'),
        sa.Index('ix_notifications_sent_at', 'sent_at'),
        sa.Index('ix_notifications_created_at', 'created_at')
    )

    # Composite index for filtering unread notifications by user
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', 'is_read', 'sent_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_notifications_user_unread', table_name='notifications')
    op.drop_table('notifications')
