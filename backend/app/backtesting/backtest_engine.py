from sqlalchemy.orm import Session

from app.strategies.moving_average import MovingAverageStrategy


class BacktestEngine:

    def __init__(self):

        self.strategy = MovingAverageStrategy()

    def load_signals(
        self,
        db: Session,
        symbol: str
    ):

        return self.strategy.generate_signals(
            db,
            symbol
        )

    def simulate_positions(
        self,
        db: Session,
        symbol: str
    ):

        signals = self.load_signals(
            db,
            symbol
        )

        position = False

        trades = []

        for row in signals:

            action = "HOLD"

            if row["signal"] == "BUY" and not position:

                action = "BUY"

                position = True

            elif row["signal"] == "SELL" and position:

                action = "SELL"

                position = False

            trades.append(

                {

                    "date": row["date"],

                    "close": row["close"],

                    "signal": row["signal"],

                    "action": action,

                    "position": "LONG" if position else "NONE"

                }

            )

        return trades
    
    def execute_trades(
        self,
        db: Session,
        symbol: str
    ):

        positions = self.simulate_positions(
            db,
            symbol
        )

        trades = []

        entry_price = None
        entry_date = None

        for row in positions:

            if row["action"] == "BUY":

                entry_price = row["close"]

                entry_date = row["date"]

            elif row["action"] == "SELL" and entry_price is not None:

                exit_price = row["close"]

                exit_date = row["date"]

                profit = exit_price - entry_price

                profit_percent = (
                    (profit / entry_price) * 100
                )

                trades.append(

                    {

                        "entry_date": entry_date,

                        "exit_date": exit_date,

                        "entry_price": round(entry_price, 2),

                        "exit_price": round(exit_price, 2),

                        "profit": round(profit, 2),

                        "profit_percent": round(
                            profit_percent,
                            2
                        )

                    }

                )

                entry_price = None

                entry_date = None

        return trades
    
    def performance_metrics(
        self,
        db: Session,
        symbol: str
    ):

        trades = self.execute_trades(
            db,
            symbol
        )

        total_trades = len(trades)

        if total_trades == 0:

            return {

                "symbol": symbol,

                "total_trades": 0,

                "winning_trades": 0,

                "losing_trades": 0,

                "win_rate": 0,

                "net_profit": 0,

                "average_profit": 0,

                "best_trade": 0,

                "worst_trade": 0

            }

        profits = [

            trade["profit"]

            for trade in trades

        ]

        winning = [

            p

            for p in profits

            if p > 0

        ]

        losing = [

            p

            for p in profits

            if p <= 0

        ]

        return {

            "symbol": symbol,

            "total_trades": total_trades,

            "winning_trades": len(winning),

            "losing_trades": len(losing),

            "win_rate": round(

                len(winning)

                / total_trades

                * 100,

                2

            ),

            "net_profit": round(

                sum(profits),

                2

            ),

            "average_profit": round(

                sum(profits)

                / total_trades,

                2

            ),

            "best_trade": round(

                max(profits),

                2

            ),

            "worst_trade": round(

                min(profits),

                2

            )

        }
    
    def equity_curve(
        self,
        db: Session,
        symbol: str,
        initial_capital: float = 100000
    ):

        trades = self.execute_trades(
            db,
            symbol
        )

        capital = initial_capital

        curve = []

        for trade in trades:

            capital += trade["profit"]

            curve.append(

                {

                    "exit_date": trade["exit_date"],

                    "capital": round(capital, 2),

                    "profit": trade["profit"]

                }

            )

        return {

            "symbol": symbol,

            "initial_capital": initial_capital,

            "final_capital": round(capital, 2),

            "equity_curve": curve

        }
    
    def drawdown_metrics(
        self,
        db: Session,
        symbol: str
    ):

        equity = self.equity_curve(
            db,
            symbol
        )

        curve = equity["equity_curve"]

        if not curve:

            return {

                "symbol": symbol,

                "max_drawdown": 0,

                "current_drawdown": 0,

                "peak_capital": equity["initial_capital"]

            }

        peak = curve[0]["capital"]

        max_drawdown = 0

        current_drawdown = 0

        for point in curve:

            capital = point["capital"]

            if capital > peak:

                peak = capital

            drawdown = (

                (peak - capital)

                / peak

            ) * 100

            if drawdown > max_drawdown:

                max_drawdown = drawdown

            current_drawdown = drawdown

        return {

            "symbol": symbol,

            "peak_capital": round(peak, 2),

            "max_drawdown": round(max_drawdown, 2),

            "current_drawdown": round(current_drawdown, 2)

        }