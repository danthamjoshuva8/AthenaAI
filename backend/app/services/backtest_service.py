
from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.portfolio_engine import PortfolioEngine
from app.config.backtest_config import BacktestConfig


class BacktestService:
    """
    Provides a service layer for backtesting, portfolio execution,
    performance analytics, strategy optimization, and AI-driven insights.
    """

    def __init__(self):
        """Initializes backtesting configuration and engine instances."""

        self.config = BacktestConfig()  # Default backtesting configuration.

        self.engine = BacktestEngine(
            self.config
        )  # Engine for individual stock backtesting.

        self.portfolio_engine = PortfolioEngine()  # Engine for portfolio-level operations.

    def load_signals(self, db: Session, symbol: str):
        """Loads historical trading signals for a given stock."""
        return self.engine.load_signals(db, symbol)

    def simulate_positions(self, db: Session, symbol: str):
        """Simulates trading positions for a given stock."""
        return self.engine.simulate_positions(db, symbol)

    def execute_trades(self, db: Session, symbol: str):
        """Executes the backtesting logic for a given stock."""
        return self.engine.execute_trades(db, symbol)

    def performance_metrics(self, db: Session, symbol: str):
        """Calculates individual stock performance metrics."""
        return self.engine.performance_metrics(db, symbol)

    def portfolio_metrics(self, db: Session, symbols: list):
        """Loads and ranks trades across the specified portfolio symbols."""
        return self.portfolio_engine.load_all_trades(db, symbols)

    def execute_portfolio(self, db: Session, symbols: list):
        """Executes portfolio-level trade simulation."""
        return self.portfolio_engine.execute_portfolio(db, symbols)

    def equity_curve(self, db: Session, symbol: str):
        """Generates the equity curve for a given stock."""
        return self.engine.equity_curve(db, symbol)

    def drawdown_metrics(self, db: Session, symbol: str):
        """Calculates drawdown metrics for a given stock."""
        return self.engine.drawdown_metrics(db, symbol)

    def portfolio_summary(self, db: Session, symbols: list):
        """Generates a summary of portfolio trading performance."""
        return self.portfolio_engine.portfolio_summary(db, symbols)

    def update_config(self, config: BacktestConfig):
        """Updates the portfolio engine configuration."""
        self.portfolio_engine.config = config

    def portfolio_statistics(self, db: Session, symbols: list):
        """Calculates portfolio execution and capital utilization statistics."""
        return self.portfolio_engine.portfolio_statistics(db, symbols)

    def trade_analytics(self, db: Session, symbols: list):
        """Calculates detailed trade performance analytics."""
        return self.portfolio_engine.trade_analytics(db, symbols)

    def risk_analytics(self, db: Session, symbols: list):
        """Calculates portfolio trading risk metrics."""
        return self.portfolio_engine.risk_analytics(db, symbols)

    def holding_analytics(self, db: Session, symbols: list):
        """Analyzes trade holding periods and durations."""
        return self.portfolio_engine.holding_analytics(db, symbols)

    def monthly_analytics(self, db: Session, symbols: list):
        """Generates monthly trading performance analytics."""
        return self.portfolio_engine.monthly_analytics(db, symbols)

    def yearly_analytics(self, db: Session, symbols: list):
        """Generates yearly trading performance analytics."""
        return self.portfolio_engine.yearly_analytics(db, symbols)

    def market_analytics(self, db: Session, symbols: list):
        """Analyzes trading performance across market conditions."""
        return self.portfolio_engine.market_analytics(db, symbols)

    def sector_analytics(self, db: Session, symbols: list):
        """Analyzes trading performance across different sectors."""
        return self.portfolio_engine.sector_analytics(db, symbols)

    def skipped_trade_analytics(self, db: Session, symbols: list):
        """Analyzes opportunities skipped during portfolio execution."""
        return self.portfolio_engine.skipped_trade_analytics(db, symbols)

    def capital_utilization_analytics(self, db: Session, symbols: list):
        """Analyzes portfolio capital utilization and available cash."""
        return self.portfolio_engine.capital_utilization_analytics(db, symbols)

    def overlap_analytics(self, db: Session, symbols: list):
        """Analyzes overlapping open trading positions."""
        return self.portfolio_engine.overlap_analytics(db, symbols)

    def optimize_strategy(self, db, symbols):
        """Optimizes strategy parameters using historical backtesting results."""
        return self.portfolio_engine.optimize_strategy(db, symbols)

    def walk_forward_analysis(self, db, symbols: list):
        """Performs walk-forward strategy optimization and evaluation."""
        return self.portfolio_engine.walk_forward_analysis(db, symbols)

    def monte_carlo_analysis(self, db, symbols, simulations=1000):
        """Performs Monte Carlo simulations on portfolio trading results."""
        return self.portfolio_engine.monte_carlo_analysis(
            db, symbols, simulations
        )

    def strategy_health(self, db, symbols):
        """Evaluates the overall health of the trading strategy."""
        return self.portfolio_engine.strategy_health(db, symbols)

    def strategy_confidence(self, db, symbols):
        """Evaluates confidence in the current trading strategy."""
        return self.portfolio_engine.strategy_confidence(db, symbols)

    def market_regime(self, db, symbol):
        """Identifies the current market regime for a given symbol."""
        return self.portfolio_engine.market_regime(db, symbol)

    def strategy_recommendation(self, db, symbol, symbols):
        """Generates strategy recommendations using market and portfolio analysis."""
        return self.portfolio_engine.strategy_recommendation(
            db, symbol, symbols
        )

    def risk_recommendation(self, db, symbols):
        """Generates risk management recommendations for the portfolio."""
        return self.portfolio_engine.risk_recommendation(db, symbols)

    def strategy_summary(self, db, symbol, symbols):
        """Generates a consolidated strategy performance summary."""
        return self.portfolio_engine.strategy_summary(
            db, symbol, symbols
        )

    def strategy_intelligence(self, db, symbol, symbols):
        """Generates comprehensive AI-driven strategy intelligence."""
        return self.portfolio_engine.strategy_intelligence(
            db, symbol, symbols
        )
