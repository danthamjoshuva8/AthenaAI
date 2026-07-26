from app.ai.context_builder.context_builder import ContextBuilder
from app.ai.orchestrator import AIOrchestrator


class AITradeService:

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.ai = AIOrchestrator()

    async def evaluate_trade(self, trade: dict):

        result = await self.ai.analyze_trade(trade)

        trade["ai_decision"] = result.decision
        trade["ai_confidence"] = result.confidence
        trade["ai_reasoning"] = result.reasoning
        trade["ai_strengths"] = result.strengths
        trade["ai_weaknesses"] = result.weaknesses
        trade["ai_risks"] = result.risks
        trade["ai_recommendation"] = result.recommendation
        trade["ai_execution_priority"] = result.execution_priority

        return result