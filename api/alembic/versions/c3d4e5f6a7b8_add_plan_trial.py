"""add plan and trial_ends_at to organizations

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("plan", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "organizations",
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "trial_ends_at")
    op.drop_column("organizations", "plan")
