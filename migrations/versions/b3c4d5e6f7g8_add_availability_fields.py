"""Add contractor availability fields.

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7g8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contractors", sa.Column("available_days", ARRAY(sa.String()), server_default="{}"))
    op.add_column("contractors", sa.Column("available_start", sa.String(5), nullable=True))
    op.add_column("contractors", sa.Column("available_end", sa.String(5), nullable=True))
    op.add_column("contractors", sa.Column("unavailable_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("contractors", "unavailable_until")
    op.drop_column("contractors", "available_end")
    op.drop_column("contractors", "available_start")
    op.drop_column("contractors", "available_days")
