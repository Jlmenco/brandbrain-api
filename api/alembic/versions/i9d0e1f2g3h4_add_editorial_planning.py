"""add editorial planning tables

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'i9d0e1f2g3h4'
down_revision = 'h8c9d0e1f2g3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'editorial_plans',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('cost_center_id', sa.String(), sa.ForeignKey('cost_centers.id'), nullable=True, index=True),
        sa.Column('period_type', sa.String(), nullable=False, server_default='week'),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('ai_rationale', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'editorial_slots',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('plan_id', sa.String(), sa.ForeignKey('editorial_plans.id'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('time_slot', sa.String(), nullable=False, server_default='morning'),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('pillar', sa.String(), nullable=False),
        sa.Column('theme', sa.String(), nullable=False),
        sa.Column('objective', sa.String(), nullable=False, server_default='awareness'),
        sa.Column('content_item_id', sa.String(), sa.ForeignKey('content_items.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('editorial_slots')
    op.drop_table('editorial_plans')
