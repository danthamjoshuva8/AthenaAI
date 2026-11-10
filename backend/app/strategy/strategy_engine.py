
from sqlalchemy.orm import Session

from app.config.backtest_config import BacktestConfig
from app.strategy.strategy_factory import StrategyFactory


class StrategyEngine:
    """
    Coordinates strategy execution through the configured strategy.

    Initializes the backtesting configuration, creates the appropriate
    strategy using StrategyFactory, and provides methods to load market
    data, calculate moving averages, and retrieve trading signals.
    """

    def __init__(self):
        """
        Initialize the strategy engine.

        Loads the backtesting configuration and creates the strategy
        implementation based on the configured strategy name.
        """
        self.config = BacktestConfig()

        # Create the configured strategy implementation.
        self.strategy = StrategyFactory.create(
            self.config.strategy.strategy_name,
            self.config
        )

    def load_data(
        self,
        db: Session,
        symbol: str
    ):
        """
        Load historical market data for a stock.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to retrieve.

        Returns:
            Historical market data records.
        """
        return self.strategy.load_market_data(
            db,
            symbol
        )

    def calculate_ma(
        self,
        db: Session,
        symbol: str
    ):
        """
        Calculate configured moving averages for a stock.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to process.

        Returns:
            DataFrame containing market data and calculated moving averages.
        """
        return self.strategy.calculate_moving_averages(
            db,
            symbol
        )

    
    def generate_signals(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):

        return self.strategy.generate_signals(
            db,
            symbol,
            start_date=start_date,
            end_date=end_date
        )


    def latest_signal(
        self,
        db: Session,
        symbol: str
    ):
        """
        Retrieve the most recent trading signal for a stock.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to retrieve the signal for.

        Returns:
            Dictionary containing the symbol, date, closing price,
            latest signal, and moving average values.
        """
        latest = self.generate_signals(
            db,
            symbol
        )[-1]

        return {
            "symbol": symbol,
            "date": latest["date"],
            "close": latest["close"],
            "signal": latest["signal"],
            "moving_averages": latest["moving_averages"]
        }

    def buy_signals(
        self,
        db: Session,
        symbol: str
    ):
        """
        Retrieve all BUY signals generated for a stock.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to retrieve signals for.

        Returns:
            List containing only BUY signals.
        """
        return [
            signal
            for signal in self.generate_signals(
                db,
                symbol
            )
            if signal["signal"] == "BUY"
        ]

    def sell_signals(
        self,
        db: Session,
        symbol: str
    ):
        """
        Retrieve all SELL signals generated for a stock.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to retrieve signals for.

        Returns:
            List containing only SELL signals.
        """
        return [
            signal
            for signal in self.generate_signals(
                db,
                symbol
            )
            if signal["signal"] == "SELL"
        ]
