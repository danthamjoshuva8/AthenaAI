
from dataclasses import dataclass


@dataclass(frozen=True)
class ForwardTestingPortfolioConfig:
    """
    Configuration for the AthenaAI forward-testing portfolio.

    These settings apply only to paper trading.
    They do not modify backtesting or live-trading configuration.
    """

    # Portfolio capital
    initial_capital: float = 100_000.00

    # Portfolio limits
    max_positions: int = 5
    max_position_allocation_pct: float = 20.0
    max_portfolio_allocation_pct: float = 100.0

    # Risk management
    risk_per_trade_pct: float = 1.0
    max_portfolio_risk_pct: float = 5.0

    # Candidate selection
    max_new_positions_per_day: int = 3

    # Execution settings
    allow_multiple_positions_per_symbol: bool = False
    allow_new_positions: bool = True

    # Paper trading
    enable_paper_trading: bool = True

    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be greater than zero.")

        if self.max_positions <= 0:
            raise ValueError("Maximum positions must be greater than zero.")

        if self.max_new_positions_per_day <= 0:
            raise ValueError(
                "Maximum new positions per day must be greater than zero."
            )

        if not 0 < self.max_position_allocation_pct <= 100:
            raise ValueError("Invalid maximum position allocation percentage.")

        if not 0 < self.max_portfolio_allocation_pct <= 100:
            raise ValueError("Invalid maximum portfolio allocation percentage.")

        if not 0 < self.risk_per_trade_pct <= 100:
            raise ValueError("Invalid risk per trade percentage.")

        if not 0 < self.max_portfolio_risk_pct <= 100:
            raise ValueError("Invalid maximum portfolio risk percentage.")

        if self.risk_per_trade_pct > self.max_portfolio_risk_pct:
            raise ValueError(
                "Risk per trade cannot exceed maximum portfolio risk."
            )


# Dedicated forward-testing configuration instance
FORWARD_TESTING_PORTFOLIO_CONFIG = ForwardTestingPortfolioConfig()
