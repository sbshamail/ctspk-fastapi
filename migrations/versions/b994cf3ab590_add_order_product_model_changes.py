"""add_order_product_model_changes

Revision ID: b994cf3ab590
Revises: e2528b6674da
Create Date: 2025-10-12 23:32:01.249307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'b994cf3ab590'
down_revision: Union[str, Sequence[str], None] = 'e2528b6674da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE orderitemtype AS ENUM ('SIMPLE', 'VARIABLE', 'GROUPED')")
    
    # Add the new columns
    op.add_column('order_product', 
                  sa.Column('item_type', 
                           sa.Enum('SIMPLE', 'VARIABLE', 'GROUPED', 
                                  name='orderitemtype', 
                                  create_type=False), 
                           nullable=False, 
                           server_default='SIMPLE'))
    
    op.add_column('order_product', 
                  sa.Column('variation_data', 
                           postgresql.JSONB(astext_type=sa.Text()), 
                           nullable=True))
    
    op.add_column('order_product', 
                  sa.Column('grouped_items', 
                           postgresql.JSONB(astext_type=sa.Text()), 
                           nullable=True))
    
    op.add_column('order_product', 
                  sa.Column('product_snapshot', 
                           postgresql.JSONB(astext_type=sa.Text()), 
                           nullable=True))
    
    op.add_column('order_product', 
                  sa.Column('variation_snapshot', 
                           postgresql.JSONB(astext_type=sa.Text()), 
                           nullable=True))
    
    # Remove the server default after data migration if needed
    op.alter_column('order_product', 'item_type', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the columns first
    op.drop_column('order_product', 'variation_snapshot')
    op.drop_column('order_product', 'product_snapshot')
    op.drop_column('order_product', 'grouped_items')
    op.drop_column('order_product', 'variation_data')
    op.drop_column('order_product', 'item_type')
    
    # Drop the enum type
    op.execute("DROP TYPE orderitemtype")