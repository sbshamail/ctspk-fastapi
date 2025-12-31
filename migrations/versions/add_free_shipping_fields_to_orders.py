"""add_free_shipping_fields_to_orders

Revision ID: f1a2b3c4d5e6
Revises: be26c92482b7
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'be26c92482b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original_delivery_fee and free_shipping_source columns to orders table."""
    # Add original_delivery_fee column
    op.add_column('orders', sa.Column('original_delivery_fee', sa.Float(), nullable=True))

    # Add free_shipping_source column with default 'none'
    op.add_column('orders', sa.Column('free_shipping_source', sa.String(length=50), nullable=True, server_default='none'))


def downgrade() -> None:
    """Remove original_delivery_fee and free_shipping_source columns from orders table."""
    op.drop_column('orders', 'free_shipping_source')
    op.drop_column('orders', 'original_delivery_fee')
