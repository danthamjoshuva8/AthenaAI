
"""
Base interface for all Large Language Model (LLM) providers.

Every LLM provider integrated with AthenaAI must implement this interface.
Examples include DeepSeek, OpenAI, and locally hosted models.

This abstraction allows the AI orchestration layer to use different
LLM providers without depending on provider-specific implementations.
"""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Abstract base class for AthenaAI LLM providers.

    Responsibilities:
        - Define a consistent interface for LLM providers.
        - Ensure every provider implements trade analysis.
        - Provide a common extension point for future providers.

    Notes:
        - API requests and provider-specific logging belong in subclasses.
        - Response validation is handled by the AI response models.
        - Caching should be implemented outside this interface.
    """

    @abstractmethod
    async def analyze_trade(self, prompt: str) -> dict:
        """
        Analyse a trading opportunity using the configured LLM provider.

        Args:
            prompt: Complete analysis prompt containing trade context
                    and instructions for the LLM.

        Returns:
            dict: Structured AI analysis response.

        Raises:
            NotImplementedError: If a subclass does not implement this method.
            Exception: Provider-specific API or response-processing errors.

        Implementation requirements:
            - Implement asynchronous API communication.
            - Handle provider-specific errors and timeouts.
            - Log request failures without exposing API keys or sensitive data.
            - Return a structured response compatible with LLMResponse.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement analyze_trade()."
        )
