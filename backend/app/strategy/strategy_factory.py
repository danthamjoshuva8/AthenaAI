
from app.config.backtest_config import BacktestConfig
from app.strategy.moving_average import MovingAverageStrategy


class StrategyFactory:
    """
    Creates strategy instances based on the configured strategy name.

    Maintains a mapping between strategy names and their implementation
    classes, allowing the application to select the appropriate trading
    strategy dynamically.
    """

    @staticmethod
    def create(
        strategy_name: str,
        config: BacktestConfig
    ):
        """
        Create and return the requested trading strategy.

        Args:
            strategy_name: Name of the strategy to instantiate.
            config: Backtesting configuration passed to the strategy.

        Returns:
            An initialized instance of the selected strategy.

        Raises:
            ValueError: If the requested strategy name is not registered.
        """

        # Normalize the strategy name for case-insensitive matching.
        strategy_name = strategy_name.lower()

        # Register available strategy implementations.
        strategies = {
            "moving_average": MovingAverageStrategy
        }

        # Retrieve the implementation associated with the strategy name.
        strategy_class = strategies.get(strategy_name)

        if strategy_class is None:
            raise ValueError(
                f"Unknown strategy: {strategy_name}"
            )

        # Initialize the selected strategy with its configuration.
        return strategy_class(config)
