"""
Full 3R Exit Strategy for AthenaAI.

Closes the entire remaining position when:
    1. Price reaches the 3R target.
    2. A SELL signal is generated.

Exit priority:
    - 3R target is checked first.
    - SELL signal is checked second.

The strategy does not execute broker orders.
It only returns an exit decision to the backtesting engine.
"""

import logging
from time import perf_counter
from typing import Any

from app.backtesting.exits.exit_strategy import ExitStrategy


logger = logging.getLogger(__name__)


class Full3RStrategy(ExitStrategy):
    """
    Exit the entire remaining position at the 3R target
    or when the short moving average SELL signal occurs.
    """

    def process(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Evaluate whether the position should be fully closed.

        Args:
            position: Current position containing target_3r
                      and remaining_quantity.
            row: Current market candle containing high, close
                 and signal.

        Returns:
            dict | None:
                Exit decision when an exit condition is met.
                None when the position should remain open.
        """

        start_time = perf_counter()

        symbol = position.get("symbol", "UNKNOWN")
        remaining_quantity = position["remaining_quantity"]

        try:
            # Condition 1: Price reaches the 3R target.
            if row["high"] >= position["target_3r"]:

                exit_price = position["target_3r"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": remaining_quantity,
                    "exit_price": exit_price,
                    "exit_reason": "TARGET_3R",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Full 3R target reached. Closing entire position",
                    extra={
                        "event": "exit_target_3r_hit",
                        "strategy": "FULL_3R",
                        "symbol": symbol,
                        "exit_price": exit_price,
                        "sell_quantity": remaining_quantity,
                        "exit_reason": "TARGET_3R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Condition 2: Short moving average SELL signal.
            if row["signal"] == "SELL":

                exit_price = row["close"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": remaining_quantity,
                    "exit_price": exit_price,
                    "exit_reason": "SHORT_MA_BREAK",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Short moving average SELL signal. Closing entire position",
                    extra={
                        "event": "exit_short_ma_break",
                        "strategy": "FULL_3R",
                        "symbol": symbol,
                        "exit_price": exit_price,
                        "sell_quantity": remaining_quantity,
                        "exit_reason": "SHORT_MA_BREAK",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # No exit condition met.
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.debug(
                "No exit condition met. Position remains open",
                extra={
                    "event": "exit_condition_not_met",
                    "strategy": "FULL_3R",
                    "symbol": symbol,
                    "remaining_quantity": remaining_quantity,
                    "duration_ms": duration_ms,
                },
            )

            return None

        except Exception:
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "Full 3R exit strategy evaluation failed",
                extra={
                    "event": "exit_strategy_failed",
                    "strategy": "FULL_3R",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )

            raise