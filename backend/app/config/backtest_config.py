from dataclasses import dataclass, field
from app.models.strategy_parameters import StrategyParameters

@dataclass
class BacktestConfig : #
    # Capital
    #

    initial_capital : float = 100000

    risk_percent : float = 0.75

    #
    # Strategy Parameters
    #

    strategy: StrategyParameters = field(
        default_factory=StrategyParameters
    )

    #
    # Capital Modes
    #

    capital_mode : str = "compound"
    # fixed
    # compound
    # profit_only

    #
    # Capital Update
    #

    capital_update : str = "daily"
    # trade
    # daily
    # weekly

    #
    # Capital Check
    #

    capital_check : bool = True

    #
    # Margin
    #

    margin_mode : str = "cash"
    # cash
    # margin
    # mtf

    leverage : float = 1.0

    #
    # Costs
    #

    brokerage : bool = False

    slippage : bool = False

    start_date = None

    end_date = None