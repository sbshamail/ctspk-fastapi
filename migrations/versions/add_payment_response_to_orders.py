"""add_payment_response_to_orders

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payment_response JSON column to orders table."""
    op.add_column('orders', sa.Column('payment_response', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove payment_response column from orders table."""
    op.drop_column('orders', 'payment_response')
