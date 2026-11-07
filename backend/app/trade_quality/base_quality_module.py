from abc import ABC, abstractmethod

from app.models.trade_candidate import TradeCandidate


class BaseTradeQualityModule(ABC):
    """
    Defines the abstract interface for all trade quality modules.

    Each quality module must provide a unique module name and implement
    a method to calculate a score for a trade candidate.
    """

    @property
    @abstractmethod
    def module_name(self) -> str:
        """
        Return the unique identifier of the trade quality module.

        Returns:
            The module name used to identify the scoring component.
        """
        pass

    @abstractmethod
    def calculate_score(
        self,
        candidate: TradeCandidate
    ) -> float:
        """
        Calculate the quality score for a trade candidate.

        Args:
            candidate: Trade candidate containing the data required
                by the scoring module.

        Returns:
            The calculated quality score.
        """
        pass