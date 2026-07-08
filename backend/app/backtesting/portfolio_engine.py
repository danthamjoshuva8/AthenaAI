from sqlalchemy.orm import Session

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.trade_decision import TradeDecision


class PortfolioEngine:

    def __init__(self):

        self.backtest_engine = BacktestEngine()

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
        symbols: list,
        initial_capital: float = 100000
    ):

        trades = self.load_all_trades(
            db,
            symbols
        )

        timeline = self.build_timeline(
            trades
        )

        available_cash = initial_capital

        locked_capital = 0

        open_positions = {}

        portfolio_events = []

        trade_decisions = []

        for event in timeline:

            symbol = event["symbol"]

            trade = event["trade"]

            #
            # BUY
            #

            if event["type"] == "BUY":

                capital_required = trade["capital_used"]

                #
                # Not enough cash
                #

                if capital_required > available_cash:

                    trade_decisions.append(

                        TradeDecision(

                            symbol=symbol,

                            date=event["date"],

                            decision="BUY",

                            reason="CAPITAL_AVAILABLE",

                            capital_required=capital_required,

                            available_capital=available_cash

                        )

                    )

                    continue

                #
                # Execute BUY
                #

                open_positions[symbol] = trade

                available_cash -= capital_required

                locked_capital += capital_required

            elif event["type"] == "SELL_2R":

                released = (

                    trade["entry_price"]

                    * trade["sold_quantity"]

                )

                available_cash += released

                locked_capital -= released

            #
            # FINAL EXIT
            #

            elif event["type"] == "SELL":

                released = (

                    trade["entry_price"]

                    * trade["remaining_quantity"]

                )

                available_cash += released

                locked_capital -= released

                if symbol in open_positions:

                    del open_positions[symbol]

            portfolio_events.append(

                {

                    **event,

                    "available_cash": round(
                        available_cash,
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

        return portfolio_events