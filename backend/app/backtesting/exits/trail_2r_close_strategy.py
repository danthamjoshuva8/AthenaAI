"""
Trail 2R Close Exit Strategy for AthenaAI.

Exit conditions:
    1. Activate trailing protection when daily candle closes above 2R.
    2. Move stop loss to the 2R target.
    3. Exit the entire remaining position at 3R.
    4. Exit when daily close falls below the trailing stop.
    5. Exit when a short MA SELL signal occurs.

Exit priority:
    - Activate trailing protection.
    - Check 3R target.
    - Check trailing stop.
    - Check short MA SELL signal.

The strategy does not execute broker orders.
It returns exit decisions to the backtesting engine.
"""

import logging
from time import perf_counter
from typing import Any

from app.backtesting.exits.exit_strategy import ExitStrategy


logger = logging.getLogger(__name__)


class Trail2RCloseStrategy(ExitStrategy):
    """
    Activate trailing protection after a daily close above 2R.

    The stop loss moves to the 2R target.
    The remaining position exits at 3R or when the trailing
    stop or short MA SELL condition is triggered.
    """

    def process(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Evaluate trailing protection and position exit conditions.

        Args:
            position: Current position containing target_2r,
                      target_3r, remaining_quantity and stop_loss.
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
            # Initialize trailing flag if missing.
            if "trail_active" not in position:
                position["trail_active"] = False

            # Activate trailing protection after daily close above 2R.
            if (
                not position["trail_active"]
                and row["close"] >= position["target_2r"]
            ):

                position["trail_active"] = True
                position["stop_loss"] = position["target_2r"]

                logger.info(
                    "Trailing protection activated at 2R",
                    extra={
                        "event": "trail_2r_activated",
                        "strategy": "TRAIL_2R_CLOSE",
                        "symbol": symbol,
                        "activation_price": row["close"],
                        "new_stop_loss": position["stop_loss"],
                    },
                )

            # Exit at 3R.
            if (
                position["trail_active"]
                and row["high"] >= position["target_3r"]
            ):

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
                    "3R target reached. Closing entire position",
                    extra={
                        "event": "trail_2r_close_target_3r_hit",
                        "strategy": "TRAIL_2R_CLOSE",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "sell_quantity": sell_quantity,
                        "exit_reason": "TARGET_3R",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Exit when daily close falls below the 2R trailing stop.
            if (
                position["trail_active"]
                and row["close"] < position["stop_loss"]
            ):

                sell_quantity = position["remaining_quantity"]

                result = {
                    "close_position": True,
                    "action": "CLOSE",
                    "sell_quantity": sell_quantity,
                    "exit_price": row["close"],
                    "exit_reason": "TRAIL_STOP",
                }

                duration_ms = round(
                    (perf_counter() - start_time) * 1000,
                    2,
                )

                logger.info(
                    "Daily close breached trailing stop. Closing position",
                    extra={
                        "event": "trail_2r_close_stop_hit",
                        "strategy": "TRAIL_2R_CLOSE",
                        "symbol": symbol,
                        "exit_price": result["exit_price"],
                        "stop_loss": position["stop_loss"],
                        "sell_quantity": sell_quantity,
                        "exit_reason": "TRAIL_STOP",
                        "duration_ms": duration_ms,
                    },
                )

                return result

            # Exit on short MA SELL signal.
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
                    "Short MA SELL signal. Closing entire position",
                    extra={
                        "event": "trail_2r_close_short_ma_break",
                        "strategy": "TRAIL_2R_CLOSE",
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
                    "event": "trail_2r_close_condition_not_met",
                    "strategy": "TRAIL_2R_CLOSE",
                    "symbol": symbol,
                    "trail_active": position["trail_active"],
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
                "Trail 2R close strategy evaluation failed",
                extra={
                    "event": "exit_strategy_failed",
                    "strategy": "TRAIL_2R_CLOSE",
                    "symbol": symbol,
                    "duration_ms": duration_ms,
                },
            )

            raise