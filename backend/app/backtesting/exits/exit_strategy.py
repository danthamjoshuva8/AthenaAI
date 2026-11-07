"""
Exit Strategy Base Class for AthenaAI.

Defines the common interface for all position exit strategies.

Responsibilities:
    - Establish a standard contract for exit strategies.
    - Require each strategy to implement position processing.
    - Ensure consistent exit decision structures across strategies.

The base class does not calculate exit prices, modify positions,
or execute trades.
"""

from abc import ABC, abstractmethod
from typing import Any


class ExitStrategy(ABC):
    """
    Abstract base class for AthenaAI position exit strategies.

    All concrete exit strategies must implement the process() method.

    Expected strategies may include:
        - PartialExitStrategy
        - Full3RStrategy
        - Trail2RStrategy
    """

    @abstractmethod
    def process(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate a position and determine whether an exit action is required.

        Args:
            position: Current position details, including entry price,
                      quantity, stop loss and other position metadata.

            row: Current market candle or price data used for evaluating
                 exit conditions.

        Returns:
            dict: Exit decision containing:

                {
                    "close_position": bool,
                    "action": str,
                    "exit_price": float,
                    "exit_reason": str,
                    "sell_quantity": int
                }

        Raises:
            NotImplementedError: If a concrete strategy does not
                                 implement this method.
        """
        raise NotImplementedError(
            "Exit strategies must implement the process() method."
        )