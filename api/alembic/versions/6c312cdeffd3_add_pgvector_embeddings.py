"""add pgvector embeddings

Revision ID: 6c312cdeffd3
Revises: 30e58d18f930
Create Date: 2026-03-04 18:42:19.984836

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from pgvector.sqlalchemy import Vector

revision = '6c312cdeffd3'
down_revision = '30e58d18f930'
branch_labels = None
depends_on = None

def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table('brand_kit_embeddings',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('brand_kit_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('influencer_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('chunk_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('chunk_text', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(1536), nullable=True),
    sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['brand_kit_id'], ['brand_kits.id'], ),
    sa.ForeignKeyConstraint(['influencer_id'], ['influencers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brand_kit_embeddings_brand_kit_id'), 'brand_kit_embeddings', ['brand_kit_id'], unique=False)
    op.create_index(op.f('ix_brand_kit_embeddings_influencer_id'), 'brand_kit_embeddings', ['influencer_id'], unique=False)

    # HNSW index for fast cosine similarity search
    op.execute("""
        CREATE INDEX ix_bke_embedding_cosine
        ON brand_kit_embeddings
        USING hnsw (embedding vector_cosine_ops)
    """)

def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_bke_embedding_cosine')
    op.drop_index(op.f('ix_brand_kit_embeddings_influencer_id'), table_name='brand_kit_embeddings')
    op.drop_index(op.f('ix_brand_kit_embeddings_brand_kit_id'), table_name='brand_kit_embeddings')
    op.drop_table('brand_kit_embeddings')
