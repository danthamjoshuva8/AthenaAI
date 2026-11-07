"""
Trail 2R Exit Strategy for AthenaAI.

Manages position exits in multiple stages.

Exit conditions:
    1. Sell 50% of the original quantity when price reaches 2R.
    2. Move the stop loss to the 2R target.
    3. Exit the remaining position when price reaches 3R.
    4. Exit the remaining position when price falls to the trailing stop.
    5. Exit the remaining position on a short MA SELL signal.

Exit priority:
    - Partial exit at 2R.
    - Final target at 3R.
    - Trailing stop.
    - Short MA SELL signal.

The strategy does not execute broker orders.
It returns exit decisions to the backtesting engine.
"""

import logging
from time import perf_counter
from typing import Any

from app.backtesting.exits.exit_strategy import ExitStrategy


logger = logging.getLogger(__name__)


class Trail2RStrategy(ExitStrategy):
    """
    Exit 50% of the position at 2R and trail the remaining
    position using the 2R target as the stop loss.

    The remaining position exits at 3R, trailing stop,
    or short MA SELL signal.
    """

    def process(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Evaluate partial exit, final target and trailing stop conditions.

        Args:
            position: Current position containing quantity,
                      remaining_quantity, target_2r, target_3r,
                      stop_loss and partial_exit_2r.

            row: Current market candle containing high, low,
                 close and signal.

        Returns:
            dict | None:
                Exit decision when an exit condition is met.
                None when the position should remain open.
        """

        start_time = perf_counter()

        symbol = position.get("symbol", "UNKNOWN")

        try:
            # Step 1: Partial exit at 2R.
            if (
                not position["partial_exit_2r"]
                and row["high"] >= position["target_2r"]
            ):

                sell_quantity = min(
                    position["remaining_quantity"],
                    max(1, position["quantity"] // 2),
                )

                position["partial_exit_2r"] = True
                position["stop_loss"] = position["target_2r"]

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
                    "Partial position exit triggered at 2R. Trailing stop activated",
                    extra={
                        "event": "trail_2r_partial_exit",
                        "strategy": "TRAIL_2R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
                        "remaining_quantity": (
                            position["remaining_quantity"] - sell_quantity
                        ),
                        "new_stop_loss": position["stop_loss"],
                        "exit_reason": "TARGET_2R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Step 2: Final target at 3R.
            if row["high"] >= position["target_3r"]:

                sell_quantity = position["remaining_quantity"]

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
                    "3R target reached. Closing remaining position",
                    extra={
                        "event": "trail_2r_target_3r_hit",
                        "strategy": "TRAIL_2R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
                        "exit_reason": "TARGET_3R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Step 3: Exit when price reaches the trailing stop.
            if (
                position["partial_exit_2r"]
                and row["low"] <= position["stop_loss"]
            ):

                sell_quantity = position["remaining_quantity"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": sell_quantity,
                    "exit_price": position["stop_loss"],
                    "exit_reason": "TRAIL_STOP",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Trailing stop reached. Closing remaining position",
                    extra={
                        "event": "trail_2r_stop_hit",
                        "strategy": "TRAIL_2R",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "stop_loss": position["stop_loss"],
                        "sell_quantity": sell_quantity,
                        "exit_reason": "TRAIL_STOP",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Step 4: Exit on short MA SELL signal.
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
                    "Short MA SELL signal. Closing remaining position",
                    extra={
                        "event": "trail_2r_short_ma_break",
                        "strategy": "TRAIL_2R",
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
                "No exit condition met. Position remains open",
                extra={
                    "event": "trail_2r_condition_not_met",
                    "strategy": "TRAIL_2R",
                    "symbol": symbol,
                    "partial_exit_2r": position["partial_exit_2r"],
                    "stop_loss": position.get("stop_loss"),
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
                "Trail 2R exit strategy evaluation failed",
                extra={
                    "event": "exit_strategy_failed",
                    "strategy": "TRAIL_2R",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )

            raise