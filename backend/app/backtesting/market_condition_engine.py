
import logging
import time


logger = logging.getLogger(__name__)


class MarketConditionEngine:
    """
    Classifies market conditions for completed trades.

    NOTE:
    Current implementation uses trade profitability as a temporary
    proxy. This will later be replaced with actual market analysis
    using Nifty 50 / Nifty 200 market data.
    """

    def classify_market(
        self,
        trade: dict
    ) -> str:
        """
        Classify a trade as Bull or Bear based on its realized profit.

        Returns:
            str: Bull when profit is positive, otherwise Bear.
        """
        started_at = time.perf_counter()

        try:
            if not isinstance(trade, dict):
                raise TypeError(
                    "Trade must be provided as a dictionary."
                )

            if "profit" not in trade:
                raise ValueError(
                    "Trade dictionary must contain profit."
                )

            profit = trade["profit"]

            if isinstance(profit, bool) or not isinstance(
                profit, (int, float)
            ):
                raise ValueError(
                    "Trade profit must be a numeric value."
                )

            if not isinstance(profit, (int, float)):
                raise ValueError("Invalid trade profit.")

            if profit > 0:
                market_condition = "Bull"
            else:
                market_condition = "Bear"

            logger.debug(
                "Market condition classified",
                extra={
                    "event": "market_condition_classified",
                    "symbol": trade.get("symbol"),
                    "profit": profit,
                    "market_condition": market_condition,
                    "classification_method": "trade_profit_proxy",
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )

            return market_condition

        except Exception:
            logger.exception(
                "Market condition classification failed",
                extra={
                    "event": "market_condition_classification_failed",
                    "symbol": (
                        trade.get("symbol")
                        if isinstance(trade, dict)
                        else None
                    ),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise
