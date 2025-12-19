"""update cart unique constraint to include variation_option_id

Revision ID: b1c2d3e4f5g6
Revises: 57c4687b492d
Create Date: 2025-12-20

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, Sequence[str], None] = '57c4687b492d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old unique constraint (user_id + product_id only)
    op.drop_constraint('uix_user_product', 'carts', type_='unique')

    # Add new unique constraint (user_id + product_id + variation_option_id)
    op.create_unique_constraint(
        'uix_user_product_variation',
        'carts',
        ['user_id', 'product_id', 'variation_option_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new constraint
    op.drop_constraint('uix_user_product_variation', 'carts', type_='unique')

    # Restore old constraint
    op.create_unique_constraint(
        'uix_user_product',
        'carts',
        ['user_id', 'product_id']
    )
