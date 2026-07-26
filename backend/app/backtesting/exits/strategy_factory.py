from app.config.backtest_config import ExitStrategyType

from .partial_exit_strategy import PartialExitStrategy

from .full_3r_strategy import Full3RStrategy

from .trail_2r_strategy import Trail2RStrategy


class ExitStrategyFactory:

    @staticmethod
    def create(strategy):

        if strategy == ExitStrategyType.PARTIAL_2R_3R:
            return PartialExitStrategy()

        if strategy == ExitStrategyType.FULL_3R:
            return Full3RStrategy()

        if strategy == ExitStrategyType.TRAIL_2R:
            return Trail2RStrategy()

        raise ValueError("Unknown Exit Strategy")