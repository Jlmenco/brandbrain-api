from app.config import settings

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
}


class AIGateway:
    """Gateway for interacting with AI providers."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider
        self.model = settings.AI_MODEL or DEFAULT_MODELS.get(provider, "")
        self.openai_client = None
        self.anthropic_client = None

        if provider == "openai" and AsyncOpenAI:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif provider == "anthropic" and AsyncAnthropic:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

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

        if self.provider == "openai" and self.openai_client:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        if self.provider == "anthropic" and self.anthropic_client:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system:
                kwargs["system"] = system

            response = await self.anthropic_client.messages.create(**kwargs)
            return response.content[0].text

        # Default to mock if provider not recognized
        return f"[MOCK AI RESPONSE] Prompt received: {prompt[:100]}..."


def get_gateway() -> AIGateway:
    """Get an AI Gateway instance configured with the default provider."""
    return AIGateway(provider=settings.AI_DEFAULT_PROVIDER)
