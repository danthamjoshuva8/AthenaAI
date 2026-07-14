import random
import math
from statistics import mean, median, stdev


class MonteCarloEngine:

    def __init__(self):

        pass

    def shuffle_trades(

        self,

        trades

    ):

        shuffled = trades.copy()

        random.shuffle(

            shuffled

        )

        return shuffled
    
    def generate_simulations(

        self,

        trades,

        simulations=1000

    ):

        simulation_results = []

        for _ in range(simulations):

            shuffled = self.shuffle_trades(

                trades

            )

            simulation_results.append(

                shuffled

            )

        return simulation_results
    
    def calculate_total_profit(

        self,

        trades

    ):

        return round(

            sum(

                trade["profit"]

                for trade in trades

            ),

            2

        )
    
    def simulation_summary(

        self,

        trades,

        simulations=1000

    ):

        simulation_results = self.generate_simulations(

            trades,

            simulations

        )

        results = []

        for simulation in simulation_results:

            equity_curve = self.generate_equity_curve(

                simulation

            )

            results.append(

                {

                    "profit": self.calculate_total_profit(

                        simulation

                    ),

                    "max_drawdown": self.calculate_max_drawdown(

                        equity_curve

                    ),

                    "equity_curve": equity_curve

                }

            )

        ranked_results = self.rank_simulations(

            results

        )

        return {

            "simulations": simulations,

            "probability_of_profit":

                self.calculate_probability_of_profit(

                    results

                ),

            "summary":

                self.calculate_summary_statistics(

                    results

                ),

            "confidence_intervals":

                self.calculate_confidence_intervals(

                    results

                ),

            "results": ranked_results

        }
    
    def generate_equity_curve(

        self,

        trades,

        initial_capital=100000

    ):

        equity = initial_capital

        curve = []

        for trade in trades:

            equity += trade["profit"]

            curve.append(

                round(

                    equity,

                    2

                )

            )

        return curve
    
    def calculate_max_drawdown(

        self,

        equity_curve

    ):

        if not equity_curve:

            return 0

        peak = equity_curve[0]

        max_drawdown = 0

        for equity in equity_curve:

            if equity > peak:

                peak = equity

            drawdown = peak - equity

            if drawdown > max_drawdown:

                max_drawdown = drawdown

        return round(

            max_drawdown,

            2

        )
    
    def calculate_probability_of_profit(

        self,

        simulation_results

    ):

        if not simulation_results:

            return 0

        profitable = sum(

            1

            for result in simulation_results

            if result["profit"] > 0

        )

        return round(

            profitable * 100 / len(simulation_results),

            2

        )
    
    def calculate_confidence_intervals(

        self,

        simulation_results

    ):

        if not simulation_results:

            return {}

        profits = sorted(

            result["profit"]

            for result in simulation_results

        )

        n = len(profits)

        return {

            "min": profits[0],

            "percentile_5": profits[

                math.floor(

                    n * 0.05

                )

            ],

            "median": profits[

                math.floor(

                    n * 0.50

                )

            ],

            "percentile_95": profits[

                math.floor(

                    n * 0.95

                )

            ],

            "max": profits[-1]

        }
    
    def calculate_summary_statistics(

        self,

        simulation_results

    ):

        if not simulation_results:

            return {}

        profits = [

            result["profit"]

            for result in simulation_results

        ]

        drawdowns = [

            result["max_drawdown"]

            for result in simulation_results

        ]

        return {

            "average_profit": round(

                mean(

                    profits

                ),

                2

            ),

            "median_profit": round(

                median(

                    profits

                ),

                2

            ),

            "best_profit": round(

                max(

                    profits

                ),

                2

            ),

            "worst_profit": round(

                min(

                    profits

                ),

                2

            ),

            "profit_std_dev": round(

                stdev(

                    profits

                ),

                2

            ) if len(profits) > 1 else 0,

            "average_drawdown": round(

                mean(

                    drawdowns

                ),

                2

            ),

            "best_drawdown": round(

                min(

                    drawdowns

                ),

                2

            ),

            "worst_drawdown": round(

                max(

                    drawdowns

                ),

                2

            )

        }
    
    def rank_simulations(

        self,

        simulation_results

    ):

        ranked = sorted(

            simulation_results,

            key=lambda x: x["profit"],

            reverse=True

        )

        return [

            {

                "rank": index + 1,

                **simulation

            }

            for index, simulation

            in enumerate(ranked)

        ]