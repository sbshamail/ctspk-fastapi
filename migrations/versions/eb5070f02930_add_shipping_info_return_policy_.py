"""add shipping_info,return_policy,warranty,meta_description,meta_title,tags as jsonb to products

Revision ID: eb5070f02930
Revises: dc1ae0c8f4d7
Create Date: 2025-10-04 09:51:05.875271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'eb5070f02930'
down_revision: Union[str, Sequence[str], None] = 'dc1ae0c8f4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add new column meta_title as TEXT
    op.add_column("products", sa.Column("meta_title", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # 2. Add new column meta_description as TEXT
    op.add_column("products", sa.Column("meta_description", sa.Text(), nullable=True))
    # 3. Add new column warranty as TEXT
    op.add_column("products", sa.Column("warranty", sa.Text(), nullable=True))
    # 4. Add new column return_policy as TEXT
    op.add_column("products", sa.Column("return_policy", sa.Text(), nullable=True))
    # 5. Add new column html_content as TEXT
    op.add_column("products", sa.Column("shipping_info", sa.Text(), nullable=True))
    # 6. Add new column meta_title as TEXT
    op.add_column("products", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "tags")
    op.drop_column("products", "meta_title")
    op.drop_column("products", "origmeta_descriptioninal")
    op.drop_column("products", "warranty")
    op.drop_column("products", "return_policy")
    op.drop_column("products", "shipping_info")
