"""create wishlist table

Revision ID: e9323ee6489b
Revises: d595e5090de1
Create Date: 2025-10-09 11:06:03.172039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'e9323ee6489b'
down_revision: Union[str, Sequence[str], None] = 'd595e5090de1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('wishlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('variation_option_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        
        # Primary Key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_wishlists_user_id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_wishlists_product_id'),
        sa.ForeignKeyConstraint(['variation_option_id'], ['variation_options.id'], name='fk_wishlists_variation_option_id'),
        
        # Indexes
        sa.Index('ix_wishlists_user_id', 'user_id'),
        sa.Index('ix_wishlists_product_id', 'product_id'),
        sa.Index('ix_wishlists_variation_option_id', 'variation_option_id'),
        sa.Index('ix_wishlists_created_at', 'created_at')
    )
    
    # Unique constraint to prevent duplicate wishlist items
    op.create_index('uq_wishlist_user_product_variation', 'wishlists', 
                   ['user_id', 'product_id', 'variation_option_id'], 
                   unique=True)
    
    # Composite index for common queries
    op.create_index('idx_wishlist_user_created', 'wishlists', ['user_id', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_wishlist_user_created', table_name='wishlists')
    op.drop_index('uq_wishlist_user_product_variation', table_name='wishlists')
    op.drop_table('wishlists')
