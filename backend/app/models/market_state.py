from dataclasses import dataclass


@dataclass
class MarketState:

    trend: str

    trend_score: float

    breadth_score: float

    strength_score: float

    volatility_score: float

    total_score: float

    stocks_above_ma: int = 0

    ma_distance_percent: float = 0
    ma_slope_percent: float = 0
    momentum_percent: float = 0
    atr_percent: float = 0