"""add_deliver_completed_images_and_contactinfo

Revision ID: 57c4687b492d
Revises: a8b7c9d0e1f2
Create Date: 2025-12-20 01:04:47.690647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '57c4687b492d'
down_revision: Union[str, Sequence[str], None] = 'a8b7c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add deliver_image and completed_image to orders table
    op.add_column('orders', sa.Column('deliver_image', sa.JSON(), nullable=True))
    op.add_column('orders', sa.Column('completed_image', sa.JSON(), nullable=True))

    # Add contactinfo to users table
    op.add_column('users', sa.Column('contactinfo', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'contactinfo')
    op.drop_column('orders', 'completed_image')
    op.drop_column('orders', 'deliver_image')
