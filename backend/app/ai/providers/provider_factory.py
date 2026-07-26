from app.core.config import settings

from app.ai.providers.deepseek_provider import DeepSeekProvider
from app.ai.providers.ollama_provider import OllamaProvider


class ProviderFactory:

    @staticmethod
    def get_provider():

        provider = settings.LLM_PROVIDER.lower()

        if provider == "deepseek":
            return DeepSeekProvider()

        if provider == "ollama":
            return OllamaProvider()

        raise ValueError(f"Unsupported provider: {provider}")