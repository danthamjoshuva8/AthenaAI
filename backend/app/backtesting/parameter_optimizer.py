
import logging
import math
import time

from itertools import product

from app.backtesting.backtest_engine import BacktestEngine


logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    Optimizes moving average parameters by evaluating multiple
    configurations through portfolio backtesting.
    """

    def generate_configs(self):
        """
        Generate valid short, medium and long moving average combinations.
        """

        start_time = time.perf_counter()

        try:
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
                    configs.append({
                        "short_ma": short,
                        "medium_ma": medium,
                        "long_ma": long
                    })

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "parameter_configs_generated",
                extra={
                    "event": "parameter_configs_generated",
                    "configuration_count": len(configs),
                    "duration_ms": duration_ms
                }
            )

            return configs

        except Exception:
            logger.exception(
                "parameter_config_generation_failed",
                extra={
                    "event": "parameter_config_generation_failed"
                }
            )
            raise

    def evaluate_configs(
        self,
        portfolio_engine,
        db,
        symbols
    ):
        """
        Evaluate each moving average configuration using portfolio backtesting.

        Original configuration and BacktestEngine are restored even
        if an individual configuration fails.
        """

        start_time = time.perf_counter()

        original_engine = portfolio_engine.backtest_engine

        strategy_config = portfolio_engine.config.strategy

        original_short = strategy_config.short_ma
        original_medium = strategy_config.medium_ma
        original_long = strategy_config.long_ma

        results = []
        failed_configurations = 0

        try:
            if not symbols:
                raise ValueError("At least one symbol is required.")

            configs = self.generate_configs()

            logger.info(
                "parameter_optimization_started",
                extra={
                    "event": "parameter_optimization_started",
                    "symbol_count": len(symbols),
                    "configuration_count": len(configs)
                }
            )

            for index, config in enumerate(configs, start=1):

                config_start = time.perf_counter()

                try:
                    strategy_config.short_ma = config["short_ma"]
                    strategy_config.medium_ma = config["medium_ma"]
                    strategy_config.long_ma = config["long_ma"]

                    # Rebuild the backtest engine using the new parameters.
                    portfolio_engine.backtest_engine = BacktestEngine(
                        portfolio_engine.config
                    )

                    summary = portfolio_engine.portfolio_summary(
                        db,
                        symbols
                    )

                    required_fields = [
                        "total_trades",
                        "winning_trades",
                        "losing_trades",
                        "win_rate",
                        "net_profit",
                        "average_profit",
                        "best_trade",
                        "worst_trade"
                    ]

                    missing_fields = [
                        field for field in required_fields
                        if field not in summary
                    ]

                    if missing_fields:
                        raise ValueError(
                            f"Portfolio summary is missing fields: "
                            f"{missing_fields}"
                        )

                    result = {
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
                    }

                    # Validate numerical performance metrics.
                    for field in (
                        "win_rate",
                        "net_profit",
                        "average_profit"
                    ):
                        value = result[field]

                        if (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(value)
                        ):
                            raise ValueError(
                                f"Invalid {field} returned by portfolio summary."
                            )

                    results.append(result)

                    config_duration_ms = round(
                        (time.perf_counter() - config_start) * 1000,
                        2
                    )

                    logger.info(
                        "parameter_configuration_evaluated",
                        extra={
                            "event": "parameter_configuration_evaluated",
                            "configuration_number": index,
                            "total_configurations": len(configs),
                            "short_ma": config["short_ma"],
                            "medium_ma": config["medium_ma"],
                            "long_ma": config["long_ma"],
                            "total_trades": result["total_trades"],
                            "net_profit": result["net_profit"],
                            "win_rate": result["win_rate"],
                            "duration_ms": config_duration_ms
                        }
                    )

                except Exception:
                    failed_configurations += 1

                    logger.exception(
                        "parameter_configuration_failed",
                        extra={
                            "event": "parameter_configuration_failed",
                            "configuration_number": index,
                            "short_ma": config["short_ma"],
                            "medium_ma": config["medium_ma"],
                            "long_ma": config["long_ma"]
                        }
                    )

                    # Continue evaluating other configurations.

            if not results:
                raise RuntimeError(
                    "Parameter optimization failed: "
                    "no configurations produced valid results."
                )

            results.sort(
                key=lambda result: result["net_profit"],
                reverse=True
            )

            for rank, result in enumerate(results, start=1):
                result["rank"] = rank

            optimization_result = self.optimization_summary(results)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "parameter_optimization_completed",
                extra={
                    "event": "parameter_optimization_completed",
                    "evaluated_configurations": len(results),
                    "failed_configurations": failed_configurations,
                    "best_net_profit": results[0]["net_profit"],
                    "best_parameters": {
                        "short_ma": results[0]["short_ma"],
                        "medium_ma": results[0]["medium_ma"],
                        "long_ma": results[0]["long_ma"]
                    },
                    "duration_ms": duration_ms
                }
            )

            optimization_result["failed_configurations"] = (
                failed_configurations
            )

            return optimization_result

        except Exception:
            logger.exception(
                "parameter_optimization_failed",
                extra={
                    "event": "parameter_optimization_failed",
                    "evaluated_configurations": len(results),
                    "failed_configurations": failed_configurations
                }
            )
            raise

        finally:
            # Always restore original parameters and engine.
            strategy_config.short_ma = original_short
            strategy_config.medium_ma = original_medium
            strategy_config.long_ma = original_long

            portfolio_engine.backtest_engine = original_engine

            logger.info(
                "parameter_configuration_restored",
                extra={
                    "event": "parameter_configuration_restored",
                    "short_ma": original_short,
                    "medium_ma": original_medium,
                    "long_ma": original_long
                }
            )

    def optimization_summary(self, results):
        """
        Generate overall statistics for evaluated configurations.
        """

        start_time = time.perf_counter()

        try:
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
                sum(result["net_profit"] for result in results) / total,
                2
            )

            average_win_rate = round(
                sum(result["win_rate"] for result in results) / total,
                2
            )

            summary = {
                "total_configurations": total,
                "best_strategy": best,
                "worst_strategy": worst,
                "comparison": comparison,
                "average_net_profit": average_profit,
                "average_win_rate": average_win_rate,
                "results": results
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "parameter_optimization_summary_generated",
                extra={
                    "event": "parameter_optimization_summary_generated",
                    "configuration_count": total,
                    "average_net_profit": average_profit,
                    "average_win_rate": average_win_rate,
                    "duration_ms": duration_ms
                }
            )

            return summary

        except Exception:
            logger.exception(
                "parameter_optimization_summary_failed",
                extra={
                    "event": "parameter_optimization_summary_failed",
                    "configuration_count": (
                        len(results) if isinstance(results, list) else None
                    )
                }
            )
            raise

    def compare_strategies(self, best, worst):
        """
        Compare the best and worst performing parameter configurations.
        """

        start_time = time.perf_counter()

        try:
            comparison = {
                "profit_difference": round(
                    best["net_profit"] - worst["net_profit"],
                    2
                ),
                "win_rate_difference": round(
                    best["win_rate"] - worst["win_rate"],
                    2
                ),
                "trade_difference": (
                    best["total_trades"] - worst["total_trades"]
                ),
                "better_parameters": {
                    "short_ma": best["short_ma"],
                    "medium_ma": best["medium_ma"],
                    "long_ma": best["long_ma"]
                }
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.debug(
                "parameter_strategies_compared",
                extra={
                    "event": "parameter_strategies_compared",
                    "profit_difference": comparison["profit_difference"],
                    "win_rate_difference": comparison["win_rate_difference"],
                    "duration_ms": duration_ms
                }
            )

            return comparison

        except Exception:
            logger.exception(
                "parameter_strategy_comparison_failed",
                extra={
                    "event": "parameter_strategy_comparison_failed"
                }
            )
            raise
