"""
AI Orchestrator for AthenaAI.

Coordinates the complete AI trade analysis pipeline.

Responsibilities:
    - Receive trade candidates.
    - Build structured trade context.
    - Generate AI analysis prompts.
    - Communicate with the configured LLM provider.
    - Validate and return structured AI responses.

The orchestrator does not execute trades or modify trading
strategy calculations.

Logging:
    - Tracks each analysis stage.
    - Records execution duration.
    - Captures provider, decision and confidence metadata.
    - Logs failures with exception details.

Caching:
    - No caching is implemented.
    - AI analysis depends on changing market conditions and trade context.
      Reusing cached responses could produce stale decisions.
"""

import logging
from time import perf_counter
from typing import Any

from app.ai.context.builder import ContextBuilder
from app.ai.llm_models.llm_response import LLMResponse
from app.ai.prompts.trade_prompt import TradePrompt
from app.ai.providers.provider_factory import ProviderFactory


logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Central coordinator for AthenaAI's LLM analysis pipeline.

    Connects context preparation, prompt generation, provider
    communication and response validation.

    The selected LLM provider is initialized once when the
    orchestrator instance is created.
    """

    def __init__(self):
        """
        Initialize the AI orchestration components.

        Creates:
            - ContextBuilder: Prepares trade analysis context.
            - LLM Provider: Handles communication with the configured
              language model.
        """

        start_time = perf_counter()

        logger.info(
            "AI orchestrator initialization started",
            extra={
                "event": "ai_orchestrator_initialization_started",
            },
        )

        try:
            self.context_builder = ContextBuilder()
            self.provider = ProviderFactory.get_provider()

            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.info(
                "AI orchestrator initialized successfully",
                extra={
                    "event": "ai_orchestrator_initialization_completed",
                    "provider": self.provider.__class__.__name__,
                    "status": "success",
                    "duration_ms": duration_ms,
                },
            )

        except Exception:
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "AI orchestrator initialization failed",
                extra={
                    "event": "ai_orchestrator_initialization_failed",
                    "status": "failed",
                    "duration_ms": duration_ms,
                },
            )
            raise

    async def analyze_trade(
        self,
        trade: dict[str, Any],
    ) -> LLMResponse:
        """
        Analyse a trade candidate using the configured LLM provider.

        Args:
            trade: Trade candidate containing symbol, scores,
                   technical metrics and other available context.

        Returns:
            LLMResponse: Validated AI trade analysis result.

        Raises:
            ValueError: If the trade context or response is invalid.
            Exception: If context preparation, provider communication
                       or response processing fails.
        """

        start_time = perf_counter()

        symbol = (
            trade.get("symbol", "UNKNOWN")
            if isinstance(trade, dict)
            else "UNKNOWN"
        )

        provider_name = self.provider.__class__.__name__

        logger.info(
            "AI trade analysis started",
            extra={
                "event": "ai_trade_analysis_started",
                "symbol": symbol,
                "provider": provider_name,
            },
        )

        try:
            # Step 1: Prepare structured trade context.
            stage_start = perf_counter()

            context = await self.context_builder.build_context(trade)

            context_duration_ms = round(
                (perf_counter() - stage_start) * 1000,
                2,
            )

            logger.info(
                "AI trade context prepared",
                extra={
                    "event": "ai_trade_context_prepared",
                    "symbol": symbol,
                    "context_field_count": len(context),
                    "duration_ms": context_duration_ms,
                },
            )

            # Step 2: Generate the AI analysis prompt.
            stage_start = perf_counter()

            prompt = TradePrompt.build(context)

            prompt_duration_ms = round(
                (perf_counter() - stage_start) * 1000,
                2,
            )

            logger.info(
                "AI trade analysis prompt generated",
                extra={
                    "event": "ai_trade_prompt_generated",
                    "symbol": symbol,
                    "prompt_length": len(prompt),
                    "duration_ms": prompt_duration_ms,
                },
            )

            # Step 3: Send the prompt to the configured LLM provider.
            stage_start = perf_counter()

            response = await self.provider.analyze_trade(prompt)

            provider_duration_ms = round(
                (perf_counter() - stage_start) * 1000,
                2,
            )

            logger.info(
                "AI provider analysis completed",
                extra={
                    "event": "ai_provider_analysis_completed",
                    "symbol": symbol,
                    "provider": provider_name,
                    "duration_ms": provider_duration_ms,
                },
            )

            # Step 4: Validate the provider response.
            stage_start = perf_counter()

            result = LLMResponse(**response)

            validation_duration_ms = round(
                (perf_counter() - stage_start) * 1000,
                2,
            )

            logger.info(
                "AI response validation completed",
                extra={
                    "event": "ai_response_validation_completed",
                    "symbol": symbol,
                    "validation_status": "success",
                    "duration_ms": validation_duration_ms,
                },
            )

            # Step 5: Record final analysis result.
            total_duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.info(
                "AI trade analysis completed successfully",
                extra={
                    "event": "ai_trade_analysis_completed",
                    "symbol": symbol,
                    "provider": provider_name,
                    "decision": result.decision,
                    "confidence": result.confidence,
                    "status": "success",
                    "duration_ms": total_duration_ms,
                },
            )

            return result

        except Exception:
            total_duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "AI trade analysis failed",
                extra={
                    "event": "ai_trade_analysis_failed",
                    "symbol": symbol,
                    "provider": provider_name,
                    "status": "failed",
                    "duration_ms": total_duration_ms,
                },
            )

            raise