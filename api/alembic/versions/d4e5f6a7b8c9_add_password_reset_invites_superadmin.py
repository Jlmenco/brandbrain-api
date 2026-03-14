"""add password_reset_tokens, org_invites, user.is_superadmin

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # is_superadmin no user (para admin panel)
    op.add_column(
        "users",
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Tokens de reset de senha
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("token", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Convites de membros
    op.create_table(
        "org_invites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("invited_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False, index=True),
        sa.Column("role", sa.String(), nullable=False, server_default="editor"),
        sa.Column("token", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("org_invites")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "is_superadmin")
