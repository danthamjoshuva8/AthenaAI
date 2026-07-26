from typing import List

from app.ai.orchestrator import AIOrchestrator
from app.ai.context_builder.context_builder import ContextBuilder


class AIBatchService:

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.ai = AIOrchestrator()

    async def evaluate_trades(self, trades: List[dict]):

        results = []

        for trade in trades:

            ai_result = await self.ai.analyze_trade(
                trade=trade
            )

            trade["ai"] = ai_result.model_dump()

            trade["ai_confidence"] = ai_result.confidence

            trade["ai_decision"] = ai_result.decision

            results.append(trade)

        return results