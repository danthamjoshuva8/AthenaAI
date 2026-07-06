from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine


class BacktestService:

    def __init__(self):

        self.engine = BacktestEngine()

    def load_signals(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.load_signals(
            db,
            symbol
        )
    
    def simulate_positions(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.simulate_positions(
            db,
            symbol
        )
    
    def execute_trades(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.execute_trades(
            db,
            symbol
        )
    
    def performance_metrics(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.performance_metrics(
            db,
            symbol
        )
    
    def portfolio_metrics(
        self,
        db: Session,
        symbols: list
    ):
        return self.engine.portfolio_metrics(
            db,
            symbols
        )
    
    def execute_portfolio(
        self,
        db: Session,
        symbols: list
    ):
        return self.engine.execute_portfolio(
            db,
            symbols
        )
    
    def equity_curve(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.equity_curve(
            db,
            symbol
        )
    
    def drawdown_metrics(
        self,
        db: Session,
        symbol: str
    ):

        return self.engine.drawdown_metrics(
            db,
            symbol
        )