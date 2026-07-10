from dataclasses import dataclass


@dataclass
class StrategyParameters:

    strategy_name: str = "moving_average"

    short_ma: int = 15

    medium_ma: int = 30

    long_ma: int = 150

    risk_percent: float = 1.0

    partial_exit_2r: bool = True

    partial_exit_3r: bool = True