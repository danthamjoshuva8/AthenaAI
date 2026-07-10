from sqlalchemy.orm import Session

from app.strategies.moving_average import MovingAverageStrategy
from app.config.backtest_config import BacktestConfig
from app.strategies.strategy_factory import StrategyFactory


class StrategyService:

    def __init__(self):

        self.config = BacktestConfig()

        self.factory = StrategyFactory()

        self.strategy = self.factory.create_strategy(

            self.config.strategy.strategy_name,

            self.config

        )

    def load_data(
        self,
        db: Session,
        symbol: str
    ):

        return self.strategy.load_market_data(
            db,
            symbol
        )

    def calculate_ma(
        self,
        db: Session,
        symbol: str
    ):

        return self.strategy.calculate_moving_averages(
            db,
            symbol
        )
    
    def generate_signals(
        self,
        db: Session,
        symbol: str
    ):

        return self.strategy.generate_signals(
            db,
            symbol
        )
    
    def latest_signal(
        self,
        db: Session,
        symbol: str
    ):

        latest = self.generate_signals(
            db,
            symbol
        )[-1]

        return {

            "symbol": symbol,

            "date": latest["date"],

            "close": latest["close"],

            "signal": latest["signal"],

            "MA15": latest["MA15"],

            "MA30": latest["MA30"],

            "MA150": latest["MA150"]

        }


    def buy_signals(
        self,
        db: Session,
        symbol: str
    ):

        signals = self.generate_signals(
            db,
            symbol
        )

        return [

            s

            for s in signals

            if s["signal"] == "BUY"

        ]


    def sell_signals(
        self,
        db: Session,
        symbol: str
    ):

        signals = self.generate_signals(
            db,
            symbol
        )

        return [

            s

            for s in signals

            if s["signal"] == "SELL"

        ]