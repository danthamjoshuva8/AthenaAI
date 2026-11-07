
import logging
import math
import time

from app.config.trading_cost_config import TradingCostConfig


logger = logging.getLogger(__name__)


class TradingCostEngine:
    """
    Calculates brokerage, taxes, DP charges, and slippage
    for stock trades using the configured trading costs.
    """

    def __init__(self):
        """Initialize trading cost configuration."""

        self.config = TradingCostConfig()

        logger.info(
            "Trading Cost Engine initialized",
            extra={
                "enabled": self.config.enabled,
                "trading_type": self.config.trading_type
            }
        )

    @staticmethod
    def _validate_value(value, field_name):
        """Validate monetary input values."""

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{field_name} must be a finite non-negative number"
            )

        return float(value)

    def _zero_cost_result(self):
        """Return zero costs when cost calculation is disabled."""

        return {
            "brokerage": 0,
            "stt": 0,
            "exchange": 0,
            "sebi": 0,
            "stamp": 0,
            "gst": 0,
            "dp_charge": 0,
            "slippage": 0,
            "total": 0
        }

    def calculate_trade_cost(
        self,
        buy_value: float,
        sell_value: float
    ) -> dict:
        """
        Calculate total transaction costs for a completed trade.

        Args:
            buy_value: Total purchase turnover.
            sell_value: Total selling turnover.

        Returns:
            Dictionary containing individual cost components
            and total transaction cost.
        """

        start_time = time.perf_counter()

        try:
            buy_value = self._validate_value(
                buy_value,
                "Buy value"
            )

            sell_value = self._validate_value(
                sell_value,
                "Sell value"
            )

            # -----------------------------------------
            # 1. Check whether trading costs are enabled
            # -----------------------------------------

            if not self.config.enabled:
                logger.debug(
                    "Trading cost calculation skipped: costs disabled",
                    extra={
                        "buy_value": buy_value,
                        "sell_value": sell_value
                    }
                )

                return self._zero_cost_result()

            # -----------------------------------------
            # 2. Calculate Brokerage
            # -----------------------------------------

            if self.config.trading_type == "delivery":
                brokerage = 0

            else:
                buy_brokerage = min(
                    buy_value * 0.0003,
                    20
                )

                sell_brokerage = min(
                    sell_value * 0.0003,
                    20
                )

                brokerage = (
                    buy_brokerage + sell_brokerage
                )

            # -----------------------------------------
            # 3. Calculate Turnover
            # -----------------------------------------

            turnover = buy_value + sell_value

            # -----------------------------------------
            # 4. Calculate Taxes
            # -----------------------------------------

            stt = (
                turnover
                * self.config.stt_percent
                / 100
            )

            exchange = (
                turnover
                * self.config.exchange_percent
                / 100
            )

            sebi = (
                turnover
                * self.config.sebi_percent
                / 100
            )

            stamp = (
                buy_value
                * self.config.stamp_percent
                / 100
            )

            gst = (
                brokerage + exchange
            ) * self.config.gst_percent / 100

            # -----------------------------------------
            # 5. Calculate DP Charges
            # -----------------------------------------

            dp = 0

            if self.config.trading_type == "delivery":
                dp = self.config.dp_charge

            # -----------------------------------------
            # 6. Calculate Slippage
            # -----------------------------------------

            slippage = (
                turnover
                * self.config.slippage_percent
                / 100
            )

            # -----------------------------------------
            # 7. Calculate Total Transaction Cost
            # -----------------------------------------

            costs = {
                "brokerage": round(brokerage, 2),
                "stt": round(stt, 2),
                "exchange": round(exchange, 2),
                "sebi": round(sebi, 2),
                "stamp": round(stamp, 2),
                "gst": round(gst, 2),
                "dp_charge": round(dp, 2),
                "slippage": round(slippage, 2)
            }

            # Sum rounded components so the total reconciles
            # with the displayed individual cost components.
            costs["total"] = round(
                sum(costs.values()),
                2
            )

            logger.info(
                "Trading cost calculated successfully",
                extra={
                    "trading_type": self.config.trading_type,
                    "buy_value": buy_value,
                    "sell_value": sell_value,
                    "turnover": turnover,
                    **costs,
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return costs

        except Exception:
            logger.exception(
                "Trading cost calculation failed",
                extra={
                    "buy_value": buy_value,
                    "sell_value": sell_value
                }
            )
            raise
