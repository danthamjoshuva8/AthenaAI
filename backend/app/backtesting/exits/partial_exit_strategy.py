"""
Partial Exit Strategy for AthenaAI.

Manages position exits in multiple stages.

Exit conditions:
    1. First 50% of the original quantity exits at 2R.
    2. Remaining position exits at 3R.
    3. Remaining position exits if a short MA SELL signal occurs.

The strategy evaluates exit conditions in the above priority order.

The strategy does not execute broker orders.
It returns exit decisions to the backtesting engine.
"""

import logging
from time import perf_counter
from typing import Any

from app.backtesting.exits.exit_strategy import ExitStrategy


logger = logging.getLogger(__name__)


class PartialExitStrategy(ExitStrategy):
    """
    Exit a position partially at 2R and fully at 3R.

    If a SELL signal occurs before the 3R target,
    the remaining position is closed at the candle close.
    """

    def process(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Evaluate partial and full position exit conditions.

        Args:
            position: Current position containing original quantity,
                      remaining quantity, targets and partial exit flags.

            row: Current market candle containing high, close and signal.

        Returns:
            dict | None:
                Exit decision when an exit condition is met.
                None when the position should remain open.
        """

        start_time = perf_counter()

        symbol = position.get("symbol", "UNKNOWN")

        try:
            # First 50% exit at 2R.
            if (
                not position["partial_exit_2r"]
                and row["high"] >= position["target_2r"]
            ):

                sell_quantity = min(
                    position["remaining_quantity"],
                    max(1, round(position["quantity"] * 0.5)),
                )

                position["partial_exit_2r"] = True

                result = {
                    "close_position": False,
                    "action": "PARTIAL_CLOSE",
                    "sell_quantity": sell_quantity,
                    "exit_price": position["target_2r"],
                    "exit_reason": "TARGET_2R",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Partial exit triggered at 2R",
                    extra={
                        "event": "partial_exit_2r_hit",
                        "strategy": "PARTIAL_2R_3R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
                        "remaining_quantity": position["remaining_quantity"],
                        "exit_reason": "TARGET_2R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Remaining position exits at 3R.
            if (
                position["partial_exit_2r"]
                and not position["partial_exit_3r"]
                and row["high"] >= position["target_3r"]
            ):

                sell_quantity = position["remaining_quantity"]

                position["partial_exit_3r"] = True

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": sell_quantity,
                    "exit_price": position["target_3r"],
                    "exit_reason": "TARGET_3R",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Remaining position closed at 3R",
                    extra={
                        "event": "partial_exit_3r_hit",
                        "strategy": "PARTIAL_2R_3R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
                        "exit_reason": "TARGET_3R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Close remaining position on short MA SELL signal.
            if row["signal"] == "SELL":

                sell_quantity = position["remaining_quantity"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": sell_quantity,
                    "exit_price": row["close"],
                    "exit_reason": "SHORT_MA_BREAK",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Remaining position closed due to short MA SELL signal",
                    extra={
                        "event": "partial_exit_short_ma_break",
                        "strategy": "PARTIAL_2R_3R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
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
                "No partial exit condition met",
                extra={
                    "event": "partial_exit_condition_not_met",
                    "strategy": "PARTIAL_2R_3R",
                    "symbol": symbol,
                    "partial_exit_2r": position["partial_exit_2r"],
                    "partial_exit_3r": position["partial_exit_3r"],
                    "remaining_quantity": position["remaining_quantity"],
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
                "Partial exit strategy evaluation failed",
                extra={
                    "event": "exit_strategy_failed",
                    "strategy": "PARTIAL_2R_3R",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )

            raise