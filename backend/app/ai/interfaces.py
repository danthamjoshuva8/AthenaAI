"""
AI Interfaces

Defines the contract that every AI agent must implement.
"""

from abc import ABC, abstractmethod

from app.ai.context import AIContext


class AIAgent(ABC):
    """
    Base interface for all AI agents.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique agent name.
        """
        pass

    @abstractmethod
    async def analyze(self, context: AIContext) -> dict:
        """
        Analyze the trade and return the agent result.

        Returns:
            Dictionary containing the analysis result.
        """
        pass

    async def initialize(self) -> None:
        """
        Optional initialization.
        Override if the agent needs setup.
        """
        return

    async def shutdown(self) -> None:
        """
        Optional cleanup.
        Override if required.
        """
        return