"""
Target 2R Exit Strategy for AthenaAI.

Closes the entire remaining position when:
    1. Price reaches the 2R target.
    2. A SELL signal is generated.

Exit priority:
    - 2R target is checked first.
    - SELL signal is checked second.

The strategy does not execute broker orders.
It returns exit decisions to the backtesting engine.
"""

import logging
from time import perf_counter
from typing import Any

from app.backtesting.exits.exit_strategy import ExitStrategy


logger = logging.getLogger(__name__)


class Target2RStrategy(ExitStrategy):
    """
    Exit the entire remaining position at the 2R target
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
            position: Current position containing target_2r
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

        try:
            remaining_quantity = position["remaining_quantity"]

            # Condition 1: Price reaches the 2R target.
            if row["high"] >= position["target_2r"]:

                exit_price = position["target_2r"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": remaining_quantity,
                    "exit_price": exit_price,
                    "exit_reason": "TARGET_2R",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "2R target reached. Closing entire position",
                    extra={
                        "event": "exit_target_2r_hit",
                        "strategy": "TARGET_2R",
                        "symbol": symbol,
                        "exit_price": exit_price,
                        "sell_quantity": remaining_quantity,
                        "exit_reason": "TARGET_2R",
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
                        "strategy": "TARGET_2R",
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
                    "strategy": "TARGET_2R",
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
                "Target 2R exit strategy evaluation failed",
                extra={
                    "event": "exit_strategy_failed",
                    "strategy": "TARGET_2R",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )

            raise