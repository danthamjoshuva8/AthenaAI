
import logging
import math
import time

from datetime import date

from app.backtesting.parameter_optimizer import ParameterOptimizer


logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    Optimizes strategy parameters on a training period and
    evaluates the selected parameters on a separate test period.
    """

    def __init__(self):
        """Initialize parameter optimizer."""

        self.optimizer = ParameterOptimizer()

        logger.info("Walk Forward Optimizer initialized")

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    @staticmethod
    def _validate_year(year, field_name):
        """Validate year input."""

        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or year < 1900
            or year > 9998
        ):
            raise ValueError(
                f"{field_name} must be a valid year"
            )

        return year

    @staticmethod
    def _validate_parameters(parameters):
        """Validate moving average parameters."""

        if not isinstance(parameters, dict):
            raise ValueError(
                "Strategy parameters must be a dictionary"
            )

        required = [
            "short_ma",
            "medium_ma",
            "long_ma"
        ]

        for field in required:
            value = parameters.get(field)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(
                    f"{field} must be a positive integer"
                )

        if not (
            parameters["short_ma"]
            < parameters["medium_ma"]
            < parameters["long_ma"]
        ):
            raise ValueError(
                "Moving averages must satisfy "
                "short_ma < medium_ma < long_ma"
            )

        return {
            field: parameters[field]
            for field in required
        }

    # --------------------------------------------------
    # Strategy Rebuild
    # --------------------------------------------------

    @staticmethod
    def _rebuild_strategy(portfolio_engine):
        """
        Rebuild strategy after changing configuration.

        Uses the existing strategy factory.
        """

        portfolio_engine.backtest_engine.strategy = (
            portfolio_engine.backtest_engine.factory.create(
                portfolio_engine.config.strategy.strategy_name,
                portfolio_engine.config
            )
        )

    # --------------------------------------------------
    # Training Window Optimization
    # --------------------------------------------------

    def optimize_training_window(
        self,
        portfolio_engine,
        db,
        symbols,
        train_start,
        train_end
    ):
        """
        Optimize parameters using training-period data only.

        Original portfolio dates are always restored.
        """

        start_time = time.perf_counter()

        original_start = portfolio_engine.config.start_date
        original_end = portfolio_engine.config.end_date

        try:
            train_start = self._validate_year(
                train_start,
                "Training start year"
            )

            train_end = self._validate_year(
                train_end,
                "Training end year"
            )

            if train_start > train_end:
                raise ValueError(
                    "Training start year cannot exceed training end year"
                )

            if not isinstance(symbols, list) or not symbols:
                raise ValueError(
                    "At least one symbol is required"
                )

            # -----------------------------------------
            # Apply training period
            # -----------------------------------------

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

            logger.info(
                "Walk-forward training optimization started",
                extra={
                    "train_start": train_start,
                    "train_end": train_end,
                    "symbol_count": len(symbols)
                }
            )

            # -----------------------------------------
            # Optimize training period
            # -----------------------------------------

            results = self.optimizer.evaluate_configs(
                portfolio_engine,
                db,
                symbols
            )

            if not isinstance(results, dict):
                raise ValueError(
                    "Parameter optimizer must return a dictionary"
                )

            if not results.get("best_strategy"):
                raise ValueError(
                    "No valid strategy found during training optimization"
                )

            logger.info(
                "Training optimization completed",
                extra={
                    "train_start": train_start,
                    "train_end": train_end,
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return results

        except Exception:
            logger.exception(
                "Training window optimization failed",
                extra={
                    "train_start": train_start,
                    "train_end": train_end
                }
            )
            raise

        finally:
            # Always restore original portfolio dates.
            portfolio_engine.config.start_date = original_start
            portfolio_engine.config.end_date = original_end

            logger.debug(
                "Original portfolio date configuration restored"
            )

    # --------------------------------------------------
    # Select Best Parameters
    # --------------------------------------------------

    def select_best_parameters(
        self,
        optimization_results
    ):
        """Extract the best strategy parameters."""

        start_time = time.perf_counter()

        try:
            if not isinstance(optimization_results, dict):
                raise ValueError(
                    "Optimization results must be a dictionary"
                )

            best = optimization_results.get("best_strategy")

            if not isinstance(best, dict):
                raise ValueError(
                    "Best strategy not found in optimization results"
                )

            parameters = self._validate_parameters(best)

            net_profit = best.get("net_profit")
            win_rate = best.get("win_rate")

            for field, value in (
                ("net_profit", net_profit),
                ("win_rate", win_rate)
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    raise ValueError(
                        f"Invalid {field} in best strategy"
                    )

            if not 0 <= win_rate <= 100:
                raise ValueError(
                    "Win rate must be between 0 and 100"
                )

            result = {
                **parameters,
                "net_profit": round(net_profit, 2),
                "win_rate": round(win_rate, 2)
            }

            logger.info(
                "Best training parameters selected",
                extra={
                    **result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Best parameter selection failed"
            )
            raise

    # --------------------------------------------------
    # Optimize
    # --------------------------------------------------

    def optimize(
        self,
        portfolio_engine,
        db,
        symbols,
        train_start,
        train_end
    ):
        """
        Optimize training parameters and apply the best result.

        Original strategy parameters are included in the
        returned dictionary for restoration after testing.
        """

        start_time = time.perf_counter()

        original_parameters = {
            "short_ma": portfolio_engine.config.strategy.short_ma,
            "medium_ma": portfolio_engine.config.strategy.medium_ma,
            "long_ma": portfolio_engine.config.strategy.long_ma
        }

        try:
            original_parameters = self._validate_parameters(
                original_parameters
            )

            logger.info(
                "Walk-forward optimization started",
                extra={
                    "train_start": train_start,
                    "train_end": train_end,
                    "original_parameters": original_parameters
                }
            )

            results = self.optimize_training_window(
                portfolio_engine,
                db,
                symbols,
                train_start,
                train_end
            )

            best = self.select_best_parameters(results)

            # Apply the best training parameters.
            self.apply_best_parameters(
                portfolio_engine,
                best
            )

            # Keep original parameters for test cleanup.
            best["original_parameters"] = original_parameters

            logger.info(
                "Walk-forward optimization completed",
                extra={
                    "selected_parameters": {
                        key: best[key]
                        for key in (
                            "short_ma",
                            "medium_ma",
                            "long_ma"
                        )
                    },
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return best

        except Exception:
            logger.exception(
                "Walk-forward optimization failed"
            )

            # Prevent failed optimization from leaving
            # the portfolio with partially changed parameters.
            self.restore_original_parameters(
                portfolio_engine,
                original_parameters
            )

            raise

    # --------------------------------------------------
    # Apply Best Parameters
    # --------------------------------------------------

    def apply_best_parameters(
        self,
        portfolio_engine,
        best_parameters
    ):
        """Apply selected moving average parameters."""

        start_time = time.perf_counter()

        try:
            parameters = self._validate_parameters(
                best_parameters
            )

            strategy_config = portfolio_engine.config.strategy

            old_parameters = {
                "short_ma": strategy_config.short_ma,
                "medium_ma": strategy_config.medium_ma,
                "long_ma": strategy_config.long_ma
            }

            try:
                strategy_config.short_ma = parameters["short_ma"]
                strategy_config.medium_ma = parameters["medium_ma"]
                strategy_config.long_ma = parameters["long_ma"]

                self._rebuild_strategy(portfolio_engine)

            except Exception:
                strategy_config.short_ma = old_parameters["short_ma"]
                strategy_config.medium_ma = old_parameters["medium_ma"]
                strategy_config.long_ma = old_parameters["long_ma"]

                self._rebuild_strategy(portfolio_engine)
                raise

            logger.info(
                "Best strategy parameters applied",
                extra={
                    **parameters,
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

        except Exception:
            logger.exception(
                "Failed to apply best strategy parameters"
            )
            raise

    # --------------------------------------------------
    # Restore Original Parameters
    # --------------------------------------------------

    def restore_original_parameters(
        self,
        portfolio_engine,
        original_parameters
    ):
        """Restore original moving average configuration."""

        start_time = time.perf_counter()

        try:
            parameters = self._validate_parameters(
                original_parameters
            )

            strategy_config = portfolio_engine.config.strategy

            strategy_config.short_ma = parameters["short_ma"]
            strategy_config.medium_ma = parameters["medium_ma"]
            strategy_config.long_ma = parameters["long_ma"]

            self._rebuild_strategy(portfolio_engine)

            logger.info(
                "Original strategy parameters restored",
                extra={
                    **parameters,
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

        except Exception:
            logger.exception(
                "Failed to restore original strategy parameters"
            )
            raise
