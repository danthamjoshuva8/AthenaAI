from typing import Dict

from app.ai.agents.base_agent import BaseAgent
from app.ai.context import AIContext
from app.ai.services.sentiment_service import SentimentService


class SentimentAgent(BaseAgent):

    def __init__(self):

        self.sentiment_service = SentimentService()

    async def analyze(
        self,
        context: AIContext
    ) -> Dict:

        result = await self.sentiment_service.analyze(
            context.symbol
        )

        confidence = result.final_score()

        summary = result.summary

        self.add_context_message(
            context,
            summary,
            confidence
        )

        return self.create_result(
            confidence=confidence,
            summary=summary,
            data={
                "overall_sentiment": result.overall_sentiment,
                "sentiment_score": result.sentiment_score,
                "positive_signals": result.positive_signals,
                "negative_signals": result.negative_signals,
            }
        )