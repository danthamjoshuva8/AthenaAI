from app.ai.providers.base_provider import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):

    async def analyze_trade(self, prompt: str):

        raise NotImplementedError(
            "Ollama provider is not implemented yet."
        )