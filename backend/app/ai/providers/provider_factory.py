"""
LLM Provider Factory for AthenaAI.

Creates the configured LLM provider based on the LLM_PROVIDER setting.

Currently supported:
    - DeepSeek

Ollama is recognized but not implemented yet.

Responsibilities:
    - Read the configured LLM provider.
    - Validate the provider selection.
    - Initialize the corresponding provider.
    - Log provider initialization events and failures.

Caching:
    Provider instances are not cached by this factory.
    Provider lifecycle and reuse should be managed by the AI orchestrator
    or application dependency lifecycle.
"""

import logging
from time import perf_counter

from app.ai.providers.base_provider import BaseLLMProvider
from app.ai.providers.deepseek_provider import DeepSeekProvider
from app.config.settings import settings


logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory responsible for creating configured LLM providers.

    Currently, DeepSeek is the only implemented provider.
    """

    @staticmethod
    def get_provider() -> BaseLLMProvider:
        """
        Initialize and return the configured LLM provider.

        Returns:
            BaseLLMProvider: An initialized LLM provider instance.

        Raises:
            ValueError: If the configured provider is unsupported.
            NotImplementedError: If the selected provider is not implemented.
            Exception: If provider initialization fails unexpectedly.
        """

        start_time = perf_counter()
        provider = (settings.LLM_PROVIDER or "").strip().lower()

        logger.info(
            "LLM provider initialization started",
            extra={
                "event": "llm_provider_initialization_started",
                "provider": provider or None,
            },
        )

        try:
            if provider == "deepseek":
                instance = DeepSeekProvider()

            elif provider == "ollama":
                logger.error(
                    "Selected LLM provider is not implemented",
                    extra={
                        "event": "llm_provider_not_implemented",
                        "provider": provider,
                        "status": "not_implemented",
                    },
                )

                raise NotImplementedError(
                    "Ollama provider is not implemented yet."
                )

            else:
                logger.error(
                    "Unsupported LLM provider configured",
                    extra={
                        "event": "llm_provider_unsupported",
                        "provider": provider or None,
                        "status": "unsupported",
                    },
                )

                raise ValueError(
                    f"Unsupported LLM provider: {provider or '<empty>'}"
                )

            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.info(
                "LLM provider initialized successfully",
                extra={
                    "event": "llm_provider_initialization_completed",
                    "provider": provider,
                    "status": "success",
                    "duration_ms": duration_ms,
                },
            )

            return instance

        except (ValueError, NotImplementedError):
            raise

        except Exception:
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "Unexpected error during LLM provider initialization",
                extra={
                    "event": "llm_provider_initialization_failed",
                    "provider": provider or None,
                    "status": "failed",
                    "duration_ms": duration_ms,
                },
            )

            raise