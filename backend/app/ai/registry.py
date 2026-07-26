"""
AI Agent Registry

Maintains all registered AI agents.
"""

from typing import Dict, List

from app.ai.agents.strategy_agent import StrategyAgent
from app.ai.agents.technical_agent import TechnicalAgent
from app.ai.interfaces import AIAgent
from app.ai.agents.market_agent import MarketAgent
from app.ai.agents.news_agent import NewsAgent
from app.ai.agents.sentiment_agent import SentimentAgent


class AgentRegistry:
    """
    Registry for all AI agents.
    """

    def __init__(self):
        self._agents: Dict[str, AIAgent] = {}

    def register(self, agent: AIAgent) -> None:
        self._agents[agent.name] = agent

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def get(self, name: str) -> AIAgent | None:
        return self._agents.get(name)

    def get_all(self) -> List[AIAgent]:
        return list(self._agents.values())

    def clear(self) -> None:
        self._agents.clear()

    def count(self) -> int:
        return len(self._agents)

    def register_default_agents(self) -> None:
        """
        Register all built-in AI agents.
        """

        self.clear()

        self.register(TechnicalAgent())

        self.register(StrategyAgent())

        self.register(MarketAgent())

        self.register(NewsAgent())

        self.register(SentimentAgent())


# Global registry instance
agent_registry = AgentRegistry()

# Register default agents
agent_registry.register_default_agents()