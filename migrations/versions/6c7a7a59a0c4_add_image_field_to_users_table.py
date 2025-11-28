"""add image field to users table

Revision ID: 6c7a7a59a0c4
Revises: 4f0d69165d99
Create Date: 2025-11-27 20:53:01.987717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6c7a7a59a0c4'
down_revision: Union[str, Sequence[str], None] = '4f0d69165d99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('image', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'image')
