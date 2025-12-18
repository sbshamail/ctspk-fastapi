"""add_return_tracking_to_order_product

Revision ID: a8b7c9d0e1f2
Revises: 87af15e4b3f2
Create Date: 2025-12-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8b7c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = '87af15e4b3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add return tracking columns to order_product table
    op.add_column('order_product', sa.Column('return_request_id', sa.Integer(), nullable=True))
    op.add_column('order_product', sa.Column('is_returned', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('order_product', sa.Column('returned_quantity', sa.Integer(), nullable=True, server_default='0'))

    # Add foreign key constraint for return_request_id
    op.create_foreign_key(
        'fk_order_product_return_request_id',
        'order_product',
        'return_requests',
        ['return_request_id'],
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint first
    op.drop_constraint('fk_order_product_return_request_id', 'order_product', type_='foreignkey')

    # Drop columns
    op.drop_column('order_product', 'returned_quantity')
    op.drop_column('order_product', 'is_returned')
    op.drop_column('order_product', 'return_request_id')
