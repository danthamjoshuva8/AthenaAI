from app.ai.context_builder.context_builder import ContextBuilder
from app.ai.prompts.trade_prompt import TradePrompt
from app.ai.providers.provider_factory import ProviderFactory
from app.ai.llm_models.llm_response import LLMResponse


class AIOrchestrator:

    def __init__(self):

        self.context_builder = ContextBuilder()

        self.provider = ProviderFactory.get_provider()

    async def analyze_trade(
        self,
        trade: dict,
    ) -> LLMResponse:

        context = await self.context_builder.build_context(trade)

        prompt = TradePrompt.build(context)

        print("=" * 80)
        print(prompt)
        print("=" * 80)

        response = await self.provider.analyze_trade(prompt)

        return LLMResponse(**response)