
from dataclasses import dataclass


@dataclass
class StrategyFeatures:
    """
    Stores technical and trading-related features used to evaluate a strategy.
    """

    trend_strength: float = 0.0          # Measures the strength of the prevailing market trend.

    volume_strength: float = 0.0         # Measures trading volume relative to normal volume.

    breakout_strength: float = 0.0       # Measures the strength of price breakout conditions.

    momentum_strength: float = 0.0       # Measures the strength of price momentum.

    risk_reward_strength: float = 0.0    # Represents the quality of the potential risk-to-reward ratio.

    relative_strength: float = 0.0       # Measures performance relative to a benchmark or market index.

    liquidity_strength: float = 0.0      # Measures stock liquidity based on trading activity.
