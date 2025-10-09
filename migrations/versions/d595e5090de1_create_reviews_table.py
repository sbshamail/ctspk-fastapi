"""create reviews table

Revision ID: d595e5090de1
Revises: 381927433838
Create Date: 2025-10-09 10:34:46.895344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'd595e5090de1'
down_revision: Union[str, Sequence[str], None] = '381927433838'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('variation_option_id', sa.Integer(), nullable=True),
        sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('photos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # Add foreign keys
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_reviews_order_id', 'orders', ['order_id'], ['id'])
        batch_op.create_foreign_key('fk_reviews_user_id', 'users', ['user_id'], ['id'])
        batch_op.create_foreign_key('fk_reviews_shop_id', 'shops', ['shop_id'], ['id'])
        batch_op.create_foreign_key('fk_reviews_product_id', 'products', ['product_id'], ['id'])
        batch_op.create_foreign_key('fk_reviews_variation_option_id', 'variation_options', ['variation_option_id'], ['id'])
        
        # Create indexes
        batch_op.create_index('ix_reviews_order_id', ['order_id'])
        batch_op.create_index('ix_reviews_user_id', ['user_id'])
        batch_op.create_index('ix_reviews_shop_id', ['shop_id'])
        batch_op.create_index('ix_reviews_product_id', ['product_id'])
        batch_op.create_index('ix_reviews_variation_option_id', ['variation_option_id'])
        batch_op.create_index('ix_reviews_rating', ['rating'])
        batch_op.create_index('ix_reviews_created_at', ['created_at'])
        
        # Unique constraint for non-deleted reviews
        batch_op.create_index('uq_review_order_product', ['order_id', 'product_id'], unique=True, 
                            postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index('uq_review_order_product')
        batch_op.drop_index('ix_reviews_created_at')
        batch_op.drop_index('ix_reviews_rating')
        batch_op.drop_index('ix_reviews_variation_option_id')
        batch_op.drop_index('ix_reviews_product_id')
        batch_op.drop_index('ix_reviews_shop_id')
        batch_op.drop_index('ix_reviews_user_id')
        batch_op.drop_index('ix_reviews_order_id')
        
        batch_op.drop_constraint('fk_reviews_variation_option_id', type_='foreignkey')
        batch_op.drop_constraint('fk_reviews_product_id', type_='foreignkey')
        batch_op.drop_constraint('fk_reviews_shop_id', type_='foreignkey')
        batch_op.drop_constraint('fk_reviews_user_id', type_='foreignkey')
        batch_op.drop_constraint('fk_reviews_order_id', type_='foreignkey')
    
    op.drop_table('reviews')
