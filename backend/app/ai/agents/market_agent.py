"""
Market Intelligence Agent

Analyzes the overall market condition before allowing
a trade to proceed.
"""

from typing import Dict

from app.ai.agents.base_agent import BaseAgent
from app.ai.context import AIContext


class MarketAgent(BaseAgent):

    async def analyze(
        self,
        context: AIContext
    ) -> Dict:

        candidate = context.trade

        confidence = self._calculate_market_confidence(candidate)

        summary = self._market_summary(candidate)

        self.add_context_message(
            context,
            summary,
            confidence
        )

        return self.create_result(
            confidence=confidence,
            summary=summary,
            data={
                "market_score": candidate.market_score
            }
        )

    def _calculate_market_confidence(
        self,
        candidate
    ) -> float:

        score = candidate.market_score

        if score >= 25:
            return 95

        if score >= 20:
            return 88

        if score >= 15:
            return 80

        if score >= 10:
            return 70

        return 55

    def _market_summary(
        self,
        candidate
    ) -> str:

        score = candidate.market_score

        if score >= 25:
            return "Excellent market conditions."

        if score >= 20:
            return "Strong bullish market."

        if score >= 15:
            return "Healthy market."

        if score >= 10:
            return "Neutral market."

        return "Weak market conditions."