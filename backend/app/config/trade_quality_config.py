from dataclasses import dataclass, field


@dataclass
class TradeQualityModuleConfig:
    enabled: bool = True
    weight: float = 1.0

@dataclass
class MarketContextConfig:

    enabled: bool = True

    long_ma_period: int = 150

    bullish_trend_score: float = 30
    bearish_trend_score: float = 0

    breadth_weight: float = 30
    strength_weight: float = 20
    volatility_weight: float = 20

    bullish_threshold: float = 25
    neutral_threshold: float = 15

    trend_lookback_days: int = 20

    breadth_bullish_percent: float = 70
    breadth_neutral_percent: float = 50

    breadth_bullish_score: float = 30
    breadth_neutral_score: float = 15
    breadth_bearish_score: float = 0

    medium_momentum_score = 3
    weak_momentum_score = 1

    momentum_strong_percent = 8
    momentum_medium_percent = 4

    acceptable_volatility_score = 2

    normal_atr_percent = 3
    acceptable_atr_percent = 4

    max_market_score = 30

    ma_distance_weak = 2
    ma_distance_medium = 5
    ma_distance_strong = 10

    ma_slope_weak = 0.2
    ma_slope_medium = 0.6
    ma_slope_strong = 1.2

    momentum_weak = 2
    momentum_medium = 5
    momentum_strong = 8

@dataclass
class TradeQualityConfig:

    body_quality = TradeQualityModuleConfig(
        enabled=True,
        weight=10
    )

    relative_strength = TradeQualityModuleConfig(
        enabled=False,      # Will enable after RS implementation
        weight=20
    )

    breakout = TradeQualityModuleConfig(
        enabled=False,
        weight=15
    )

    consolidation = TradeQualityModuleConfig(
        enabled=False,
        weight=20
    )

    market_context: MarketContextConfig = field(
        default_factory=MarketContextConfig
    )

    # ===============================
    # Trade Quality Weights
    # ===============================

    volume = TradeQualityModuleConfig(
        enabled=True,
        weight=25
    )

    distance_from_ma = TradeQualityModuleConfig(
        enabled=True,
        weight=30
    )

    candle_quality = TradeQualityModuleConfig(
        enabled=True,
        weight=10
    )

    volume_confirmation = TradeQualityModuleConfig(
        enabled=True,
        weight=5
    )

    sector = TradeQualityModuleConfig(
        enabled=True,
        weight=10
    )

    market = TradeQualityModuleConfig(
        enabled=True,
        weight=10
    )