"""add drip campaigns, steps, enrollments

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'drip_campaigns',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('trigger_event', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'drip_steps',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('campaign_id', sa.String(), sa.ForeignKey('drip_campaigns.id'), nullable=False, index=True),
        sa.Column('step_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delay_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subject', sa.String(), nullable=False, server_default=''),
        sa.Column('body_template', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'drip_enrollments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('campaign_id', sa.String(), sa.ForeignKey('drip_campaigns.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True, index=True),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False),
        sa.Column('next_send_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('drip_enrollments')
    op.drop_table('drip_steps')
    op.drop_table('drip_campaigns')
