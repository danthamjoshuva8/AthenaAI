
from sqlalchemy.orm import Session

from app.strategy.strategy_engine import StrategyEngine


class StrategyService:
    """
    Provides a service layer for technical strategy operations,
    including market data loading, moving average calculations,
    and trading signal generation.
    """

    def __init__(self):
        """Initializes the strategy engine."""

        self.engine = StrategyEngine()  # Engine responsible for strategy operations.

    def load_data(self, db: Session, symbol: str):
        """Loads historical market data required for strategy calculations."""
        return self.engine.load_data(db, symbol)

    def calculate_ma(self, db: Session, symbol: str):
        """Calculates moving averages for the specified stock."""
        return self.engine.calculate_ma(db, symbol)

    def generate_signals(self, db: Session, symbol: str):
        """Generates trading signals using the configured strategy."""
        return self.engine.generate_signals(db, symbol)

    def latest_signal(self, db: Session, symbol: str):
        """Retrieves the latest trading signal for the specified stock."""
        return self.engine.latest_signal(db, symbol)

    def buy_signals(self, db: Session, symbol: str):
        """Retrieves all generated buy signals for the specified stock."""
        return self.engine.buy_signals(db, symbol)

    def sell_signals(self, db: Session, symbol: str):
        """Retrieves all generated sell signals for the specified stock."""
        return self.engine.sell_signals(db, symbol)
