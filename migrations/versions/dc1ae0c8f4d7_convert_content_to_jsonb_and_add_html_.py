"""convert content to jsonb and add html_content to email_template

Revision ID: dc1ae0c8f4d7
Revises: 5b0dd5fd667a
Create Date: 2025-10-03 10:09:09.777859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dc1ae0c8f4d7'
down_revision: Union[str, Sequence[str], None] = '5b0dd5fd667a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
   # 1. Change column `content` from TEXT to JSONB
    # Using "USING content::jsonb" so existing rows are converted automatically
    op.alter_column(
        "email_template",
        "content",
        type_=postgresql.JSONB,
        postgresql_using="content::jsonb"
    )

    # 2. Add new column html_content as TEXT
    op.add_column("email_template", sa.Column("html_content", sa.Text(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the changes
    op.drop_column("email_template", "html_content")

    op.alter_column(
        "email_template",
        "content",
        type_=sa.Text,
        postgresql_using="content::text"
    )
