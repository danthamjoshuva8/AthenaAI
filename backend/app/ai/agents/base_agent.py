"""
Base AI Agent

Provides common functionality for all AI agents.
"""

from abc import abstractmethod
from typing import Any, Dict

from app.ai.context import AIContext
from app.ai.interfaces import AIAgent


class BaseAgent(AIAgent):
    """
    Base class for all AI agents.

    Every agent should inherit from this class instead of implementing
    the interface directly.
    """

    @property
    def name(self) -> str:
        """
        Default agent name.
        """
        return self.__class__.__name__

    @abstractmethod
    async def analyze(self, context: AIContext) -> Dict[str, Any]:
        """
        Perform AI analysis.

        Must be implemented by child agents.
        """
        raise NotImplementedError

    def create_result(
        self,
        confidence: float = 0.0,
        summary: str = "",
        data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Create a standard result object.
        """

        return {
            "agent": self.name,
            "confidence": confidence,
            "summary": summary,
            "data": data or {}
        }

    def add_context_message(
        self,
        context: AIContext,
        message: str,
        confidence: float | None = None,
    ) -> None:
        """
        Add a message to the shared AI context.
        """

        context.add_message(
            agent=self.name,
            message=message,
            confidence=confidence,
        )