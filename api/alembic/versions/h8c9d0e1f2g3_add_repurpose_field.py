"""add source_repurpose_id to content_items

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'h8c9d0e1f2g3'
down_revision = 'g7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'content_items',
        sa.Column('source_repurpose_id', sa.String(), sa.ForeignKey('content_items.id'), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column('content_items', 'source_repurpose_id')
