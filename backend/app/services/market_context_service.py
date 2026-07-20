import pandas as pd

from app.models.market_state import MarketState
from app.config.trade_quality_config import TradeQualityConfig


class MarketContextService:

    def __init__(self):

        self.config = TradeQualityConfig().market_context

    def analyze(
        self,
        nifty_df: pd.DataFrame
    ) -> MarketState:

        required = max(
            self.config.long_ma_period,
            self.config.trend_lookback_days + 1
        )

        print("Required rows:", required)
        print("Actual rows:", len(nifty_df))

        if len(nifty_df) < required:

            return MarketState(
                trend="UNKNOWN",
                trend_score=0,
                breadth_score=0,
                strength_score=0,
                volatility_score=0,
                total_score=0
            )
        latest = nifty_df.iloc[-1]
        trend_score = 0
        previous = nifty_df.iloc[
            -(self.config.trend_lookback_days + 1)
        ]

        close = latest["Close"]
        ma_column = f"MA{self.config.long_ma_period}"

        ma = latest[ma_column]

        distance_percent = (
            (close - ma)
            / ma
        ) * 100

        ma_old = previous[ma_column]

        trend_score = self.config.bearish_trend_score
        strength_score = 0
        volatility_score = 0

        if distance_percent >= self.config.ma_distance_strong:

            trend_score += 10

        elif distance_percent >= self.config.ma_distance_medium:

            trend_score += 7

        elif distance_percent >= self.config.ma_distance_weak:

            trend_score += 4

        slope_percent = (
            (ma - ma_old)
            / ma_old
        ) * 100

        if slope_percent >= self.config.ma_slope_strong:

            trend_score += 8

        elif slope_percent >= self.config.ma_slope_medium:

            trend_score += 4

        elif slope_percent >= self.config.ma_slope_weak:

            trend_score += 2

        # Price above MA20

        if close > latest["MA20"]:
            trend_score += 4

        momentum = latest["Momentum20"]

        if momentum >= self.config.momentum_strong:

            trend_score += 5

        elif momentum >= self.config.momentum_medium:

            trend_score += 3

        elif momentum >= self.config.momentum_weak:

            trend_score += 1

        atr = latest["ATRPercent"]
        volatility_score = atr

        if 1 <= atr <= 2:

            trend_score += 4

        elif 2 < atr <= 3:

            trend_score += 3

        elif 3 < atr <= 4:

            trend_score += 2

        total_score = min(
            trend_score,
            self.config.max_market_score
        )

        if total_score >= self.config.bullish_threshold:
            trend = "BULLISH"

        elif total_score >= self.config.neutral_threshold:
            trend = "NEUTRAL"

        else:
            trend = "BEARISH"

        print("=" * 70)
        print(f"Market Trend       : {trend}")
        print(f"Distance MA150 %   : {distance_percent:.2f}")
        print(f"MA150 Slope %      : {slope_percent:.2f}")
        print(f"Momentum20 %       : {momentum:.2f}")
        print(f"ATR %              : {atr:.2f}")
        print(f"Market Score       : {total_score}")
        print("=" * 70)

        return MarketState(
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