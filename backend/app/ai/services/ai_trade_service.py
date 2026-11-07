
"""
AI Trade Service for AthenaAI.

Acts as the application-level service between the trading system
and the AI analysis engine.

Responsibilities:
    - Receive trade candidates from the trading system.
    - Submit trades for AI analysis through AIOrchestrator.
    - Attach AI analysis results to the original trade.
    - Return structured AI analysis results.

This service does not perform technical analysis or call the
LLM provider directly.
"""

import logging
from typing import Any

from app.ai.orchestrator import AIOrchestrator
from app.ai.llm_models.llm_response import LLMResponse


logger = logging.getLogger(__name__)


class AITradeService:
    """
    Application service responsible for AI-based trade evaluation.

    AIOrchestrator handles context preparation, prompt generation,
    provider communication and response validation.

    AITradeService integrates the resulting analysis with the
    trading application's trade data.
    """

    def __init__(self):
        """
        Initialize the AI trade service.

        Creates the AI orchestrator responsible for trade analysis.
        """

        self.ai = AIOrchestrator()

        logger.info("AITradeService initialized successfully.")

    async def evaluate_trade(
        self,
        trade: dict[str, Any]
    ) -> LLMResponse:
        """
        Evaluate a trade candidate using the configured AI provider.

        Args:
            trade: Trade candidate containing symbol, strategy scores,
                   technical metrics and other available trade context.

        Returns:
            LLMResponse: Structured AI analysis result.

        Raises:
            Exception: Propagates errors from context preparation,
                       provider communication or response validation.
        """

        symbol = trade.get("symbol", "UNKNOWN")

        logger.info(
            "Starting AI trade evaluation | Symbol: %s",
            symbol,
        )

        try:
            # Submit the trade to the AI orchestration pipeline.
            result = await self.ai.analyze_trade(trade)

            # Attach AI analysis results to the original trade.
            trade.update({
                "ai_decision": result.decision,
                "ai_confidence": result.confidence,
                "ai_reasoning": result.reasoning,
                "ai_strengths": result.strengths,
                "ai_weaknesses": result.weaknesses,
                "ai_risks": result.risks,
                "ai_recommendation": result.recommendation,
                "ai_execution_priority": result.execution_priority,
            })

            logger.info(
                "AI trade evaluation completed | Symbol: %s | "
                "Decision: %s | Confidence: %s",
                symbol,
                result.decision,
                result.confidence,
            )

            return result

        except Exception:
            logger.exception(
                "AI trade evaluation failed | Symbol: %s",
                symbol,
            )
            raise
