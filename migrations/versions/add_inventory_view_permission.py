"""add_inventory_view_permission

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add inventory:view permission to roles that need inventory access.

    This adds the inventory:view permission to:
    - Roles with role_id NOT in [2, 4, 5, 6] that have product-related permissions
    - Admin roles (typically role_id 1)

    Users with this permission AND role_id NOT in [2, 4, 5, 6] can bypass
    shop ownership checks in the inventory route.
    """
    # Add inventory:view permission to roles that already have product_view or system:* permission
    # Using raw SQL to update the JSON array - cast JSON to JSONB for operations
    op.execute("""
        UPDATE roles
        SET permissions = (permissions::jsonb || '["inventory:view"]'::jsonb)::json
        WHERE (
            permissions::jsonb ? 'product_view'
            OR permissions::jsonb ? 'system:*'
            OR permissions::jsonb ? 'shop_admin'
        )
        AND NOT (permissions::jsonb ? 'inventory:view')
    """)


def downgrade() -> None:
    """Remove inventory:view permission from all roles."""
    op.execute("""
        UPDATE roles
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions::jsonb) AS elem
            WHERE elem::text != '"inventory:view"'
        )
        WHERE permissions::jsonb ? 'inventory:view'
    """)
