from dataclasses import dataclass


@dataclass
class StrategyConfig:

    #
    # Moving Averages
    #

    ma_fast = 15

    ma_medium = 30

    ma_slow = 150

    #
    # Pullback
    #

    pullback_percent = 1.5

    #
    # Volume
    #

    volume_multiplier = 0.5

    #
    # Candle
    #

    max_body_percent = 3.0

    max_upper_wick_ratio = 1.0

    min_lower_wick_ratio = 0.20

    #
    # Breakout
    #

    breakout_wait = 5