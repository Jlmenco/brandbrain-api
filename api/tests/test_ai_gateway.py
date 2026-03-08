"""Tests for AIGateway with mock, openai, and anthropic providers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAIGatewayMock:
    """Tests for the mock provider."""

    def test_mock_provider_init(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        assert gw.provider == "mock"
        assert gw.openai_client is None
        assert gw.anthropic_client is None

    @pytest.mark.asyncio
    async def test_mock_generate(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        result = await gw.generate(prompt="Write a post about marketing")
        assert "[MOCK AI RESPONSE]" in result
        assert "Write a post" in result

    @pytest.mark.asyncio
    async def test_unknown_provider_falls_back_to_mock(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="unknown_provider")
        result = await gw.generate(prompt="test")
        assert "[MOCK AI RESPONSE]" in result

    def test_get_gateway_returns_instance(self):
        from app.services.ai_gateway import get_gateway

        gw = get_gateway()
        assert gw.provider == "mock"


class TestAIGatewayOpenAI:
    """Tests for the OpenAI provider (mocked SDK)."""

    @pytest.mark.asyncio
    async def test_openai_generate_with_system(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        # Manually set up a mock openai client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated post content"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        gw.provider = "openai"
        gw.openai_client = mock_client
        gw.model = "gpt-4o-mini"

        result = await gw.generate(
            prompt="Write a post",
            system="You are a marketing expert",
            temperature=0.7,
            max_tokens=800,
        )

        assert result == "Generated post content"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_openai_generate_without_system(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        gw.provider = "openai"
        gw.openai_client = mock_client
        gw.model = "gpt-4o-mini"

        result = await gw.generate(prompt="Write a post")

        assert result == "Response"
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"


class TestAIGatewayAnthropic:
    """Tests for the Anthropic provider (mocked SDK)."""

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_system(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude generated content")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        gw.provider = "anthropic"
        gw.anthropic_client = mock_client
        gw.model = "claude-haiku-4-5-20251001"

        result = await gw.generate(
            prompt="Write a post about brand marketing",
            system="You are a marketing expert for Brand Brain",
            temperature=0.7,
            max_tokens=800,
        )

        assert result == "Claude generated content"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
        assert call_kwargs["system"] == "You are a marketing expert for Brand Brain"
        assert call_kwargs["messages"] == [{"role": "user", "content": "Write a post about brand marketing"}]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 800

    @pytest.mark.asyncio
    async def test_anthropic_generate_without_system(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response without system")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        gw.provider = "anthropic"
        gw.anthropic_client = mock_client
        gw.model = "claude-haiku-4-5-20251001"

        result = await gw.generate(prompt="Hello")

        assert result == "Response without system"
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    @pytest.mark.asyncio
    async def test_anthropic_no_client_falls_back_to_mock(self):
        from app.services.ai_gateway import AIGateway

        gw = AIGateway(provider="mock")
        gw.provider = "anthropic"
        gw.anthropic_client = None

        result = await gw.generate(prompt="test")
        assert "[MOCK AI RESPONSE]" in result


class TestAIGatewayDefaults:
    """Tests for default model selection."""

    def test_default_model_openai(self):
        from app.services.ai_gateway import AIGateway, DEFAULT_MODELS

        gw = AIGateway(provider="mock")
        gw.provider = "openai"
        gw.model = DEFAULT_MODELS["openai"]
        assert gw.model == "gpt-4o-mini"

    def test_default_model_anthropic(self):
        from app.services.ai_gateway import AIGateway, DEFAULT_MODELS

        gw = AIGateway(provider="mock")
        gw.provider = "anthropic"
        gw.model = DEFAULT_MODELS["anthropic"]
        assert gw.model == "claude-haiku-4-5-20251001"
