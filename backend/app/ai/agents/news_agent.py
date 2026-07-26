from typing import Dict

from app.ai.agents.base_agent import BaseAgent
from app.ai.context import AIContext
from app.ai.services.news_service import NewsService


class NewsAgent(BaseAgent):

    def __init__(self):

        self.news_service = NewsService()

    async def analyze(
        self,
        context: AIContext
    ) -> Dict:

        result = await self.news_service.analyze(
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
                "news_score": result.news_score,
                "sentiment_score": result.sentiment_score,
                "headlines": result.headlines
            }
        )