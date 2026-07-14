from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.portfolio_engine import PortfolioEngine
from app.config.backtest_config import BacktestConfig


class BacktestService:

    def __init__(self):

        self.config = BacktestConfig()

        self.engine = BacktestEngine(
            self.config
        )

        self.portfolio_engine = PortfolioEngine()

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
        return self.portfolio_engine.load_all_trades(
            db,
            symbols
        )
    
    def execute_portfolio(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.execute_portfolio(

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
    
    def portfolio_summary(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.portfolio_summary(
            db,
            symbols
        )
    
    def update_config(
        self,
        config: BacktestConfig
    ):

        self.portfolio_engine.config = config

    def portfolio_statistics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.portfolio_statistics(
            db,
            symbols
        )
    
    def trade_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.trade_analytics(
            db,
            symbols
        )
    
    def risk_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.risk_analytics(
            db,
            symbols
        )
    
    def holding_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.holding_analytics(
            db,
            symbols
        )
    
    def monthly_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.monthly_analytics(
            db,
            symbols
        )
    
    def yearly_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.yearly_analytics(
            db,
            symbols
        )
    
    def market_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.market_analytics(
            db,
            symbols
        )
    
    def sector_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.sector_analytics(

            db,

            symbols

        )
    
    def skipped_trade_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.skipped_trade_analytics(

            db,

            symbols

        )
    
    def capital_utilization_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.capital_utilization_analytics(
            db,
            symbols
        )
    
    def overlap_analytics(
        self,
        db: Session,
        symbols: list
    ):

        return self.portfolio_engine.overlap_analytics(
            db,
            symbols
        )
    
    def optimize_strategy(
        self,
        db,
        symbols
    ):

        return self.portfolio_engine.optimize_strategy(
            db,
            symbols
        )
    
    def walk_forward_analysis(
        self,
        db
    ):

        return self.portfolio_engine.walk_forward_analysis(
            db
        )
    
    def monte_carlo_analysis(

        self,

        db,

        symbols,

        simulations=1000

    ):

        return self.portfolio_engine.monte_carlo_analysis(

            db,

            symbols,

            simulations

        )