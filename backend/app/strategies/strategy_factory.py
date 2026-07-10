from app.config.backtest_config import BacktestConfig
from app.strategies.moving_average import MovingAverageStrategy


class StrategyFactory:

    def create_strategy(
        self,
        strategy_name: str,
        config: BacktestConfig
    ):

        strategy_name = strategy_name.lower()

        if strategy_name == "moving_average":

            return MovingAverageStrategy(
                config
            )

        raise ValueError(
            f"Unknown strategy: {strategy_name}"
        )