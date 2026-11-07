
import logging
import math
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds a standardized AI context dictionary from trade data.

    Organizes trade information into:
        - Trade details.
        - Strategy scores.
        - Technical analysis.
        - Advanced technical indicators.
        - Market and sector context.
        - Company information.
        - Historical news.

    Optional fields are retained with None values when unavailable.

    This class performs data transformation only. It does not fetch
    external data, access the database, or require caching.
    """

    async def build_context(
        self,
        trade: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build structured AI context from a trade candidate.

        Args:
            trade: Dictionary containing trade, technical,
                   market, sector, and company information.

        Returns:
            dict[str, Any]: Standardized AI context dictionary.

        Raises:
            TypeError: If trade is not a dictionary.
            ValueError: If trade data is invalid.
        """

        start_time = perf_counter()

        # Step 1: Validate the input trade data.
        if not isinstance(trade, dict):
            logger.error(
                "AI context construction rejected: invalid trade input",
                extra={
                    "event": "ai_context_validation_failed",
                    "service": "context_builder",
                    "reason": "invalid_trade_type",
                },
            )

            raise TypeError(
                "Trade data must be provided as a dictionary."
            )

        if not trade:
            logger.error(
                "AI context construction rejected: empty trade data",
                extra={
                    "event": "ai_context_validation_failed",
                    "service": "context_builder",
                    "reason": "empty_trade_data",
                },
            )

            raise ValueError(
                "Trade data cannot be empty."
            )

        symbol = trade.get("symbol")

        if not isinstance(symbol, str) or not symbol.strip():
            logger.error(
                "AI context construction rejected: invalid symbol",
                extra={
                    "event": "ai_context_validation_failed",
                    "service": "context_builder",
                    "reason": "missing_or_invalid_symbol",
                },
            )

            raise ValueError(
                "Trade symbol is missing or invalid."
            )

        symbol = symbol.strip().upper()

        # Step 2: Log the beginning of context construction.
        logger.info(
            "AI context construction started",
            extra={
                "event": "ai_context_build_started",
                "service": "context_builder",
                "symbol": symbol,
            },
        )

        try:
            # Step 3: Prepare frequently used technical values.
            volume_ratio = self._round_value(
                trade.get("volume_ratio", 0)
            )

            body_percent = self._round_value(
                trade.get("body_percent", 0)
            )

            distance_from_ma = self._round_value(
                trade.get("distance_from_ma", 0)
            )

            # Step 4: Build standardized trade context.
            context = {

                # ==========================
                # Trade Details
                # ==========================

                "symbol": symbol,
                "entry_date": (
                    str(trade.get("entry_date"))
                    if trade.get("entry_date") is not None
                    else None
                ),
                "entry_price": trade.get("entry_price"),
                "stop_loss": trade.get("stop_loss"),
                "risk_per_share": trade.get("risk_per_share"),
                "target_2r": trade.get("target_2r"),
                "target_3r": trade.get("target_3r"),

                # ==========================
                # Strategy Scores
                # ==========================

                "strategy_score": trade.get("total_score"),
                "market_score": trade.get("market_score"),
                "sector_score": trade.get("sector_score"),

                # ==========================
                # Technical Analysis
                # ==========================

                "volume_ratio": volume_ratio,
                "body_percent": body_percent,
                "distance_from_ma": distance_from_ma,

                "volume_confirmation": trade.get(
                    "volume_confirmation"
                ),
                "quality_pass": trade.get("quality_pass"),

                # ==========================
                # Advanced Technical Indicators
                # ==========================

                "atr": trade.get("atr"),
                "atr_percent": trade.get("atr_percent"),

                "distance_from_ath": trade.get("distance_from_ath"),
                "breakout_percent": trade.get("breakout_percent"),

                "ma15_slope": trade.get("ma15_slope"),
                "ma30_slope": trade.get("ma30_slope"),
                "ma150_slope": trade.get("ma150_slope"),

                "distance_from_15ma": trade.get("distance_from_15ma"),
                "distance_from_30ma": trade.get("distance_from_30ma"),
                "distance_from_150ma": trade.get("distance_from_150ma"),

                # ==========================
                # Market and Sector Context
                # ==========================

                "market_trend": trade.get("market_trend"),

                "market_ma_distance": trade.get("market_ma_distance"),
                "market_ma_slope": trade.get("market_ma_slope"),
                "market_momentum": trade.get("market_momentum"),
                "market_atr_percent": trade.get("market_atr_percent"),

                "sector_trend": trade.get("sector_trend"),

                # ==========================
                # Company Information
                # ==========================

                "sector": trade.get("sector"),
                "industry": trade.get("industry"),
                "market_cap": trade.get("market_cap"),

                # ==========================
                # Historical News
                # ==========================

                "historical_news": trade.get("historical_news", []),
            }

            # Step 5: Calculate execution duration.
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            # Step 6: Log successful context construction.
            logger.info(
                "AI context built successfully",
                extra={
                    "event": "ai_context_build_completed",
                    "service": "context_builder",
                    "symbol": symbol,
                    "status": "success",
                    "context_fields": len(context),
                    "has_historical_news": bool(
                        context["historical_news"]
                    ),
                    "duration_ms": duration_ms,
                },
            )

            return context

        except Exception:
            # Step 7: Log the exception without exposing trade data.
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "AI context construction failed",
                extra={
                    "event": "ai_context_build_failed",
                    "service": "context_builder",
                    "symbol": symbol,
                    "status": "failed",
                    "duration_ms": duration_ms,
                },
            )

            raise

    @staticmethod
    def _round_value(value: Any) -> float:
        """
        Round a technical indicator to two decimal places.

        Args:
            value: Numeric technical indicator.

        Returns:
            float: Rounded indicator value. Returns 0.0
                   when the value is None.

        Raises:
            TypeError: If the value is not numeric.
            ValueError: If the value is not finite.
        """

        # Step 1: Handle unavailable indicator values.
        if value is None:
            return 0.0

        # Step 2: Validate numeric input.
        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise TypeError(
                f"Technical indicator must be numeric: {value}"
            )

        if not math.isfinite(value):
            raise ValueError(
                f"Technical indicator must be finite: {value}"
            )

        # Step 3: Round the indicator value.
        return round(value, 2)
