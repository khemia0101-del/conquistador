"""add pricing fields to lead_assignments

Revision ID: a2b3c4d5e6f7
Revises: 169dbe8a4c11
Create Date: 2026-03-28 21:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '169dbe8a4c11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lead_assignments', sa.Column('contractor_quote', sa.DECIMAL(precision=10, scale=2), nullable=True))
    op.add_column('lead_assignments', sa.Column('markup_pct', sa.DECIMAL(precision=5, scale=2), server_default='20', nullable=True))
    op.add_column('lead_assignments', sa.Column('customer_price', sa.DECIMAL(precision=10, scale=2), nullable=True))
    op.add_column('lead_assignments', sa.Column('is_backup', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('lead_assignments', 'is_backup')
    op.drop_column('lead_assignments', 'customer_price')
    op.drop_column('lead_assignments', 'markup_pct')
    op.drop_column('lead_assignments', 'contractor_quote')
