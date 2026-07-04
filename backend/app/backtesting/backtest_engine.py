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

    def _open_position(
        self,
        row: dict
    ):

        return {

            "entry_date": row["date"],

            "entry_price": row["entry_price"],

            "stop_loss": row["stop_loss"]

        }

    def _resolve_exit(
        self,
        row: dict,
        position: dict
    ):

        stop_loss = position["stop_loss"]

        if (
            stop_loss is not None
            and row["low"] <= stop_loss
        ):

            return {

                "exit_price": stop_loss,

                "exit_reason": "STOP_LOSS"

            }

        ma15 = row.get("MA15")

        if (
            ma15 is not None
            and row["close"] < ma15
        ):

            return {

                "exit_price": row["close"],

                "exit_reason": "MA15_CLOSE"

            }

        return None

    def _build_position_row(
        self,
        row: dict,
        action: str,
        trade_context: dict,
        position_open: bool,
        exit_reason=None,
        exit_price=None
    ):

        return {

            "date": row["date"],

            "close": row["close"],

            "entry_price": (
                None if trade_context is None
                else round(trade_context["entry_price"], 2)
            ),

            "stop_loss": (
                None if trade_context is None
                else round(trade_context["stop_loss"], 2)
            ),

            "exit_price": (
                None if exit_price is None
                else round(exit_price, 2)
            ),

            "signal": row["signal"],

            "action": action,

            "position": "LONG" if position_open else "NONE",

            "exit_reason": exit_reason

        }

    def _build_trade_record(
        self,
        position: dict,
        exit_row: dict,
        exit_price: float,
        exit_reason: str
    ):

        profit_points = exit_price - position["entry_price"]

        profit_percent = (
            profit_points
            / position["entry_price"]
        ) * 100

        holding_days = (
            exit_row["date"]
            - position["entry_date"]
        ).days

        return {

            "entry_date": position["entry_date"],

            "exit_date": exit_row["date"],

            "entry_price": round(
                position["entry_price"],
                2
            ),

            "exit_price": round(
                exit_price,
                2
            ),

            "stop_loss": round(
                position["stop_loss"],
                2
            ),

            "holding_days": holding_days,

            "profit_points": round(
                profit_points,
                2
            ),

            "profit_percent": round(
                profit_percent,
                2
            ),

            "exit_reason": exit_reason,

            "profit": round(
                profit_points,
                2
            )

        }

    def _process_signals(
        self,
        signals: list
    ):

        position = None

        positions = []

        trades = []

        for row in signals:

            action = "HOLD"
            exit_reason = None
            exit_price = None
            row_position = position

            if position is None:

                if row["signal"] == "BUY":

                    position = self._open_position(
                        row
                    )

                    action = "BUY"

                    row_position = position

                positions.append(
                    self._build_position_row(
                        row,
                        action,
                        row_position,
                        position is not None
                    )
                )

                continue

            exit_details = self._resolve_exit(
                row,
                position
            )

            if exit_details is not None:

                action = "SELL"

                exit_reason = exit_details[
                    "exit_reason"
                ]

                exit_price = exit_details[
                    "exit_price"
                ]

                trades.append(
                    self._build_trade_record(
                        position,
                        row,
                        exit_price,
                        exit_reason
                    )
                )

                row_position = position

                position = None

            positions.append(
                self._build_position_row(
                    row,
                    action,
                    row_position,
                    position is not None,
                    exit_reason,
                    exit_price
                )
            )

        return positions, trades

    def simulate_positions(
        self,
        db: Session,
        symbol: str
    ):

        signals = self.load_signals(
            db,
            symbol
        )

        positions, _ = self._process_signals(
            signals
        )

        return positions
    
    def execute_trades(
        self,
        db: Session,
        symbol: str
    ):

        signals = self.load_signals(
            db,
            symbol
        )

        _, trades = self._process_signals(
            signals
        )

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

            trade["profit_points"]

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
