"""
Strategy Intelligence Agent

Evaluates the historical quality of the current strategy setup.
"""

from typing import Any, Dict

from app.ai.agents.base_agent import BaseAgent
from app.ai.context import AIContext


class StrategyAgent(BaseAgent):
    """
    Strategy Intelligence Agent.

    Future responsibility:
    - Learn winning patterns
    - Learn losing patterns
    - Improve trade quality
    """

    async def analyze(
        self,
        context: AIContext
    ) -> Dict[str, Any]:

        trade_score = context.trade_score

        confidence = self._strategy_confidence(trade_score)

        summary = self._strategy_summary(confidence)

        self.add_context_message(
            context,
            summary,
            confidence
        )

        return self.create_result(
            confidence=confidence,
            summary=summary,
            data={
                "trade_score": trade_score,
                "strategy_quality": confidence
            }
        )

    def _strategy_confidence(
        self,
        trade_score: float
    ) -> float:
        """
        Placeholder strategy confidence.

        This will later be replaced by
        historical learning and ML.
        """

        return trade_score

    def _strategy_summary(
        self,
        confidence: float
    ) -> str:

        if confidence >= 90:
            return "Historical strategy confidence is excellent."

        if confidence >= 80:
            return "Historical strategy confidence is strong."

        if confidence >= 70:
            return "Historical strategy confidence is good."

        if confidence >= 60:
            return "Historical strategy confidence is acceptable."

        return "Historical strategy confidence is weak."