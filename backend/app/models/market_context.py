
from dataclasses import dataclass


@dataclass
class MarketContext:
    """
    Stores the overall market context based on trend and technical indicators.
    """

    trend: str              # Current market trend (Bullish, Bearish, or Neutral).
    close: float            # Latest closing price of the market index.
    ma150: float            # 150-period moving average value.
    ma150_slope: float      # Slope of the 150-period moving average.
    score: float            # Overall market condition score.
