"""add_order_deliver_date_to_orders_status

Revision ID: 8ddb41b78bfc
Revises: b1c2d3e4f5g6
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8ddb41b78bfc'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add order_deliver_date column to orders_status table
    op.add_column('orders_status', sa.Column('order_deliver_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders_status', 'order_deliver_date')
