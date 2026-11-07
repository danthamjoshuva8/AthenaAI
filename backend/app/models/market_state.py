
from dataclasses import dataclass


@dataclass
class MarketState:
    """
    Stores the overall market condition and its contributing scores.
    """

    trend: str                     # Overall market trend (Bullish, Bearish, or Neutral).

    trend_score: float             # Score representing the market trend.
    breadth_score: float           # Score representing market breadth.
    strength_score: float           # Score representing overall market strength.
    volatility_score: float         # Score representing market volatility.
    total_score: float              # Combined market condition score.

    stocks_above_ma: int = 0        # Number of stocks trading above the selected moving average.

    ma_distance_percent: float = 0  # Percentage distance of market price from its moving average.
    ma_slope_percent: float = 0     # Percentage slope of the moving average.
    momentum_percent: float = 0    # Market momentum percentage.
    atr_percent: float = 0         # Average True Range as a percentage of market price.
