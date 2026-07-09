from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.trade_decision import TradeDecision
from app.config.backtest_config import BacktestConfig
from app.backtesting.trading_cost_engine import TradingCostEngine


class PortfolioEngine:

    def __init__(self):

        self.backtest_engine = BacktestEngine()

        self.config = BacktestConfig()

        self.cost_engine = TradingCostEngine()

    def load_all_trades(
        self,
        db: Session,
        symbols: list
    ):

        portfolio_trades = []

        for symbol in symbols:

            trades = self.backtest_engine.execute_trades(
                db,
                symbol
            )

            for trade in trades:

                trade["symbol"] = symbol

            portfolio_trades.extend(trades)

        portfolio_trades.sort(

            key=lambda trade: trade["entry_date"]

        )

        return portfolio_trades
    
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

        timeline.sort(

            key=lambda event: event["date"]

        )

        return timeline
    
    def execute_portfolio(
        self,
        db: Session,
        symbols: list
    ):

        trades = self.load_all_trades(
            db,
            symbols
        )

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

                executed_trades.append(trade)

            elif event["type"] == "SELL_2R":

                released = (

                    trade["entry_price"]

                    * trade["sold_quantity"]

                )

                available_cash += released

                locked_capital -= released

                if symbol in open_positions:

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

                del open_positions[symbol]

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

        initial_capital = self.config.initial_capital

        for event in timeline:

            utilization.append(

                (

                    event["locked_capital"]

                    / initial_capital

                )

                * 100

            )

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