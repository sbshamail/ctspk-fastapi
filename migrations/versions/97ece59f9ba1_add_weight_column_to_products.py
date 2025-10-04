"""add weight column to products

Revision ID: 97ece59f9ba1
Revises: eb5070f02930
Create Date: 2025-10-04 13:18:55.643276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97ece59f9ba1'
down_revision: Union[str, Sequence[str], None] = 'eb5070f02930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("products", sa.Column("weight", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "weight")
