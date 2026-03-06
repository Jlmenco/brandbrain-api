from app.config import settings

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class AIGateway:
    """Gateway for interacting with AI providers."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider
        if provider == "openai" and AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate text using the configured AI provider."""
        if self.provider == "mock":
            return f"[MOCK AI RESPONSE] Prompt received: {prompt[:100]}..."

        if self.provider == "openai" and self.client:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        # Default to mock if provider not recognized
        return f"[MOCK AI RESPONSE] Prompt received: {prompt[:100]}..."


def get_gateway() -> AIGateway:
    """Get an AI Gateway instance configured with the default provider."""
    return AIGateway(provider=settings.AI_DEFAULT_PROVIDER)
