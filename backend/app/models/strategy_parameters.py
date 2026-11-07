
from dataclasses import dataclass


@dataclass
class StrategyParameters:
    """
    Stores the configurable parameters used by the trading strategy.
    """

    strategy_name: str = "moving_average"  # Name of the trading strategy.

    short_ma: int = 10                     # Short-term moving average period.
    medium_ma: int = 20                    # Medium-term moving average period.
    long_ma: int = 100                     # Long-term moving average period.

    risk_percent: float = 1.0              # Percentage of capital risked per trade.

    partial_exit_2r: bool = True            # Enables partial profit booking at 2R.
    partial_exit_3r: bool = True            # Enables partial profit booking at 3R.

    @property
    def short_ma_column(self):
        """Returns the dataframe column name for the short-term moving average."""
        return f"MA{self.short_ma}"

    @property
    def medium_ma_column(self):
        """Returns the dataframe column name for the medium-term moving average."""
        return f"MA{self.medium_ma}"

    @property
    def long_ma_column(self):
        """Returns the dataframe column name for the long-term moving average."""
        return f"MA{self.long_ma}"
