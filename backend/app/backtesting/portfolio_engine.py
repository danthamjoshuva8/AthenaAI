from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.trade_decision import TradeDecision
from app.config.backtest_config import BacktestConfig
from app.backtesting.trading_cost_engine import TradingCostEngine
from app.backtesting.market_condition_engine import MarketConditionEngine
from app.backtesting.sector_engine import SectorEngine
from app.backtesting.parameter_optimizer import ParameterOptimizer
from app.utils.report_exporter import ReportExporter
from app.utils.nifty200 import get_nifty200_symbols
from datetime import date
from app.backtesting.walk_forward_optimizer import WalkForwardOptimizer
from app.backtesting.monte_carlo_engine import MonteCarloEngine
from app.backtesting.strategy_intelligence import StrategyIntelligence
from collections import defaultdict
from collections import defaultdict

class PortfolioEngine:

    def __init__(self):

        self.config = BacktestConfig()

        self.backtest_engine = BacktestEngine(
            self.config
        )

        self.cost_engine = TradingCostEngine()

        self.market_engine = MarketConditionEngine()

        self.sector_engine = SectorEngine()

        self.optimizer = ParameterOptimizer()

        self.report_exporter = ReportExporter()

        self.walk_forward_optimizer = WalkForwardOptimizer()

        self.monte_carlo_engine = MonteCarloEngine()

        self.strategy_intelligence_engine = StrategyIntelligence()

    def load_all_trades(
        self,
        db: Session,
        symbols: list
    ):

        portfolio_trades = []

        #
        # Load trades from all symbols
        #
        for symbol in symbols:

            trades = self.backtest_engine.execute_trades(
                db,
                symbol
            )

            for trade in trades:

                trade["symbol"] = symbol

            portfolio_trades.extend(trades)

        #
        # Group trades by entry date
        #
        grouped = defaultdict(list)

        for trade in portfolio_trades:

            grouped[
                trade["entry_date"]
            ].append(trade)

        ranked_trades = []

        #
        # Rank every trading day separately
        #
        for entry_date in sorted(grouped.keys()):

            today = grouped[entry_date]

            #
            # Highest score first
            #
            today.sort(

                key=lambda x: x.get(
                    "total_score",
                    0
                ),

                reverse=True

            )

            ranked_trades.extend(today)

        return ranked_trades

    def build_timeline(
        self,
        trades: list
    ):

        timeline = []

        for trade in trades:

            #
            # BUY EVENT
            #

            timeline.append(

                {

                    "date": trade["entry_date"],

                    "type": "BUY",

                    "symbol": trade["symbol"],

                    "price": trade["entry_price"],

                    "quantity": trade["quantity"],

                    "trade": trade

                }

            )

            #
            # 2R PARTIAL EXIT
            #

            if trade.get("partial_exit_done"):

                timeline.append(

                    {

                        "date": trade["target_2r_date"],

                        "type": "SELL_2R",

                        "symbol": trade["symbol"],

                        "price": trade["target_2r"],

                        "quantity": trade["sold_quantity"],

                        "trade": trade

                    }

                )

            #
            # FINAL EXIT
            #

            timeline.append(

                {

                    "date": trade["exit_date"],

                    "type": "SELL",

                    "symbol": trade["symbol"],

                    "price": trade["exit_price"],

                    "quantity": trade["remaining_quantity"],

                    "trade": trade

                }

            )

        priority = {
            "SELL": 0,
            "SELL_2R": 1,
            "BUY": 2
        }

        timeline.sort(
            key=lambda event: (
                event["date"],
                priority[event["type"]]
            )
        )

        return timeline
    
    def execute_portfolio(
        self,
        db: Session,
        symbols: list
    ):
        daily_entries = defaultdict(int)

        trades = self.load_all_trades(
            db,
            symbols
        )

        #
        # Rank trades by day
        #
        trades = self.rank_daily_trades(trades)

        timeline = self.build_timeline(
            trades
        )

        portfolio_value = self.config.initial_capital

        available_cash = portfolio_value

        weekly_capital = portfolio_value

        current_week = None

        locked_capital = 0

        open_positions = {}

        executed_trades = []

        skipped_trades = []

        portfolio_events = []

        trade_decisions = []

        for event in timeline:

            event_week = event["date"].isocalendar().week

            if current_week != event_week:

                current_week = event_week

                weekly_capital = portfolio_value

            symbol = event["symbol"]

            trade = event["trade"]

            #
            # BUY
            #

            if event["type"] == "BUY":

                #
                # Already holding this stock
                #

                if symbol in open_positions:

                    continue

                trade_date = event["date"]

                if (
                    daily_entries[trade_date]
                    >= self.config.max_daily_entries
                ):

                    skipped_trades.append(trade)

                    trade_decisions.append(

                        TradeDecision(

                            symbol=symbol,

                            date=trade_date,

                            decision="SKIPPED",

                            reason="DAILY_LIMIT_REACHED"

                        )

                    )

                    continue

                capital_required = trade["capital_used"]

                risk_ratio = capital_required / self.config.initial_capital

                #
                # Fixed
                #

                if self.config.capital_mode == "fixed":

                    capital_required = trade["capital_used"]

                #
                # Compound
                #

                elif self.config.capital_mode == "compound":

                    #
                    # Weekly update
                    #

                    if self.config.capital_update == "weekly":

                        capital_required = weekly_capital * risk_ratio

                    #
                    # Daily update
                    #

                    else:

                        capital_required = portfolio_value * risk_ratio

                #
                # Profit Only
                #

                elif self.config.capital_mode == "profit_only":

                    effective_capital = max(

                        portfolio_value,

                        self.config.initial_capital

                    )

                    #
                    # Weekly update
                    #

                    if self.config.capital_update == "weekly":

                        effective_capital = max(

                            weekly_capital,

                            self.config.initial_capital

                        )

                    capital_required = effective_capital * risk_ratio

                #
                # Not enough cash
                #

                if (

                    self.config.capital_check

                    and

                    capital_required > available_cash

                ):

                    skipped_trades.append(trade)

                    trade_decisions.append(

                        TradeDecision(

                            symbol=symbol,

                            date=event["date"],

                            decision="SKIPPED",

                            reason="INSUFFICIENT_CAPITAL",

                            capital_required=capital_required,

                            available_capital=available_cash

                        )

                    )

                    continue

                #
                # Execute BUY
                #

                open_positions[symbol] = {

                    "trade": trade,

                    "locked_capital": capital_required

                }

                available_cash -= capital_required

                locked_capital += capital_required

                capital_limit = portfolio_value

                if self.config.capital_mode != "compound":
                    capital_limit = self.config.initial_capital

                if (
                    self.config.capital_check
                    and locked_capital > capital_limit
                ):
                    raise Exception(
                        f"""
                Capital exceeded

                Date: {event['date']}
                Symbol: {symbol}

                Locked Capital : {locked_capital}

                Capital Limit : {capital_limit}

                Available Cash : {available_cash}

                Portfolio Value : {portfolio_value}
                """
                    )

                executed_trades.append(trade)
                daily_entries[event["date"]] += 1

            elif event["type"] == "SELL_2R":

                released = open_positions[symbol]["locked_capital"] * (
                    trade["sold_quantity"] /
                    trade["quantity"]
                )

                available_cash += released
                locked_capital -= released
                open_positions[symbol]["locked_capital"] -= released

            #
            # FINAL EXIT
            #

            elif event["type"] == "SELL":

                if symbol not in open_positions:

                    continue

                released = open_positions[symbol]["locked_capital"]

                available_cash += released

                locked_capital -= released

                #
                # Calculate trading cost
                #

                buy_value = (

                    trade["entry_price"]

                    * trade["quantity"]

                )

                sell_value = (

                    trade["exit_price"]

                    * trade["quantity"]

                )

                cost = self.cost_engine.calculate_trade_cost(

                    buy_value,

                    sell_value

                )

                trade["trading_cost"] = cost

                trade["profit"] -= cost["total"]

                #
                # Compound mode
                #

                if self.config.capital_mode == "compound":

                    portfolio_value += trade["profit"]

                    available_cash += trade["profit"]
                    if available_cash < -0.01:
                        raise Exception("Negative cash balance")

                del open_positions[symbol]

            #
            # Portfolio Validation
            #

            total_assets = available_cash + locked_capital

            if abs(total_assets - portfolio_value) > 1:

                raise Exception(

                    f"""
            Portfolio mismatch

            Date : {event['date']}

            Portfolio : {portfolio_value}

            Cash : {available_cash}

            Locked : {locked_capital}

            Total : {total_assets}
            """
                )
            portfolio_events.append(

                {

                    **event,

                    "available_cash": round(
                        available_cash,
                        2
                    ),

                    "portfolio_value": round(
                        portfolio_value,
                        2
                    ),

                    "locked_capital": round(
                        locked_capital,
                        2
                    ),

                    "open_positions": len(
                        open_positions
                    )

                }

            )

        return {

            "timeline": portfolio_events,

            "executed_trades": executed_trades,

            "skipped_trades": skipped_trades,

            "trade_decisions": [

                vars(decision)

                for decision in trade_decisions

            ]

        }
    
    def portfolio_summary(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        total_trades = len(trades)

        winning = 0

        losing = 0

        net_profit = 0

        best_trade = 0

        worst_trade = 0

        for trade in trades:

            profit = trade["profit"]

            net_profit += profit

            if profit > 0:

                winning += 1

            else:

                losing += 1

            best_trade = max(
                best_trade,
                profit
            )

            worst_trade = min(
                worst_trade,
                profit
            )

        return {

            "total_trades": total_trades,

            "winning_trades": winning,

            "losing_trades": losing,

            "win_rate": round(

                (winning / total_trades) * 100,

                2

            ) if total_trades else 0,

            "net_profit": round(
                net_profit,
                2
            ),

            "average_profit": round(

                net_profit / total_trades,

                2

            ) if total_trades else 0,

            "best_trade": round(
                best_trade,
                2
            ),

            "worst_trade": round(
                worst_trade,
                2
            )
        }
    
    def portfolio_statistics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        executed_trades = portfolio["executed_trades"]

        skipped_trades = portfolio["skipped_trades"]

        timeline = portfolio["timeline"]

        total_opportunities = len(executed_trades) + len(skipped_trades)

        #
        # Cash statistics
        #

        cash_values = [

            event["available_cash"]

            for event in timeline

        ]

        average_cash = (

            sum(cash_values) / len(cash_values)

            if cash_values

            else 0

        )

        #
        # Open positions
        #

        open_positions = [

            event["open_positions"]

            for event in timeline

        ]

        average_open_positions = (

            sum(open_positions) / len(open_positions)

            if open_positions

            else 0

        )

        max_open_positions = (

            max(open_positions)

            if open_positions

            else 0

        )

        #
        # Capital utilization
        #

        utilization = []

        for event in timeline:

            portfolio_value = event["portfolio_value"]

            if portfolio_value > 0:
                utilization.append(
                    (event["locked_capital"] / portfolio_value) * 100
                )
            else:
                utilization.append(0)

        average_utilization = (

            sum(utilization) / len(utilization)

            if utilization

            else 0

        )

        max_utilization = (

            max(utilization)

            if utilization

            else 0

        )

        return {

            "total_opportunities": total_opportunities,

            "executed_trades": len(executed_trades),

            "skipped_trades": len(skipped_trades),

            "execution_rate": round(

                (

                    len(executed_trades)

                    / total_opportunities

                )

                * 100,

                2

            ) if total_opportunities else 0,

            "average_cash": round(
                average_cash,
                2
            ),

            "average_open_positions": round(
                average_open_positions,
                2
            ),

            "max_open_positions": max_open_positions,

            "average_capital_utilization": round(
                average_utilization,
                2
            ),

            "max_capital_utilization": round(
                max_utilization,
                2
            )

        }
    
    def trade_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        gross_profit = 0

        gross_loss = 0

        winning = []

        losing = []

        for trade in trades:

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            if profit > 0:

                gross_profit += profit

                winning.append(profit)

            else:

                gross_loss += abs(profit)

                losing.append(profit)

        total = len(trades)

        winning_trades = len(winning)

        losing_trades = len(losing)

        win_rate = (

            winning_trades * 100 / total

            if total

            else 0

        )

        average_win = (

            sum(winning) / len(winning)

            if winning else 0

        )

        average_loss = (

            abs(sum(losing)) / len(losing)

            if losing else 0

        )

        expectancy = (

            sum(

                trade.get(
                    "net_profit",
                    trade["profit"]
                )

                for trade in trades

            ) / total

            if total else 0

        )

        profit_factor = (

            gross_profit / gross_loss

            if gross_loss else 0

        )

        trade_values = self.calculate_average_trade_values(

            trades

        )

        streaks = self.calculate_trade_streaks(

            trades

        )

        distribution = self.calculate_trade_distribution(

            trades

        )

        risk_metrics = self.calculate_risk_metrics(

            trades

        )

        return {

            "total_trades": total,

            "winning_trades": winning_trades,

            "losing_trades": losing_trades,

            "win_rate": round(

                win_rate,

                2

            ),

            "gross_profit": round(
                gross_profit,
                2
            ),

            "gross_loss": round(
                gross_loss,
                2
            ),

            "net_profit": round(
                gross_profit - gross_loss,
                2
            ),

            "profit_factor": round(
                profit_factor,
                2
            ),

            "average_win": round(
                average_win,
                2
            ),

            "average_loss": round(
                average_loss,
                2
            ),

            "expectancy": round(
                expectancy,
                2
            ),

            "largest_win": round(
                max(winning) if winning else 0,
                2
            ),

            "largest_loss": round(
                min(losing) if losing else 0,
                2
            ),

            "expectancy":

                self.calculate_expectancy(

                    trades
        
                ),

            "profit_factor":

                self.calculate_profit_factor(

                    trades

                ),

            "average_win":

                trade_values["average_win"],

            "average_loss":

                trade_values["average_loss"],

            "reward_risk_ratio":

                self.calculate_reward_risk_ratio(

                    trades

                ),

            "max_winning_streak":

                streaks["max_winning_streak"],

            "max_losing_streak":

                streaks["max_losing_streak"],

            "trade_distribution":

                distribution,

            "risk_metrics":

                risk_metrics,

            "trade_score":

                self.calculate_trade_score(

                    trades

                )

        }
    
    def risk_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        consecutive_wins = 0
        consecutive_losses = 0

        max_consecutive_wins = 0
        max_consecutive_losses = 0

        current_wins = 0
        current_losses = 0

        equity = self.config.initial_capital

        peak = equity

        max_drawdown = 0

        longest_drawdown = 0
        current_drawdown = 0

        for trade in trades:

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            #
            # Win / Loss Streak
            #

            if profit > 0:

                current_wins += 1
                current_losses = 0

            else:

                current_losses += 1
                current_wins = 0

            max_consecutive_wins = max(
                max_consecutive_wins,
                current_wins
            )

            max_consecutive_losses = max(
                max_consecutive_losses,
                current_losses
            )

            #
            # Equity
            #

            equity += profit

            if equity > peak:

                peak = equity

                current_drawdown = 0

            else:

                current_drawdown += 1

                longest_drawdown = max(
                    longest_drawdown,
                    current_drawdown
                )

                drawdown = (

                    (peak - equity)

                    / peak

                ) * 100

                max_drawdown = max(
                    max_drawdown,
                    drawdown
                )

        return {

            "max_consecutive_wins": max_consecutive_wins,

            "max_consecutive_losses": max_consecutive_losses,

            "max_drawdown_percent": round(
                max_drawdown,
                2
            ),

            "longest_drawdown_trades": longest_drawdown,

            "ending_equity": round(
                equity,
                2
            )

        }
    
    def holding_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        holding_days = []

        winning_days = []

        losing_days = []

        for trade in trades:

            days = trade["holding_days"]

            holding_days.append(days)

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            if profit > 0:

                winning_days.append(days)

            else:

                losing_days.append(days)

        return {

            "average_holding_days": round(

                sum(holding_days) / len(holding_days),

                2

            ) if holding_days else 0,

            "average_winning_days": round(

                sum(winning_days) / len(winning_days),

                2

            ) if winning_days else 0,

            "average_losing_days": round(

                sum(losing_days) / len(losing_days),

                2

            ) if losing_days else 0,

            "maximum_holding_days": max(
                holding_days
            ) if holding_days else 0,

            "minimum_holding_days": min(
                holding_days
            ) if holding_days else 0

        }
    
    def monthly_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        monthly = {}

        for trade in trades:

            date = trade["exit_date"]

            key = f"{date.year}-{date.month:02d}"

            if key not in monthly:

                monthly[key] = {

                    "trades": 0,

                    "wins": 0,

                    "losses": 0,

                    "profit": 0

                }

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            monthly[key]["trades"] += 1

            monthly[key]["profit"] += profit

            if profit > 0:

                monthly[key]["wins"] += 1

            else:

                monthly[key]["losses"] += 1

        report = []

        for month, data in sorted(monthly.items()):

            report.append({

                "month": month,

                "trades": data["trades"],

                "wins": data["wins"],

                "losses": data["losses"],

                "win_rate": round(

                    data["wins"]

                    / data["trades"]

                    * 100,

                    2

                ),

                "profit": round(
                    data["profit"],
                    2
                )

            })

        return report
    
    def yearly_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        yearly = {}

        for trade in trades:

            year = trade["exit_date"].year

            if year not in yearly:

                yearly[year] = {

                    "trades": 0,

                    "wins": 0,

                    "losses": 0,

                    "profit": 0

                }

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            yearly[year]["trades"] += 1

            yearly[year]["profit"] += profit

            if profit > 0:

                yearly[year]["wins"] += 1

            else:

                yearly[year]["losses"] += 1

        report = []

        for year, data in sorted(yearly.items()):

            report.append(

                {

                    "year": year,

                    "trades": data["trades"],

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(

                        data["wins"]

                        / data["trades"]

                        * 100,

                        2

                    ),

                    "profit": round(

                        data["profit"],

                        2

                    )

                }

            )

        return report
    
    def market_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        report = {}

        for trade in trades:

            market = self.market_engine.classify_market(
                trade
            )

            if market not in report:

                report[market] = {

                    "trades": 0,

                    "wins": 0,

                    "losses": 0,

                    "profit": 0

                }

            report[market]["trades"] += 1

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            report[market]["profit"] += profit

            if profit > 0:

                report[market]["wins"] += 1

            else:

                report[market]["losses"] += 1

        result = []

        for market, data in report.items():

            result.append({

                "market": market,

                "trades": data["trades"],

                "wins": data["wins"],

                "losses": data["losses"],

                "win_rate": round(

                    data["wins"]

                    / data["trades"]

                    * 100,

                    2

                ),

                "profit": round(
                    data["profit"],
                    2
                )

            })

        return result
    
    def sector_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        trades = portfolio["executed_trades"]

        sectors = {}

        for trade in trades:

            sector = self.sector_engine.get_sector(

                trade["symbol"]

            )

            if sector not in sectors:

                sectors[sector] = {

                    "trades": 0,

                    "wins": 0,

                    "losses": 0,

                    "profit": 0

                }

            profit = trade.get(

                "net_profit",

                trade["profit"]

            )

            sectors[sector]["trades"] += 1

            sectors[sector]["profit"] += profit

            if profit > 0:

                sectors[sector]["wins"] += 1

            else:

                sectors[sector]["losses"] += 1

        report = []

        for sector, data in sectors.items():

            report.append(

                {

                    "sector": sector,

                    "trades": data["trades"],

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(

                        data["wins"]

                        / data["trades"]

                        * 100,

                        2

                    ),

                    "profit": round(

                        data["profit"],

                        2

                    )

                }

            )

        return report
    
    def skipped_trade_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        executed = portfolio["executed_trades"]

        skipped = portfolio["skipped_trades"]

        missed_profit = 0

        missed_loss = 0

        profitable_skipped = 0

        losing_skipped = 0

        for trade in skipped:

            profit = trade.get(
                "net_profit",
                trade["profit"]
            )

            if profit > 0:

                profitable_skipped += 1

                missed_profit += profit

            else:

                losing_skipped += 1

                missed_loss += abs(profit)

        return {

            "total_opportunities":

                len(executed) + len(skipped),

            "executed_trades":

                len(executed),

            "skipped_trades":

                len(skipped),

            "profitable_skipped":

                profitable_skipped,

            "losing_skipped":

                losing_skipped,

            "missed_profit":

                round(missed_profit,2),

            "missed_loss":

                round(missed_loss,2),

            "net_missed":

                round(

                    missed_profit - missed_loss,

                    2

                )

        }
    
    def capital_utilization_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        timeline = portfolio["timeline"]

        utilization = []

        cash = []

        open_positions = []

        for event in timeline:

            portfolio_value = event["portfolio_value"]

            if portfolio_value > 0:
                utilization.append(
                    (event["locked_capital"] / portfolio_value) * 100
                )
            else:
                utilization.append(0)

            cash.append(

                event["available_cash"]

            )

            open_positions.append(

                event["open_positions"]

            )

        return {

            "average_utilization": round(

                sum(utilization)

                / len(utilization),

                2

            ) if utilization else 0,

            "maximum_utilization": round(

                max(utilization),

                2

            ) if utilization else 0,

            "minimum_utilization": round(

                min(utilization),

                2

            ) if utilization else 0,

            "average_available_cash": round(

                sum(cash)

                / len(cash),

                2

            ) if cash else 0,

            "minimum_available_cash": round(

                min(cash),

                2

            ) if cash else 0,

            "maximum_open_positions": max(

                open_positions

            ) if open_positions else 0,

            "average_open_positions": round(

                sum(open_positions)

                / len(open_positions),

                2

            ) if open_positions else 0

        }

    def overlap_analytics(
        self,
        db: Session,
        symbols: list
    ):

        portfolio = self.execute_portfolio(
            db,
            symbols
        )

        timeline = portfolio["timeline"]

        overlap_distribution = {}

        max_overlap = 0

        for event in timeline:

            positions = event["open_positions"]

            max_overlap = max(
                max_overlap,
                positions
            )

            overlap_distribution[positions] = (

                overlap_distribution.get(
                    positions,
                    0
                ) + 1

            )

        report = []

        total_events = len(timeline)

        for positions in sorted(overlap_distribution.keys()):

            count = overlap_distribution[positions]

            report.append(

                {

                    "open_positions": positions,

                    "events": count,

                    "percentage": round(

                        (count / total_events) * 100,

                        2

                    )

                }

            )

        return {

            "maximum_overlap": max_overlap,

            "distribution": report

        }
    
    def optimize_strategy(
        self,
        db,
        symbols
    ):

        results = self.optimizer.evaluate_configs(
            self,
            db,
            symbols
        )

        report_path = self.report_exporter.export_csv(results)

        return {

            "report": report_path,

            "results": results

        }
    
    def generate_walk_forward_windows(
        self,
        start_year: int,
        end_year: int
    ):

        windows = []

        #
        # Need at least 1 training year
        #

        for train_end in range(
            start_year,
            end_year
        ):

            windows.append(

                {

                    "train_start": start_year,

                    "train_end": train_end,

                    "test_year": train_end + 1

                }

            )

        return windows
    
    def walk_forward_analysis(
        self,
        db
    ):

        windows = self.generate_walk_forward_windows(

            2022,

            2026

        )

        results = []

        optimization_history = []

        for window in windows:

            result = self.execute_walk_forward_window(

                db,

                window["train_start"],

                window["train_end"],

                window["test_year"]

            )

            optimization_history.append(

                {

                    "training_period": (

                        f"{window['train_start']}"

                        f"-"

                        f"{window['train_end']}"

                    ),

                    "test_year": window["test_year"],

                    "best_parameters": result["best_parameters"]

                }

            )

            results.append(result)

        average_profit = round(

            sum(

                result["net_profit"]

                for result in results

            ) / len(results),

            2

        ) if results else 0

        average_win_rate = round(

            sum(

                result["win_rate"]

                for result in results

            ) / len(results),

            2

        ) if results else 0

        best_window = max(

            results,

            key=lambda x: x["net_profit"],

            default=None

        )

        return {

            "total_windows": len(results),

            "average_profit": average_profit,

            "average_win_rate": average_win_rate,

            "best_window": best_window,

            "optimization_history": optimization_history,

            "results": results

        }

    def execute_walk_forward_window(
        self,
        db,
        train_start,
        train_end,
        test_year
    ):

        symbols = get_nifty200_symbols()

        #
        # Optimize using training period
        #

        best_parameters = (

            self.walk_forward_optimizer.optimize(

                self,

                db,

                symbols,

                train_start,

                train_end

            )

        )

        #
        # Execute only on test year
        #

        start_date = date(
            test_year,
            1,
            1
        )

        end_date = date(
            test_year,
            12,
            31
        )

        print("=" * 80)

        print(
            f"Training : {train_start}-{train_end}"
        )

        print(
            f"Testing  : {test_year}"
        )

        print(
            f"Using MA : "
            f"{best_parameters['short_ma']} / "
            f"{best_parameters['medium_ma']} / "
            f"{best_parameters['long_ma']}"
        )

        trades = []

        for symbol in symbols:

            try:

                symbol_trades = self.backtest_engine.execute_trades(
                    db,
                    symbol,
                    start_date,
                    end_date
                )

                trades.extend(symbol_trades)

            except Exception as ex:

                print(f"Skipping {symbol}: {ex}")

        winning_trades = sum(

            1

            for trade in trades

            if trade["profit"] > 0

        )

        losing_trades = len(trades) - winning_trades

        win_rate = (

            round(

                winning_trades * 100 / len(trades),

                2

            )

            if trades

            else 0

        )

        average_profit = (

            round(

                sum(

                    trade["profit"]

                    for trade in trades

                ) / len(trades),

                2

            )

            if trades

            else 0

        )

        best_trade = (

            round(

                max(

                    trade["profit"]

                    for trade in trades

                ),

                2

            )

            if trades

            else 0

        )

        worst_trade = (

            round(

                min(

                    trade["profit"]

                    for trade in trades

                ),

                2

            )

            if trades

            else 0

        )

        self.walk_forward_optimizer.restore_original_parameters(

            self,

            best_parameters["original_parameters"]

        )

        return {

            "train_start": train_start,

            "train_end": train_end,

            "test_year": test_year,

            "best_parameters": best_parameters,

            "total_trades": len(trades),

            "winning_trades": winning_trades,

            "losing_trades": losing_trades,

            "win_rate": win_rate,

            "net_profit": round(

                sum(

                    trade["profit"]

                    for trade in trades

                ),

                2

            ),

            "average_profit": average_profit,

            "best_trade": best_trade,

            "worst_trade": worst_trade

        }
    
    def monte_carlo_analysis(

        self,

        db,

        symbols,

        simulations=1000

    ):

        trades = []

        for symbol in symbols:

            try:

                symbol_trades = self.backtest_engine.execute_trades(

                    db,

                    symbol

                )

                trades.extend(

                    symbol_trades

                )

            except Exception:

                continue

        return self.monte_carlo_engine.simulation_summary(

            trades,

            simulations

        )

    def calculate_expectancy(

        self,

        trades

    ):

        if not trades:

            return 0

        winning_trades = [

            trade

            for trade in trades

            if trade["profit"] > 0

        ]

        losing_trades = [

            trade

            for trade in trades

            if trade["profit"] <= 0

        ]

        total_trades = len(

            trades

        )

        win_rate = len(

            winning_trades

        ) / total_trades

        loss_rate = len(

            losing_trades

        ) / total_trades

        average_win = (

            sum(

                trade["profit"]

                for trade in winning_trades

            )

            / len(

                winning_trades

            )

            if winning_trades

            else 0

        )

        average_loss = (

            abs(

                sum(

                    trade["profit"]

                    for trade in losing_trades

                )

            )

            / len(

                losing_trades

            )

            if losing_trades

            else 0

        )

        expectancy = (

            win_rate * average_win

        ) - (

            loss_rate * average_loss

        )

        return round(

            expectancy,

            2

        )
    
    def calculate_profit_factor(

        self,

        trades

    ):

        if not trades:

            return 0

        gross_profit = sum(

            trade["profit"]

            for trade in trades

            if trade["profit"] > 0

        )

        gross_loss = abs(

            sum(

                trade["profit"]

                for trade in trades

                if trade["profit"] < 0

            )

        )

        if gross_loss == 0:

            return 0

        return round(

            gross_profit / gross_loss,

            2

        )
    
    def calculate_average_trade_values(

        self,

        trades

    ):

        if not trades:

            return {

                "average_win": 0,

                "average_loss": 0

            }

        winning_trades = [

            trade

            for trade in trades

            if trade["profit"] > 0

        ]

        losing_trades = [

            trade

            for trade in trades

            if trade["profit"] < 0

        ]

        average_win = (

            sum(

                trade["profit"]

                for trade in winning_trades

            )

            /

            len(

                winning_trades

            )

            if winning_trades

            else 0

        )

        average_loss = (

            abs(

                sum(

                    trade["profit"]

                    for trade in losing_trades

                )

            )

            /

            len(

                losing_trades

            )

            if losing_trades

            else 0

        )

        return {

            "average_win": round(

                average_win,

                2

            ),

            "average_loss": round(

                average_loss,

                2

            )

        }
    
    def calculate_reward_risk_ratio(

        self,

        trades

    ):

        trade_values = self.calculate_average_trade_values(

            trades

        )

        average_win = trade_values[

            "average_win"

        ]

        average_loss = trade_values[

            "average_loss"

        ]

        if average_loss == 0:

            return 0

        return round(

            average_win / average_loss,

            2

        )

    def calculate_trade_streaks(

        self,

        trades

    ):

        if not trades:

            return {

                "max_winning_streak": 0,

                "max_losing_streak": 0

            }

        current_win = 0

        current_loss = 0

        max_win = 0

        max_loss = 0

        for trade in trades:

            if trade["profit"] > 0:

                current_win += 1

                current_loss = 0

            else:

                current_loss += 1

                current_win = 0

            max_win = max(

                max_win,

                current_win

            )

            max_loss = max(

                max_loss,

                current_loss

            )

        return {

            "max_winning_streak": max_win,

            "max_losing_streak": max_loss

        }
    
    def calculate_trade_distribution(

        self,

        trades

    ):

        distribution = {

            "loss_greater_than_10": 0,

            "loss_5_to_10": 0,

            "loss_2_to_5": 0,

            "loss_0_to_2": 0,

            "profit_0_to_2": 0,

            "profit_2_to_5": 0,

            "profit_5_to_10": 0,

            "profit_greater_than_10": 0

        }

        for trade in trades:

            risk_percent = (

                trade["profit"]

                /

                trade["entry_price"]

            ) * 100

            if risk_percent < -10:

                distribution["loss_greater_than_10"] += 1

            elif risk_percent < -5:

                distribution["loss_5_to_10"] += 1

            elif risk_percent < -2:

                distribution["loss_2_to_5"] += 1

            elif risk_percent < 0:

                distribution["loss_0_to_2"] += 1

            elif risk_percent < 2:

                distribution["profit_0_to_2"] += 1

            elif risk_percent < 5:

                distribution["profit_2_to_5"] += 1

            elif risk_percent < 10:

                distribution["profit_5_to_10"] += 1

            else:

                distribution["profit_greater_than_10"] += 1

        return distribution
    
    def calculate_risk_metrics(

        self,

        trades

    ):

        if not trades:

            return {

                "win_loss_ratio": 0,

                "payoff_ratio": 0

            }

        winning_trades = [

            trade

            for trade in trades

            if trade["profit"] > 0

        ]

        losing_trades = [

            trade

            for trade in trades

            if trade["profit"] < 0

        ]

        total_wins = len(

            winning_trades

        )

        total_losses = len(

            losing_trades

        )

        average_win = (

            sum(

                trade["profit"]

                for trade in winning_trades

            )

            /

            total_wins

            if total_wins

            else 0

        )

        average_loss = (

            abs(

                sum(

                    trade["profit"]

                    for trade in losing_trades

                )

            )

            /

            total_losses

            if total_losses

            else 0

        )

        return {

            "win_loss_ratio": round(

                total_wins / total_losses,

                2

            ) if total_losses else 0,

            "payoff_ratio": round(

                average_win / average_loss,

                2

            ) if average_loss else 0

        }
    
    def generate_trade_report(

        self,

        trades

    ):

        trade_values = self.calculate_average_trade_values(

            trades

        )

        streaks = self.calculate_trade_streaks(

            trades

        )

        distribution = self.calculate_trade_distribution(

            trades

        )

        risk_metrics = self.calculate_risk_metrics(

            trades

        )

        winning_trades = [

            trade

            for trade in trades

            if trade["profit"] > 0

        ]

        losing_trades = [

            trade

            for trade in trades

            if trade["profit"] < 0

        ]

        total_trades = len(

            trades

        )

        return {

            "summary": {

                "total_trades": total_trades,

                "winning_trades": len(

                    winning_trades

                ),

                "losing_trades": len(

                    losing_trades

                ),

                "win_rate": round(

                    (

                        len(

                            winning_trades

                        )

                        /

                        total_trades

                        * 100

                    ),

                    2

                ) if total_trades else 0

            },

            "performance": {

                "expectancy":

                    self.calculate_expectancy(

                        trades

                    ),

                "profit_factor":

                    self.calculate_profit_factor(

                        trades

                    ),

                "average_win":

                    trade_values["average_win"],

                "average_loss":

                    trade_values["average_loss"],

                "reward_risk_ratio":

                    self.calculate_reward_risk_ratio(

                        trades

                    )

            },

            "risk": {

                **risk_metrics,

                **streaks

            },

            "distribution":

                distribution

        }

    def calculate_trade_score(

        self,

        trades

    ):

        if not trades:

            return 0

        expectancy = self.calculate_expectancy(

            trades

        )

        profit_factor = self.calculate_profit_factor(

            trades

        )

        reward_risk = self.calculate_reward_risk_ratio(

            trades

        )

        winning_trades = sum(

            1

            for trade in trades

            if trade["profit"] > 0

        )

        win_rate = (

            winning_trades

            * 100

            / len(trades)

        )

        score = 0

        #
        # Win Rate
        #

        score += min(

            win_rate,

            30

        )

        #
        # Profit Factor
        #

        score += min(

            profit_factor * 10,

            30

        )

        #
        # Reward Risk
        #

        score += min(

            reward_risk * 10,

            20

        )

        #
        # Expectancy
        #

        if expectancy > 0:

            score += 20

        return round(

            score,

            2

        )
    
    def strategy_health(

        self,

        db,

        symbols

    ):

        analytics = self.trade_analytics(

            db,

            symbols

        )

        return self.strategy_intelligence_engine.strategy_health(

            analytics

        )
    
    def strategy_confidence(

        self,

        db,

        symbols

    ):

        analytics = self.trade_analytics(

            db,

            symbols

        )

        return self.strategy_intelligence_engine.strategy_confidence(

            analytics

        )
    
    def market_regime(

        self,

        db,

        symbol

    ):

        df = self.backtest_engine.strategy.calculate_moving_averages(

            db,

            symbol

        )

        if df.empty:

            return {

                "market_regime": "Unknown"

            }

        latest = df.iloc[-1]

        return self.strategy_intelligence_engine.market_regime(

            latest_close=latest["close"],

            long_ma=latest["MA_LONG"]

        )
    
    def strategy_recommendation(

        self,

        db,

        symbol,

        symbols

    ):

        health = self.strategy_health(

            db,

            symbols

        )

        confidence = self.strategy_confidence(

            db,

            symbols

        )

        regime = self.market_regime(

            db,

            symbol

        )

        return self.strategy_intelligence_engine.strategy_recommendation(

            health,

            confidence,

            regime["market_regime"]

        )
    
    def risk_recommendation(

        self,

        db,

        symbols

    ):

        health = self.strategy_health(

            db,

            symbols

        )

        confidence = self.strategy_confidence(

            db,

            symbols

        )

        return self.strategy_intelligence_engine.risk_recommendation(

            health,

            confidence

        )
    
    def strategy_summary(

        self,

        db,

        symbol,

        symbols

    ):

        health = self.strategy_health(

            db,

            symbols

        )

        confidence = self.strategy_confidence(

            db,

            symbols

        )

        regime = self.market_regime(

            db,

            symbol

        )

        recommendation = self.strategy_intelligence_engine.strategy_recommendation(

            health,

            confidence,

            regime["market_regime"]

        )

        risk = self.strategy_intelligence_engine.risk_recommendation(

            health,

            confidence

        )

        return self.strategy_intelligence_engine.strategy_summary(

            health,

            confidence,

            regime,

            recommendation,

            risk

        )
    
    def strategy_intelligence(

        self,

        db,

        symbol,

        symbols

    ):

        summary = self.strategy_summary(

            db,

            symbol,

            symbols

        )

        return self.strategy_intelligence_engine.strategy_intelligence(

            summary

        )

    def rank_daily_trades(
        self,
        trades: list
    ):

        grouped = defaultdict(list)

        #
        # Group by entry date
        #
        for trade in trades:

            grouped[
                trade["entry_date"]
            ].append(trade)

        ranked = []

        #
        # Rank each day separately
        #
        for entry_date in sorted(grouped.keys()):

            today = grouped[entry_date]

            today.sort(

                key=lambda x: x.get(
                    "total_score",
                    0
                ),

                reverse=True

            )

            ranked.extend(today)

        return ranked