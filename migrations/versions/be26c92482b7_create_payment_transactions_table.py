"""create_payment_transactions_table

Revision ID: be26c92482b7
Revises: 3be62b095b1a
Create Date: 2025-12-31 04:41:27.233640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be26c92482b7'
down_revision: Union[str, Sequence[str], None] = '3be62b095b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create payment_transactions table."""
    op.create_table(
        'payment_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=191), nullable=False),
        sa.Column('gateway_transaction_id', sa.String(length=191), nullable=True),
        sa.Column('gateway_reference', sa.String(length=191), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('gateway_type', sa.String(length=50), nullable=False),
        sa.Column('flow_type', sa.String(length=50), nullable=False, server_default='redirect'),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='PKR'),
        sa.Column('fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('net_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('refunded_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='initiated'),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(length=191), nullable=True),
        sa.Column('customer_email', sa.String(length=191), nullable=True),
        sa.Column('customer_phone', sa.String(length=50), nullable=True),
        sa.Column('gateway_request', sa.JSON(), nullable=True),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('redirect_url', sa.String(length=500), nullable=True),
        sa.Column('callback_url', sa.String(length=500), nullable=True),
        sa.Column('webhook_received', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('webhook_data', sa.JSON(), nullable=True),
        sa.Column('webhook_received_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('transaction_id')
    )

    # Create indexes for better query performance
    op.create_index('ix_payment_transactions_transaction_id', 'payment_transactions', ['transaction_id'])
    op.create_index('ix_payment_transactions_gateway_transaction_id', 'payment_transactions', ['gateway_transaction_id'])
    op.create_index('ix_payment_transactions_order_id', 'payment_transactions', ['order_id'])
    op.create_index('ix_payment_transactions_gateway_type', 'payment_transactions', ['gateway_type'])
    op.create_index('ix_payment_transactions_status', 'payment_transactions', ['status'])
    op.create_index('ix_payment_transactions_customer_id', 'payment_transactions', ['customer_id'])
    op.create_index('ix_payment_transactions_created_at', 'payment_transactions', ['created_at'])


def downgrade() -> None:
    """Drop payment_transactions table."""
    op.drop_index('ix_payment_transactions_created_at', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_customer_id', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_status', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_gateway_type', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_order_id', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_gateway_transaction_id', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_transaction_id', table_name='payment_transactions')
    op.drop_table('payment_transactions')
