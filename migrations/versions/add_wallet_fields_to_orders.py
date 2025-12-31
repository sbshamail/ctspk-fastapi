"""add_wallet_fields_to_orders

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2025-12-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add wallet_amount_used column to orders table and order_id to wallet_transactions."""
    # Add wallet_amount_used column to orders table
    op.add_column('orders', sa.Column('wallet_amount_used', sa.Float(), nullable=True, server_default='0'))

    # Add order_id column to wallet_transactions table for tracking wallet payments
    op.add_column('wallet_transactions', sa.Column('order_id', sa.Integer(), nullable=True))

    # Add foreign key constraint for order_id
    op.create_foreign_key(
        'fk_wallet_transactions_order_id',
        'wallet_transactions',
        'orders',
        ['order_id'],
        ['id']
    )

    # Add index on order_id for faster lookups
    op.create_index('ix_wallet_transactions_order_id', 'wallet_transactions', ['order_id'])


def downgrade() -> None:
    """Remove wallet_amount_used column from orders table and order_id from wallet_transactions."""
    # Drop index first
    op.drop_index('ix_wallet_transactions_order_id', table_name='wallet_transactions')

    # Drop foreign key constraint
    op.drop_constraint('fk_wallet_transactions_order_id', 'wallet_transactions', type_='foreignkey')

    # Drop columns
    op.drop_column('wallet_transactions', 'order_id')
    op.drop_column('orders', 'wallet_amount_used')
