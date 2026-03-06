"""Embedding Service — Generate and search pgvector embeddings for RAG.

Follows the AI_DEFAULT_PROVIDER pattern from AIGateway:
- "mock" provider: returns deterministic fake embeddings (1536 zeros)
- "openai" provider: calls OpenAI text-embedding-3-small API
"""

import json

from sqlmodel import Session, select
from sqlalchemy import text as sa_text

from app.config import settings
from app.models.influencer import Influencer, BrandKit
from app.models.embedding import BrandKitEmbedding

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class EmbeddingService:
    def __init__(self, provider: str = "mock"):
        self.provider = provider
        if provider == "openai" and OpenAI:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None

    # --- Chunking ---

    def chunk_brand_kit(self, influencer: Influencer, brand_kit: BrandKit) -> list[dict]:
        """Convert BrandKit + Influencer into text chunks for embedding."""
        chunks = []

        # Chunk: Influencer profile summary
        profile_parts = [f"Nome: {influencer.name}"]
        if influencer.niche:
            profile_parts.append(f"Nicho: {influencer.niche}")
        if influencer.tone:
            profile_parts.append(f"Tom de voz: {influencer.tone}")
        if influencer.cta_style:
            profile_parts.append(f"Estilo de CTA: {influencer.cta_style}")
        if influencer.forbidden_topics:
            profile_parts.append(f"Topicos proibidos: {', '.join(influencer.forbidden_topics)}")
        if influencer.forbidden_words:
            profile_parts.append(f"Palavras proibidas: {', '.join(influencer.forbidden_words)}")
        if influencer.allowed_words:
            profile_parts.append(f"Palavras permitidas: {', '.join(influencer.allowed_words)}")
        profile_parts.append(f"Nivel de emojis: {influencer.emoji_level}")
        profile_parts.append(f"Idioma: {influencer.language}")
        chunks.append({"chunk_type": "influencer_profile", "chunk_text": ". ".join(profile_parts)})

        # Chunk: Brand kit description
        if brand_kit.description:
            chunks.append({"chunk_type": "description", "chunk_text": brand_kit.description})

        # Chunks: JSON fields
        json_fields = {
            "value_props": ("Propostas de valor", brand_kit.value_props),
            "products": ("Produtos", brand_kit.products),
            "audience": ("Publico-alvo", brand_kit.audience),
            "style_guidelines": ("Diretrizes de estilo", brand_kit.style_guidelines),
            "links": ("Links", brand_kit.links),
        }
        for chunk_type, (label, data) in json_fields.items():
            if data:
                text = f"{label}: {json.dumps(data, ensure_ascii=False, indent=None)}"
                chunks.append({"chunk_type": chunk_type, "chunk_text": text})

        return chunks

    # --- Embedding generation ---

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a single embedding vector."""
        if self.provider == "mock" or self.client is None:
            return [0.0] * EMBEDDING_DIM

        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call."""
        if self.provider == "mock" or self.client is None:
            return [[0.0] * EMBEDDING_DIM for _ in texts]

        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    # --- Upsert embeddings ---

    def embed_brand_kit(self, db: Session, influencer_id: str) -> int:
        """Generate and store embeddings for an influencer's brand kit.

        Deletes existing embeddings and replaces them.
        Returns number of chunks embedded.
        """
        influencer = db.get(Influencer, influencer_id)
        if not influencer:
            return 0

        brand_kit = db.exec(
            select(BrandKit).where(BrandKit.influencer_id == influencer_id)
        ).first()
        if not brand_kit:
            return 0

        chunks = self.chunk_brand_kit(influencer, brand_kit)
        if not chunks:
            return 0

        texts = [c["chunk_text"] for c in chunks]
        embeddings = self.generate_embeddings_batch(texts)

        # Delete existing embeddings
        existing = db.exec(
            select(BrandKitEmbedding).where(
                BrandKitEmbedding.brand_kit_id == brand_kit.id
            )
        ).all()
        for e in existing:
            db.delete(e)
        db.flush()

        # Insert new embeddings
        for chunk, embedding in zip(chunks, embeddings):
            row = BrandKitEmbedding(
                brand_kit_id=brand_kit.id,
                influencer_id=influencer_id,
                chunk_type=chunk["chunk_type"],
                chunk_text=chunk["chunk_text"],
                embedding=embedding,
                model_name=EMBEDDING_MODEL,
            )
            db.add(row)

        db.flush()
        return len(chunks)

    # --- Semantic search ---

    def search_brand_context(
        self,
        db: Session,
        influencer_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search brand kit embeddings by semantic similarity."""
        query_embedding = self.generate_embedding(query)

        if self.provider == "mock" or self.client is None:
            # Mock mode: return all chunks without real similarity
            rows = db.exec(
                select(BrandKitEmbedding).where(
                    BrandKitEmbedding.influencer_id == influencer_id
                )
            ).all()
            return [
                {"chunk_type": r.chunk_type, "chunk_text": r.chunk_text, "similarity": 1.0}
                for r in rows[:top_k]
            ]

        # Real pgvector cosine similarity search
        stmt = sa_text("""
            SELECT chunk_type, chunk_text,
                   1 - (embedding <=> :query_vec::vector) AS similarity
            FROM brand_kit_embeddings
            WHERE influencer_id = :inf_id
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :top_k
        """)
        results = db.execute(
            stmt,
            {"query_vec": str(query_embedding), "inf_id": influencer_id, "top_k": top_k}
        ).fetchall()

        return [
            {"chunk_type": r.chunk_type, "chunk_text": r.chunk_text, "similarity": r.similarity}
            for r in results
        ]


def get_embedding_service() -> EmbeddingService:
    """Get an EmbeddingService instance configured with the default provider."""
    return EmbeddingService(provider=settings.AI_DEFAULT_PROVIDER)
