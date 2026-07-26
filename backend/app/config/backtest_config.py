from dataclasses import dataclass, field
from app.models.strategy_parameters import StrategyParameters
from enum import Enum


class ExitStrategyType(str, Enum):

    PARTIAL_2R_3R = "partial_2r_3r"

    FULL_3R = "full_3r"

    TRAIL_2R = "trail_2r"


class StopMoveType(str, Enum):

    NONE = "none"

    BREAKEVEN = "breakeven"

    ONE_R = "1r"

    TWO_R = "2r"

@dataclass
class BacktestConfig : #
    # Capital
    #

    initial_capital : float = 100000

    risk_percent : float = 1.0

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

    max_daily_entries = 5

    #################################################
    # Exit Strategy
    #################################################

    EXIT_STRATEGY = ExitStrategyType.PARTIAL_2R_3R

    STOP_MOVE = StopMoveType.TWO_R