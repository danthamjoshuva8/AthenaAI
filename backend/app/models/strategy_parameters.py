from dataclasses import dataclass

@dataclass
class StrategyParameters:

    strategy_name: str = "moving_average"

    short_ma: int = 10
    medium_ma: int = 20
    long_ma: int = 100

    risk_percent: float = 1.0

    partial_exit_2r: bool = True
    partial_exit_3r: bool = True

    @property
    def short_ma_column(self):
        return f"MA{self.short_ma}"

    @property
    def medium_ma_column(self):
        return f"MA{self.medium_ma}"

    @property
    def long_ma_column(self):
        return f"MA{self.long_ma}"