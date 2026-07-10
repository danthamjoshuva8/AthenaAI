from itertools import product
from app.backtesting.backtest_engine import BacktestEngine


class ParameterOptimizer:

    def generate_configs(self):

        short_ma = [10, 15, 20]

        medium_ma = [20, 30, 50]

        long_ma = [100, 150, 200]

        configs = []

        for short, medium, long in product(

            short_ma,

            medium_ma,

            long_ma

        ):

            if short < medium < long:

                configs.append(

                    {

                        "short_ma": short,

                        "medium_ma": medium,

                        "long_ma": long

                    }

                )

        return configs
    
    def evaluate_configs(
        self,
        portfolio_engine,
        db,
        symbols
    ):

        configs = self.generate_configs()

        results = []

        original_short = portfolio_engine.config.strategy.short_ma

        original_medium = portfolio_engine.config.strategy.medium_ma

        original_long = portfolio_engine.config.strategy.long_ma

        for config in configs:

            portfolio_engine.config.strategy.short_ma = config["short_ma"]

            portfolio_engine.config.strategy.medium_ma = config["medium_ma"]

            portfolio_engine.config.strategy.long_ma = config["long_ma"]

            #
            # Rebuild strategy with new parameters
            #

            portfolio_engine.backtest_engine = BacktestEngine(
                portfolio_engine.config
            )

            summary = portfolio_engine.portfolio_summary(

                db,

                symbols

            )

            results.append({

                "short_ma": config["short_ma"],

                "medium_ma": config["medium_ma"],

                "long_ma": config["long_ma"],

                "total_trades": summary["total_trades"],

                "winning_trades": summary["winning_trades"],

                "losing_trades": summary["losing_trades"],

                "win_rate": summary["win_rate"],

                "net_profit": summary["net_profit"],

                "average_profit": summary["average_profit"],

                "best_trade": summary["best_trade"],

                "worst_trade": summary["worst_trade"]

            })

        portfolio_engine.config.strategy.short_ma = original_short

        portfolio_engine.config.strategy.medium_ma = original_medium

        portfolio_engine.config.strategy.long_ma = original_long

        #
        # Restore original strategy
        #

        portfolio_engine.backtest_engine = BacktestEngine(
            portfolio_engine.config
        )

        results.sort(

            key=lambda x: x["net_profit"],

            reverse=True

        )

        for rank, result in enumerate(results, start=1):

            result["rank"] = rank

        return results