
import logging
import math
import time

import pandas as pd

from app.config.trade_quality_config import TradeQualityConfig
from app.models.market_state import MarketState


logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """
    Analyzes NIFTY market conditions and determines the overall market regime.

    Evaluates:
        - Price distance from long-term moving average.
        - Long-term moving average slope.
        - Price position relative to MA20.
        - Momentum.
        - ATR-based volatility.

    Returns a MarketState containing market trend and indicator values.
    """

    def __init__(self):
        """Initialize market analysis configuration."""

        self.config = TradeQualityConfig().market_context

        logger.info(
            "MarketAnalyzer initialized",
            extra={
                "event": "market_analyzer_initialized",
                "long_ma_period": self.config.long_ma_period,
                "trend_lookback_days": self.config.trend_lookback_days
            }
        )

    def analyze(
        self,
        nifty_df: pd.DataFrame
    ) -> MarketState:
        """
        Analyze NIFTY market conditions.

        Args:
            nifty_df: DataFrame containing calculated market indicators.

        Returns:
            MarketState: Calculated market regime and indicator values.

        Raises:
            TypeError: If input is not a pandas DataFrame.
            ValueError: If required columns or indicator values are invalid.
        """

        start_time = time.perf_counter()

        try:
            # --------------------------------------------------
            # Step 1: Validate input
            # --------------------------------------------------

            if not isinstance(nifty_df, pd.DataFrame):
                raise TypeError(
                    "nifty_df must be a pandas DataFrame."
                )

            actual_rows = len(nifty_df)

            required_rows = max(
                self.config.long_ma_period,
                self.config.trend_lookback_days + 1
            )

            logger.info(
                "Market analysis started",
                extra={
                    "event": "market_analysis_started",
                    "actual_rows": actual_rows,
                    "required_rows": required_rows
                }
            )

            # --------------------------------------------------
            # Step 2: Check historical data availability
            # --------------------------------------------------

            if actual_rows < required_rows:
                logger.warning(
                    "Insufficient NIFTY history",
                    extra={
                        "event": "market_analysis_insufficient_data",
                        "actual_rows": actual_rows,
                        "required_rows": required_rows
                    }
                )

                return MarketState(
                    trend="UNKNOWN",
                    trend_score=0,
                    breadth_score=0,
                    strength_score=0,
                    volatility_score=0,
                    total_score=0
                )

            # --------------------------------------------------
            # Step 3: Validate required indicator columns
            # --------------------------------------------------

            ma_column = f"MA{self.config.long_ma_period}"

            required_columns = [
                "Close",
                ma_column,
                "MA20",
                "Momentum20",
                "ATRPercent"
            ]

            missing_columns = [
                column
                for column in required_columns
                if column not in nifty_df.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"Missing required market indicators: {missing_columns}"
                )

            # --------------------------------------------------
            # Step 4: Retrieve latest and historical observations
            # --------------------------------------------------

            latest = nifty_df.iloc[-1]

            previous = nifty_df.iloc[
                -(self.config.trend_lookback_days + 1)
            ]

            # --------------------------------------------------
            # Step 5: Validate indicator values
            # --------------------------------------------------

            def get_valid_number(value, name):
                """
                Convert an indicator into a finite numeric value.
                Reject missing, boolean, and non-numeric values.
                """

                if pd.isna(value) or isinstance(value, bool):
                    raise ValueError(
                        f"Invalid market indicator: {name}={value}"
                    )

                try:
                    numeric_value = float(value)

                except (TypeError, ValueError, OverflowError) as ex:
                    raise ValueError(
                        f"Non-numeric market indicator: {name}={value}"
                    ) from ex

                if not math.isfinite(numeric_value):
                    raise ValueError(
                        f"Non-finite market indicator: {name}={value}"
                    )

                return numeric_value

            close = get_valid_number(
                latest["Close"],
                "Close"
            )

            ma = get_valid_number(
                latest[ma_column],
                ma_column
            )

            ma_old = get_valid_number(
                previous[ma_column],
                f"Previous_{ma_column}"
            )

            ma20 = get_valid_number(
                latest["MA20"],
                "MA20"
            )

            momentum = get_valid_number(
                latest["Momentum20"],
                "Momentum20"
            )

            atr = get_valid_number(
                latest["ATRPercent"],
                "ATRPercent"
            )

            if close <= 0 or ma <= 0 or ma_old <= 0 or ma20 <= 0:
                raise ValueError(
                    "Close and moving average values must be positive."
                )

            if atr < 0:
                raise ValueError(
                    "ATR percentage cannot be negative."
                )

            # --------------------------------------------------
            # Step 6: Calculate price distance from long-term MA
            # --------------------------------------------------

            distance_percent = (
                (close - ma) / ma
            ) * 100

            # --------------------------------------------------
            # Step 7: Initialize scoring components
            # --------------------------------------------------

            trend_score = self.config.bearish_trend_score

            # Reserved for future market breadth implementation.
            strength_score = 0

            # Existing implementation uses raw ATR percentage.
            volatility_score = atr

            # --------------------------------------------------
            # Step 8: Score price distance from long-term MA
            # --------------------------------------------------

            if distance_percent >= self.config.ma_distance_strong:
                trend_score += 10

            elif distance_percent >= self.config.ma_distance_medium:
                trend_score += 7

            elif distance_percent >= self.config.ma_distance_weak:
                trend_score += 4

            # --------------------------------------------------
            # Step 9: Calculate long-term moving average slope
            # --------------------------------------------------

            slope_percent = (
                (ma - ma_old) / ma_old
            ) * 100

            # --------------------------------------------------
            # Step 10: Score moving average slope
            # --------------------------------------------------

            if slope_percent >= self.config.ma_slope_strong:
                trend_score += 8

            elif slope_percent >= self.config.ma_slope_medium:
                trend_score += 4

            elif slope_percent >= self.config.ma_slope_weak:
                trend_score += 2

            # --------------------------------------------------
            # Step 11: Evaluate price position relative to MA20
            # --------------------------------------------------

            if close > ma20:
                trend_score += 4

            # --------------------------------------------------
            # Step 12: Evaluate market momentum
            # --------------------------------------------------

            if momentum >= self.config.momentum_strong:
                trend_score += 5

            elif momentum >= self.config.momentum_medium:
                trend_score += 3

            elif momentum >= self.config.momentum_weak:
                trend_score += 1

            # --------------------------------------------------
            # Step 13: Evaluate market volatility
            # --------------------------------------------------

            if 1 <= atr <= 2:
                trend_score += 4

            elif 2 < atr <= 3:
                trend_score += 3

            elif 3 < atr <= 4:
                trend_score += 2

            # --------------------------------------------------
            # Step 14: Apply maximum market score
            # --------------------------------------------------

            total_score = min(
                trend_score,
                self.config.max_market_score
            )

            # --------------------------------------------------
            # Step 15: Determine market regime
            # --------------------------------------------------

            if total_score >= self.config.bullish_threshold:
                trend = "BULLISH"

            elif total_score >= self.config.neutral_threshold:
                trend = "NEUTRAL"

            else:
                trend = "BEARISH"

            # --------------------------------------------------
            # Step 16: Construct market state
            # --------------------------------------------------

            market_state = MarketState(
                trend=trend,
                trend_score=trend_score,
                breadth_score=0,
                strength_score=strength_score,
                volatility_score=volatility_score,
                total_score=total_score,
                stocks_above_ma=0,
                ma_distance_percent=distance_percent,
                ma_slope_percent=slope_percent,
                momentum_percent=momentum,
                atr_percent=atr
            )

            # --------------------------------------------------
            # Step 17: Log successful analysis
            # --------------------------------------------------

            duration = time.perf_counter() - start_time

            logger.info(
                "Market analysis completed",
                extra={
                    "event": "market_analysis_completed",
                    "trend": trend,
                    "trend_score": trend_score,
                    "total_score": total_score,
                    "ma_distance_percent": round(distance_percent, 2),
                    "ma_slope_percent": round(slope_percent, 2),
                    "momentum_percent": round(momentum, 2),
                    "atr_percent": round(atr, 2),
                    "duration_seconds": round(duration, 4)
                }
            )

            return market_state

        except Exception:
            duration = time.perf_counter() - start_time

            logger.exception(
                "Market analysis failed",
                extra={
                    "event": "market_analysis_failed",
                    "duration_seconds": round(duration, 4)
                }
            )

            raise
