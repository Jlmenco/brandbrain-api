"""add templates, usage logs, webhook configs, voice_id, video_job_status

Revision ID: a1b2c3d4e5f6
Revises: 6c312cdeffd3
Create Date: 2026-03-11 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

revision = 'a1b2c3d4e5f6'
down_revision = '6c312cdeffd3'
branch_labels = None
depends_on = None


def upgrade():
    # --- content_templates ---
    op.create_table(
        'content_templates',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('provider_target', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('text_template', sa.Text(), nullable=False, server_default=''),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_templates_org_id', 'content_templates', ['org_id'])

    # --- usage_logs ---
    op.create_table(
        'usage_logs',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('cost_center_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('resource_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unit_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['cost_center_id'], ['cost_centers.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_usage_logs_org_id', 'usage_logs', ['org_id'])
    op.create_index('ix_usage_logs_cost_center_id', 'usage_logs', ['cost_center_id'])

    # --- webhook_configs ---
    op.create_table(
        'webhook_configs',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('events', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_configs_org_id', 'webhook_configs', ['org_id'])

    # --- influencers: add voice_id ---
    op.add_column('influencers',
        sa.Column('voice_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )

    # --- content_items: add video_job_status + video_job_error ---
    op.add_column('content_items',
        sa.Column('video_job_status', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )
    op.add_column('content_items',
        sa.Column('video_job_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )

    # --- users: add push_token ---
    op.add_column('users',
        sa.Column('push_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )

    # --- organizations: add billing_alert_threshold ---
    op.add_column('organizations',
        sa.Column('billing_alert_threshold', sa.Float(), nullable=True)
    )


def downgrade():
    op.drop_column('organizations', 'billing_alert_threshold')
    op.drop_column('users', 'push_token')
    op.drop_column('content_items', 'video_job_error')
    op.drop_column('content_items', 'video_job_status')
    op.drop_column('influencers', 'voice_id')

    op.drop_index('ix_webhook_configs_org_id', table_name='webhook_configs')
    op.drop_table('webhook_configs')

    op.drop_index('ix_usage_logs_cost_center_id', table_name='usage_logs')
    op.drop_index('ix_usage_logs_org_id', table_name='usage_logs')
    op.drop_table('usage_logs')

    op.drop_index('ix_content_templates_org_id', table_name='content_templates')
    op.drop_table('content_templates')
