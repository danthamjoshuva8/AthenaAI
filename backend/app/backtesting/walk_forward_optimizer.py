from datetime import date

from app.backtesting.parameter_optimizer import ParameterOptimizer


class WalkForwardOptimizer:

    def __init__(self):

        self.optimizer = ParameterOptimizer()

    def optimize_training_window(

        self,

        portfolio_engine,

        db,

        symbols,

        train_start,

        train_end

    ):

        #
        # Save original dates
        #

        original_start = portfolio_engine.config.start_date

        original_end = portfolio_engine.config.end_date

        #
        # Use only training period
        #

        portfolio_engine.config.start_date = date(

            train_start,

            1,

            1

        )

        portfolio_engine.config.end_date = date(

            train_end,

            12,

            31

        )

        #
        # Optimize
        #

        results = self.optimizer.evaluate_configs(

            portfolio_engine,

            db,

            symbols

        )

        #
        # Restore original config
        #

        portfolio_engine.config.start_date = original_start

        portfolio_engine.config.end_date = original_end

        return results
    
    def select_best_parameters(
        self,
        optimization_results
    ):

        if not optimization_results:

            return None

        #
        # Get best strategy from optimizer summary
        #

        best = optimization_results["best_strategy"]

        return {

            "short_ma": best["short_ma"],

            "medium_ma": best["medium_ma"],

            "long_ma": best["long_ma"],

            "net_profit": best["net_profit"],

            "win_rate": best["win_rate"]

        }
    
    def optimize(
        self,
        portfolio_engine,
        db,
        symbols,
        train_start,
        train_end
    ):
        
        original_parameters = {

            "short_ma": portfolio_engine.config.strategy.short_ma,

            "medium_ma": portfolio_engine.config.strategy.medium_ma,

            "long_ma": portfolio_engine.config.strategy.long_ma

        }

        results = self.optimize_training_window(

            portfolio_engine,

            db,

            symbols,

            train_start,

            train_end

        )

        best = self.select_best_parameters(

            results

        )

        self.apply_best_parameters(

            portfolio_engine,

            best

        )

        best["original_parameters"] = original_parameters

        return best
    
    def apply_best_parameters(
        self,
        portfolio_engine,
        best_parameters
    ):

        if best_parameters is None:

            return

        portfolio_engine.config.strategy.short_ma = (

            best_parameters["short_ma"]

        )

        portfolio_engine.config.strategy.medium_ma = (

            best_parameters["medium_ma"]

        )

        portfolio_engine.config.strategy.long_ma = (

            best_parameters["long_ma"]

        )

        #
        # Rebuild strategy
        #

        portfolio_engine.backtest_engine.strategy = (

            portfolio_engine.backtest_engine.factory.create_strategy(

                portfolio_engine.config.strategy.strategy_name,

                portfolio_engine.config

            )

        )

    def restore_original_parameters(
        self,
        portfolio_engine,
        original_parameters
    ):

        portfolio_engine.config.strategy.short_ma = (
            original_parameters["short_ma"]
        )

        portfolio_engine.config.strategy.medium_ma = (
            original_parameters["medium_ma"]
        )

        portfolio_engine.config.strategy.long_ma = (
            original_parameters["long_ma"]
        )

        portfolio_engine.backtest_engine.strategy = (

            portfolio_engine.backtest_engine.factory.create_strategy(

                portfolio_engine.config.strategy.strategy_name,

                portfolio_engine.config

            )

        )