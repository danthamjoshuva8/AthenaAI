from abc import ABC
from abc import abstractmethod


class ExitStrategy(ABC):

    @abstractmethod
    def process(
        self,
        position: dict,
        row: dict
    ):
        """
        Returns

        {
            "close_position": bool,
            "action": "...",
            "exit_price": float,
            "exit_reason": "...",
            "sell_quantity": int
        }
        """
        pass