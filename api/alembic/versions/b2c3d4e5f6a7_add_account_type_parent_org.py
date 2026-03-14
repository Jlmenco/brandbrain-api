"""add account_type and parent_org_id to organizations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-11 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # account_type: solo | agency | group
    # Default 'agency' garante retrocompatibilidade com todos os usuarios existentes
    op.add_column('organizations',
        sa.Column('account_type', sa.String(), nullable=False, server_default='agency')
    )

    # parent_org_id: referencia para org mae (usado pelo perfil Group)
    op.add_column('organizations',
        sa.Column('parent_org_id', sa.String(), nullable=True)
    )
    op.create_foreign_key(
        'fk_organizations_parent_org_id',
        'organizations', 'organizations',
        ['parent_org_id'], ['id']
    )
    op.create_index('ix_organizations_parent_org_id', 'organizations', ['parent_org_id'])


def downgrade():
    op.drop_index('ix_organizations_parent_org_id', table_name='organizations')
    op.drop_constraint('fk_organizations_parent_org_id', 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'parent_org_id')
    op.drop_column('organizations', 'account_type')
