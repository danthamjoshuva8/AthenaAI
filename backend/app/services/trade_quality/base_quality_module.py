from abc import ABC, abstractmethod

from app.models.trade_candidate import TradeCandidate


class BaseTradeQualityModule(ABC):

    @property
    @abstractmethod
    def module_name(self) -> str:
        pass

    @abstractmethod
    def calculate_score(
        self,
        candidate: TradeCandidate
    ) -> float:
        pass