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

        return self.optimization_summary(
            results
        )
    
    def optimization_summary(
        self,
        results
    ):

        if not results:

            return {}

        total = len(results)

        best = results[0]

        worst = results[-1]

        comparison = self.compare_strategies(
            best,
            worst
        )

        average_profit = round(

            sum(
                result["net_profit"]
                for result in results
            ) / total,

            2

        )

        average_win_rate = round(

            sum(
                result["win_rate"]
                for result in results
            ) / total,

            2

        )

        return {

            "total_configurations": total,

            "best_strategy": best,

            "worst_strategy": worst,

            "comparison": comparison,

            "average_net_profit": average_profit,

            "average_win_rate": average_win_rate,

            "results": results

        }
    
    def compare_strategies(
        self,
        best,
        worst
    ):

        return {

            "profit_difference": round(
                best["net_profit"] - worst["net_profit"],
                2
            ),

            "win_rate_difference": round(
                best["win_rate"] - worst["win_rate"],
                2
            ),

            "trade_difference":

                best["total_trades"] -

                worst["total_trades"],

            "better_parameters": {

                "short_ma": best["short_ma"],

                "medium_ma": best["medium_ma"],

                "long_ma": best["long_ma"]

            }

        }