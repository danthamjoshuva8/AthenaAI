
import logging
import math
import random
import time


logger = logging.getLogger(__name__)


class MonteCarloEngine:
    """
    Generates Monte Carlo simulations by randomly shuffling trade sequences
    and calculates total profit from executed trades.
    """

    def _validate_trades(self, trades):
        """
        Validate the trade collection and its profit values.
        """

        if not isinstance(trades, list):
            raise ValueError("Trades must be provided as a list.")

        for index, trade in enumerate(trades):
            if not isinstance(trade, dict):
                raise ValueError(
                    f"Trade at index {index} must be a dictionary."
                )

            if "profit" not in trade:
                raise ValueError(
                    f"Trade at index {index} is missing the profit field."
                )

            profit = trade["profit"]

            if (
                isinstance(profit, bool)
                or not isinstance(profit, (int, float))
                or not math.isfinite(profit)
            ):
                raise ValueError(
                    f"Trade at index {index} has an invalid profit value."
                )

    def shuffle_trades(self, trades):
        """
        Return a randomly shuffled copy of the trades.
        The original trade list remains unchanged.
        """

        start_time = time.perf_counter()

        try:
            self._validate_trades(trades)

            shuffled = trades.copy()
            random.shuffle(shuffled)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.debug(
                "monte_carlo_trades_shuffled",
                extra={
                    "event": "monte_carlo_trades_shuffled",
                    "trade_count": len(shuffled),
                    "duration_ms": duration_ms
                }
            )

            return shuffled

        except Exception:
            logger.exception(
                "monte_carlo_trade_shuffle_failed",
                extra={
                    "event": "monte_carlo_trade_shuffle_failed",
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    )
                }
            )
            raise

    def generate_simulations(self, trades, simulations=1000):
        """
        Generate multiple simulations using randomized trade sequences.
        """

        start_time = time.perf_counter()

        try:
            if (
                isinstance(simulations, bool)
                or not isinstance(simulations, int)
                or simulations < 1
            ):
                raise ValueError(
                    "Simulations must be a positive integer."
                )

            self._validate_trades(trades)

            logger.info(
                "monte_carlo_simulations_started",
                extra={
                    "event": "monte_carlo_simulations_started",
                    "trade_count": len(trades),
                    "simulation_count": simulations
                }
            )

            simulation_results = []

            for _ in range(simulations):
                shuffled = trades.copy()
                random.shuffle(shuffled)

                simulation_results.append(shuffled)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_simulations_completed",
                extra={
                    "event": "monte_carlo_simulations_completed",
                    "trade_count": len(trades),
                    "simulation_count": len(simulation_results),
                    "duration_ms": duration_ms
                }
            )

            return simulation_results

        except Exception:
            logger.exception(
                "monte_carlo_simulations_failed",
                extra={
                    "event": "monte_carlo_simulations_failed",
                    "simulation_count": simulations,
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    )
                }
            )
            raise

    def calculate_total_profit(self, trades):
        """
        Calculate the combined profit of all executed trades.
        """

        start_time = time.perf_counter()

        try:
            self._validate_trades(trades)

            total_profit = round(
                sum(trade["profit"] for trade in trades),
                2
            )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_total_profit_calculated",
                extra={
                    "event": "monte_carlo_total_profit_calculated",
                    "trade_count": len(trades),
                    "total_profit": total_profit,
                    "duration_ms": duration_ms
                }
            )

            return total_profit

        except Exception:
            logger.exception(
                "monte_carlo_profit_calculation_failed",
                extra={
                    "event": "monte_carlo_profit_calculation_failed",
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    )
                }
            )
            raise

    
    def simulation_summary(self, trades, simulations=1000, initial_capital=100000):
        """
        Run Monte Carlo simulations and generate a statistical summary
        of profitability and drawdown.
        """

        start_time = time.perf_counter()

        try:
            if (
                isinstance(simulations, bool)
                or not isinstance(simulations, int)
                or simulations < 1
            ):
                raise ValueError("Simulations must be a positive integer.")

            if (
                isinstance(initial_capital, bool)
                or not isinstance(initial_capital, (int, float))
                or not math.isfinite(initial_capital)
                or initial_capital <= 0
            ):
                raise ValueError("Initial capital must be a positive finite number.")

            self._validate_trades(trades)

            if not trades:
                raise ValueError("At least one trade is required for Monte Carlo analysis.")

            logger.info(
                "monte_carlo_summary_started",
                extra={
                    "event": "monte_carlo_summary_started",
                    "trade_count": len(trades),
                    "simulation_count": simulations,
                    "initial_capital": initial_capital
                }
            )

            simulation_results = self.generate_simulations(
                trades,
                simulations
            )

            results = []

            for simulation in simulation_results:

                equity_curve = self.generate_equity_curve(
                    simulation,
                    initial_capital
                )

                total_profit = round(
                    sum(trade["profit"] for trade in simulation),
                    2
                )

                max_drawdown = self.calculate_max_drawdown(
                    equity_curve
                )

                results.append({
                    "profit": total_profit,
                    "max_drawdown": max_drawdown,
                    "equity_curve": equity_curve
                })

            ranked_results = self.rank_simulations(results)

            probability_of_profit = self.calculate_probability_of_profit(
                results
            )

            summary = self.calculate_summary_statistics(results)

            confidence_intervals = self.calculate_confidence_intervals(
                results
            )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "monte_carlo_summary_completed",
                extra={
                    "event": "monte_carlo_summary_completed",
                    "trade_count": len(trades),
                    "simulation_count": len(results),
                    "probability_of_profit": probability_of_profit,
                    "duration_ms": duration_ms
                }
            )

            return {
                "simulations": simulations,
                "probability_of_profit": probability_of_profit,
                "summary": summary,
                "confidence_intervals": confidence_intervals,
                "results": ranked_results
            }

        except Exception:
            logger.exception(
                "monte_carlo_summary_failed",
                extra={
                    "event": "monte_carlo_summary_failed",
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    ),
                    "simulation_count": simulations
                }
            )
            raise


    def generate_equity_curve(self, trades, initial_capital=100000):
        """
        Generate cumulative portfolio equity after every trade.

        Includes initial capital as the first equity point so that
        drawdown calculations account for losses on the first trade.
        """

        start_time = time.perf_counter()

        try:
            self._validate_trades(trades)

            if (
                isinstance(initial_capital, bool)
                or not isinstance(initial_capital, (int, float))
                or not math.isfinite(initial_capital)
                or initial_capital <= 0
            ):
                raise ValueError("Initial capital must be a positive finite number.")

            equity = float(initial_capital)

            # Include starting capital to calculate drawdown correctly.
            curve = [
                round(equity, 2)
            ]

            for trade in trades:
                equity += trade["profit"]

                curve.append(
                    round(equity, 2)
                )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.debug(
                "monte_carlo_equity_curve_generated",
                extra={
                    "event": "monte_carlo_equity_curve_generated",
                    "trade_count": len(trades),
                    "initial_capital": initial_capital,
                    "final_equity": round(equity, 2),
                    "duration_ms": duration_ms
                }
            )

            return curve

        except Exception:
            logger.exception(
                "monte_carlo_equity_curve_failed",
                extra={
                    "event": "monte_carlo_equity_curve_failed",
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    )
                }
            )
            raise


    def calculate_max_drawdown(self, equity_curve):
        """
        Calculate the maximum absolute drawdown from the portfolio peak.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(equity_curve, list):
                raise ValueError("Equity curve must be a list.")

            if not equity_curve:
                return 0.0

            peak = equity_curve[0]
            max_drawdown = 0.0

            for equity in equity_curve:

                if (
                    isinstance(equity, bool)
                    or not isinstance(equity, (int, float))
                    or not math.isfinite(equity)
                ):
                    raise ValueError("Equity curve contains an invalid value.")

                peak = max(peak, equity)

                drawdown = peak - equity

                max_drawdown = max(
                    max_drawdown,
                    drawdown
                )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.debug(
                "monte_carlo_max_drawdown_calculated",
                extra={
                    "event": "monte_carlo_max_drawdown_calculated",
                    "equity_points": len(equity_curve),
                    "max_drawdown": round(max_drawdown, 2),
                    "duration_ms": duration_ms
                }
            )

            return round(max_drawdown, 2)

        except Exception:
            logger.exception(
                "monte_carlo_max_drawdown_failed",
                extra={
                    "event": "monte_carlo_max_drawdown_failed",
                    "equity_points": (
                        len(equity_curve)
                        if isinstance(equity_curve, list)
                        else None
                    )
                }
            )
            raise

    
    def calculate_probability_of_profit(self, simulation_results):
        """
        Calculate the percentage of simulations that generate a profit.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(simulation_results, list):
                raise ValueError("Simulation results must be a list.")

            if not simulation_results:
                return 0.0

            profits = []

            for index, result in enumerate(simulation_results):
                if not isinstance(result, dict) or "profit" not in result:
                    raise ValueError(
                        f"Simulation result at index {index} is missing profit."
                    )

                profit = result["profit"]

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        f"Simulation result at index {index} has invalid profit."
                    )

                profits.append(profit)

            profitable = sum(1 for profit in profits if profit > 0)

            probability = round(
                profitable * 100 / len(profits),
                2
            )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_probability_calculated",
                extra={
                    "event": "monte_carlo_probability_calculated",
                    "simulation_count": len(profits),
                    "profitable_simulations": profitable,
                    "probability_of_profit": probability,
                    "duration_ms": duration_ms
                }
            )

            return probability

        except Exception:
            logger.exception(
                "monte_carlo_probability_calculation_failed",
                extra={
                    "event": "monte_carlo_probability_calculation_failed",
                    "simulation_count": (
                        len(simulation_results)
                        if isinstance(simulation_results, list)
                        else None
                    )
                }
            )
            raise


    def calculate_confidence_intervals(self, simulation_results):
        """
        Calculate profit distribution percentiles across simulations.

        Uses nearest-rank percentile calculation.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(simulation_results, list):
                raise ValueError("Simulation results must be a list.")

            if not simulation_results:
                return {}

            profits = []

            for index, result in enumerate(simulation_results):
                if not isinstance(result, dict) or "profit" not in result:
                    raise ValueError(
                        f"Simulation result at index {index} is missing profit."
                    )

                profit = result["profit"]

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        f"Simulation result at index {index} has invalid profit."
                    )

                profits.append(profit)

            profits.sort()

            n = len(profits)

            def percentile(value):
                index = max(0, math.ceil(value * n) - 1)
                return round(profits[index], 2)

            confidence_intervals = {
                "min": round(profits[0], 2),
                "percentile_5": percentile(0.05),
                "median": percentile(0.50),
                "percentile_95": percentile(0.95),
                "max": round(profits[-1], 2)
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_confidence_intervals_calculated",
                extra={
                    "event": "monte_carlo_confidence_intervals_calculated",
                    "simulation_count": n,
                    "duration_ms": duration_ms
                }
            )

            return confidence_intervals

        except Exception:
            logger.exception(
                "monte_carlo_confidence_intervals_failed",
                extra={
                    "event": "monte_carlo_confidence_intervals_failed",
                    "simulation_count": (
                        len(simulation_results)
                        if isinstance(simulation_results, list)
                        else None
                    )
                }
            )
            raise


    def calculate_summary_statistics(self, simulation_results):
        """
        Calculate profit and drawdown statistics across all simulations.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(simulation_results, list):
                raise ValueError("Simulation results must be a list.")

            if not simulation_results:
                return {}

            profits = []
            drawdowns = []

            for index, result in enumerate(simulation_results):
                if not isinstance(result, dict):
                    raise ValueError(
                        f"Simulation result at index {index} must be a dictionary."
                    )

                for field in ("profit", "max_drawdown"):
                    if field not in result:
                        raise ValueError(
                            f"Simulation result at index {index} "
                            f"is missing {field}."
                        )

                    value = result[field]

                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError(
                            f"Simulation result at index {index} "
                            f"has invalid {field}."
                        )

                if result["max_drawdown"] < 0:
                    raise ValueError(
                        f"Simulation result at index {index} "
                        "has negative maximum drawdown."
                    )

                profits.append(result["profit"])
                drawdowns.append(result["max_drawdown"])

            statistics = {
                "average_profit": round(mean(profits), 2),
                "median_profit": round(median(profits), 2),
                "best_profit": round(max(profits), 2),
                "worst_profit": round(min(profits), 2),
                "profit_std_dev": (
                    round(stdev(profits), 2)
                    if len(profits) > 1 else 0.0
                ),
                "average_drawdown": round(mean(drawdowns), 2),
                "best_drawdown": round(min(drawdowns), 2),
                "worst_drawdown": round(max(drawdowns), 2)
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_summary_statistics_calculated",
                extra={
                    "event": "monte_carlo_summary_statistics_calculated",
                    "simulation_count": len(simulation_results),
                    "duration_ms": duration_ms
                }
            )

            return statistics

        except Exception:
            logger.exception(
                "monte_carlo_summary_statistics_failed",
                extra={
                    "event": "monte_carlo_summary_statistics_failed",
                    "simulation_count": (
                        len(simulation_results)
                        if isinstance(simulation_results, list)
                        else None
                    )
                }
            )
            raise


    def rank_simulations(self, simulation_results):
        """
        Rank simulations by total profit in descending order.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(simulation_results, list):
                raise ValueError("Simulation results must be a list.")

            for index, simulation in enumerate(simulation_results):
                if not isinstance(simulation, dict):
                    raise ValueError(
                        f"Simulation at index {index} must be a dictionary."
                    )

                profit = simulation.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        f"Simulation at index {index} has invalid profit."
                    )

            ranked = sorted(
                simulation_results,
                key=lambda result: result["profit"],
                reverse=True
            )

            ranked_results = [
                {
                    "rank": index + 1,
                    **simulation
                }
                for index, simulation in enumerate(ranked)
            ]

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000, 2
            )

            logger.info(
                "monte_carlo_simulations_ranked",
                extra={
                    "event": "monte_carlo_simulations_ranked",
                    "simulation_count": len(ranked_results),
                    "duration_ms": duration_ms
                }
            )

            return ranked_results

        except Exception:
            logger.exception(
                "monte_carlo_simulation_ranking_failed",
                extra={
                    "event": "monte_carlo_simulation_ranking_failed",
                    "simulation_count": (
                        len(simulation_results)
                        if isinstance(simulation_results, list)
                        else None
                    )
                }
            )
            raise
