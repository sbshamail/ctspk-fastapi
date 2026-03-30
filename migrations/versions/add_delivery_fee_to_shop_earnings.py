"""add_delivery_fee_per_product to shop_earnings

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shop_earnings', sa.Column('delivery_fee_per_product', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))


def downgrade() -> None:
    op.drop_column('shop_earnings', 'delivery_fee_per_product')
