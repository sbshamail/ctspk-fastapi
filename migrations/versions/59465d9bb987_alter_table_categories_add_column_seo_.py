"""alter table categories add column seo title keyword and description

Revision ID: 59465d9bb987
Revises: 0ea8c1987c29
Create Date: 2025-10-05 21:03:59.875354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '59465d9bb987'
down_revision: Union[str, Sequence[str], None] = '0ea8c1987c29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("categories", sa.Column("seo_description", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("categories", sa.Column("seo_keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("categories", sa.Column("seo_title", sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("categories", "seo_description")
    op.drop_column("categories", "seo_keywords")
    op.drop_column("categories", "seo_title")
