
"""
Ollama LLM provider for AthenaAI.

This module reserves the provider interface for future local LLM integration.

Planned responsibilities:
    - Connect to a locally hosted Ollama instance.
    - Submit trade analysis prompts to a configured local model.
    - Process and return structured JSON analysis results.

Current status:
    Not implemented. DeepSeek is the currently supported provider.

Logging:
    - Track requests to the unsupported provider.
    - Record provider availability status.
    - Identify attempted operations.

Caching:
    Not required because no model operations are currently performed.
"""

import logging

from app.ai.providers.base_provider import BaseLLMProvider


logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Placeholder implementation for future Ollama integration.

    Ollama will allow AthenaAI to run supported language models locally
    instead of relying entirely on external LLM APIs.

    Current implementation:
        - No network requests.
        - No local model execution.
        - No response generation.
        - No caching.

    DeepSeek remains the active supported LLM provider.
    """

    async def analyze_trade(self, prompt: str) -> dict:
        """
        Analyse a trading opportunity using a local Ollama model.

        Args:
            prompt: Complete trade analysis prompt.

        Returns:
            dict: Structured AI analysis response.

        Raises:
            NotImplementedError: Ollama integration is not implemented.
        """

        # Step 1: Record the unsupported provider request.
        logger.warning(
            "Ollama analysis requested, but provider is not implemented",
            extra={
                "event": "llm_provider_unavailable",
                "service": "ollama",
                "provider": "ollama",
                "status": "not_implemented",
                "fallback_provider": "deepseek",
            },
        )

        # Step 2: Stop execution because local inference is unavailable.
        raise NotImplementedError(
            "Ollama provider is not implemented yet. "
            "Configure DeepSeek as the active LLM provider."
        )
