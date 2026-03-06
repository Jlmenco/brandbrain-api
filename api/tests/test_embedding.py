"""Tests for embedding service and RAG prompt builder.

BrandKitEmbedding uses pgvector (PG-specific), so these tests
mock DB operations and test logic in isolation.
"""

from app.models.influencer import Influencer, BrandKit
from app.services.embedding_service import EmbeddingService, EMBEDDING_DIM
from app.services.prompt_builder import build_content_generation_prompt


class TestChunking:
    """Test BrandKit chunking logic."""

    def test_chunk_brand_kit_full(self):
        svc = EmbeddingService(provider="mock")
        inf = Influencer(
            id="inf-1", org_id="org-1", name="Mel Expert",
            niche="mel natural", tone="acolhedor", emoji_level="low",
            language="pt-BR", cta_style="Saiba mais",
            forbidden_topics=["politica"], forbidden_words=["spam"],
            allowed_words=["inovacao"],
        )
        bk = BrandKit(
            id="bk-1", influencer_id="inf-1",
            description="Brand kit da Melpura",
            value_props={"qualidade": "mel 100% natural"},
            products={"mel_silvestre": "Mel Silvestre 500g"},
            audience={},  # empty → skipped
            style_guidelines={},  # empty → skipped
            links={"site": "https://melpura.com"},
        )
        chunks = svc.chunk_brand_kit(inf, bk)

        types = [c["chunk_type"] for c in chunks]
        assert "influencer_profile" in types
        assert "description" in types
        assert "value_props" in types
        assert "products" in types
        assert "links" in types
        # empty dicts skipped
        assert "audience" not in types
        assert "style_guidelines" not in types
        assert len(chunks) == 5

    def test_chunk_brand_kit_minimal(self):
        svc = EmbeddingService(provider="mock")
        inf = Influencer(id="inf-1", org_id="org-1", name="Minimal")
        bk = BrandKit(id="bk-1", influencer_id="inf-1")
        chunks = svc.chunk_brand_kit(inf, bk)
        # Only influencer_profile (no description, no JSON data)
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "influencer_profile"

    def test_influencer_profile_content(self):
        svc = EmbeddingService(provider="mock")
        inf = Influencer(
            id="inf-1", org_id="org-1", name="Mel Expert",
            niche="mel natural", tone="acolhedor",
            forbidden_words=["spam", "gratis"],
        )
        bk = BrandKit(id="bk-1", influencer_id="inf-1")
        chunks = svc.chunk_brand_kit(inf, bk)
        profile = chunks[0]["chunk_text"]
        assert "Mel Expert" in profile
        assert "mel natural" in profile
        assert "acolhedor" in profile
        assert "spam" in profile
        assert "gratis" in profile

    def test_chunk_all_json_fields(self):
        svc = EmbeddingService(provider="mock")
        inf = Influencer(id="inf-1", org_id="org-1", name="Full")
        bk = BrandKit(
            id="bk-1", influencer_id="inf-1",
            description="Descricao completa",
            value_props={"v": 1},
            products={"p": 1},
            audience={"a": 1},
            style_guidelines={"s": 1},
            links={"l": 1},
        )
        chunks = svc.chunk_brand_kit(inf, bk)
        # profile + description + 5 JSON fields = 7
        assert len(chunks) == 7


class TestMockEmbedding:
    """Test mock embedding generation."""

    def test_generate_embedding_mock(self):
        svc = EmbeddingService(provider="mock")
        vec = svc.generate_embedding("test text")
        assert len(vec) == EMBEDDING_DIM
        assert all(v == 0.0 for v in vec)

    def test_generate_embeddings_batch_mock(self):
        svc = EmbeddingService(provider="mock")
        vecs = svc.generate_embeddings_batch(["text1", "text2", "text3"])
        assert len(vecs) == 3
        for vec in vecs:
            assert len(vec) == EMBEDDING_DIM
            assert all(v == 0.0 for v in vec)

    def test_generate_embeddings_batch_empty(self):
        svc = EmbeddingService(provider="mock")
        vecs = svc.generate_embeddings_batch([])
        assert len(vecs) == 0


class TestPromptBuilder:
    """Test prompt construction."""

    def test_build_prompt_with_context(self):
        chunks = [
            {"chunk_type": "description", "chunk_text": "Brand kit da Melpura"},
            {"chunk_type": "products", "chunk_text": "Produtos: mel silvestre"},
        ]
        system, user = build_content_generation_prompt(
            influencer_name="Mel Expert",
            channel="instagram",
            topic="beneficios do mel",
            objectives=["awareness"],
            brand_context_chunks=chunks,
        )
        assert "Mel Expert" in system
        assert "Brand kit da Melpura" in system
        assert "mel silvestre" in system
        assert "instagram" in system
        assert "beneficios do mel" in user
        assert "awareness" in user

    def test_build_prompt_no_context(self):
        system, user = build_content_generation_prompt(
            influencer_name="Test",
            channel="linkedin",
            topic="test topic",
            objectives=[],
            brand_context_chunks=[],
        )
        assert "Nenhum contexto de marca disponivel" in system
        assert "linkedin" in system

    def test_build_prompt_multiple_objectives(self):
        _, user = build_content_generation_prompt(
            influencer_name="Test",
            channel="linkedin",
            topic="test",
            objectives=["awareness", "leads", "traffic"],
            brand_context_chunks=[],
        )
        assert "awareness" in user
        assert "leads" in user
        assert "traffic" in user

    def test_build_prompt_custom_language(self):
        system, _ = build_content_generation_prompt(
            influencer_name="Test",
            channel="twitter",
            topic="test",
            objectives=[],
            brand_context_chunks=[],
            language="en-US",
        )
        assert "en-US" in system
