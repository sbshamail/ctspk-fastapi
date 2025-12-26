"""add_actual_amount_to_orders

Revision ID: 3be62b095b1a
Revises: 8ddb41b78bfc
Create Date: 2025-12-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3be62b095b1a'
down_revision: Union[str, Sequence[str], None] = '8ddb41b78bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add actual_amount column to orders table
    op.add_column('orders', sa.Column('actual_amount', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'actual_amount')
