from unittest import signals

from sqlalchemy.orm import Session

from app.strategies.moving_average import MovingAverageStrategy
from app.config.backtest_config import BacktestConfig
from app.strategies.strategy_factory import StrategyFactory
from collections import defaultdict
from app.services.trade_selection_service import TradeSelectionService


class BacktestEngine:

    def __init__(
        self,
        config: BacktestConfig
    ):

        self.config = config

        self.factory = StrategyFactory()

        self.trade_selection = TradeSelectionService()
        
        self.strategy = self.factory.create_strategy(
            self.config.strategy.strategy_name,
            self.config
        )

        self.initial_capital = self.config.initial_capital

        self.risk_percent = 1

        self.risk_amount = (

            self.initial_capital

            * self.risk_percent

        ) / 100

    def load_signals(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):

        signals = self.strategy.generate_signals(
            db,
            symbol,
            start_date,
            end_date
        )

        candidates = self.trade_selection.build_candidates(
            db=db,
            symbol=symbol,
            signals=signals
        )

        candidates = self.trade_selection.ranking.rank_candidates(
            candidates
        )

        #
        # Convert TradeCandidate back to dictionary so the
        # existing backtest engine doesn't need to change.
        #

        buy_map = {
            c.signal_date: c
            for c in candidates
        }

        for signal in signals:

            if signal["signal"] != "BUY":
                continue

            candidate = buy_map.get(signal["date"])

            if candidate is None:
                continue

            signal["market_score"] = candidate.market_score
            signal["sector_score"] = candidate.sector_score
            signal["quantity"] = candidate.quantity
            signal["capital_required"] = candidate.capital_required
            signal["total_score"] = candidate.total_score

        return signals

    def _open_position(
        self,
        row: dict
    ):

        risk_per_share = (

            row["entry_price"]

            - row["stop_loss"]

        )

        target_2r = (
            row["entry_price"]
            + (2 * risk_per_share)
        )

        target_3r = (
            row["entry_price"]
            + (3 * risk_per_share)
        )

        quantity = (

            self.risk_amount

            / risk_per_share

        )

        capital_used = (

            quantity

            * row["entry_price"]

        )

        return {

            "entry_date": row["date"],

            "entry_price": row["entry_price"],

            "stop_loss": row["stop_loss"],

            "risk_per_share": round(

                risk_per_share,

                2

            ),

            "quantity": int(quantity),

            "capital_used": round(

                capital_used,

                2

            ),

            "target_2r": round(target_2r, 2),
            "target_3r": round(target_3r, 2),
            "remaining_quantity": int(quantity),

            "partial_exit_2r": False,

            "partial_exit_3r": False,

            "realized_profit": 0.0,

            "events": []

        }

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

            "exit_reason": exit_reason,
            "quantity": (

                None

                if trade_context is None

                else trade_context["quantity"]

            ),

            "risk_per_share": (

                None

                if trade_context is None

                else trade_context["risk_per_share"]

            ),

            "capital_used": (

                None

                if trade_context is None

                else trade_context["capital_used"]

            ),
            "target_2r": (
                None
                if trade_context is None
                else trade_context["target_2r"]
            ),

            "target_3r": (
                None
                if trade_context is None
                else trade_context["target_3r"]
            ),
            "remaining_quantity": (

                None

                if trade_context is None

                else trade_context["remaining_quantity"]

            ),

            "partial_exit_2r": (

                None

                if trade_context is None

                else trade_context["partial_exit_2r"]

            ),

            "partial_exit_3r": (

                None

                if trade_context is None

                else trade_context["partial_exit_3r"]

            )

        }

    def _build_trade_record(
        self,
        position: dict,
        exit_row: dict,
        exit_price: float,
        exit_reason: str
    ):

        profit_points = exit_price - position["entry_price"]

        profit = position["realized_profit"]

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

            "quantity": position["quantity"],

            "capital_used": position["capital_used"],

            "risk_per_share": position["risk_per_share"],

            "profit": round(

                profit,

                2

            ),
            "target_2r": position["target_2r"],

            "target_3r": position["target_3r"],
            "sold_quantity": (

                position["quantity"]

                - position["remaining_quantity"]

            ),

            "remaining_quantity": 0,

            "partial_exit_2r": position["partial_exit_2r"],

            "partial_exit_3r": position["partial_exit_3r"],

            "events": position["events"]

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

                    position["events"].append({

                        "type": "BUY",

                        "date": row["date"],

                        "price": position["entry_price"],

                        "quantity": position["quantity"]

                    })

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
            if row["signal"] == "PARTIAL_EXIT":

                action = "PARTIAL_EXIT"

                if not position["partial_exit_2r"]:

                    sell_quantity = position["remaining_quantity"] // 2

                    position["partial_exit_2r"] = True

                elif not position["partial_exit_3r"]:

                    sell_quantity = position["remaining_quantity"] // 2

                    position["partial_exit_3r"] = True

                else:

                    sell_quantity = 0

                partial_profit = (

                    row["exit_price"]

                    - position["entry_price"]

                ) * sell_quantity

                position["remaining_quantity"] -= sell_quantity

                position["realized_profit"] += partial_profit

                position["events"].append({

                    "type": row["exit_reason"],

                    "date": row["date"],

                    "price": row["exit_price"],

                    "quantity": sell_quantity,

                    "profit": round(partial_profit, 2)

                })

                row_position = position

            elif row["signal"] == "SELL":

                action = "SELL"

                exit_reason = row["exit_reason"]

                exit_price = row["exit_price"]

                #
                # Sell remaining quantity
                #

                remaining_profit = (

                    row["exit_price"]

                    - position["entry_price"]

                ) * position["remaining_quantity"]

                position["realized_profit"] += remaining_profit

                position["remaining_quantity"] = 0

                position["events"].append({

                    "type": "SELL",

                    "date": row["date"],

                    "price": row["exit_price"],

                    "quantity": position["remaining_quantity"],

                    "profit": round(remaining_profit, 2)

                })

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
        db,
        symbol,
        start_date=None,
        end_date=None
    ):

        signals = self.load_signals(
            db,
            symbol,
            start_date,
            end_date
        )

        positions, _ = self._process_signals(
            signals
        )

        return positions
    
    def execute_trades(
        self,
        db,
        symbol,
        start_date=None,
        end_date=None
    ):

        signals = self.load_signals(
            db,
            symbol,
            start_date,
            end_date
        )

        print("=" * 60)
        print(symbol)
        print("Signals:", len(signals))
        print("Start:", start_date)
        print("End:", end_date)

        if len(signals) == 0:
            return []

        _, trades = self._process_signals(signals)

        #
        # Attach ranking metrics to each completed trade
        #
        buy_signals = {
            s["date"]: s
            for s in signals
            if s["signal"] == "BUY"
        }

        for trade in trades:

            signal = buy_signals.get(trade["entry_date"])

            if signal is None:
                continue

            volume_ratio = (
                signal["volume"] / signal["volume20"]
                if signal.get("volume20")
                else 0
            )

            distance_from_ma = signal.get(
                "distance_from_ma",
                0
            )

            body_percent = signal.get(
                "body_percent",
                0
            )

            quality_pass = signal.get(
                "quality_pass",
                False
            )

            volume_confirmation = signal.get(
                "volume_confirmation",
                False
            )

            trade["market_score"] = signal.get("market_score", 0)
            trade["sector_score"] = signal.get("sector_score", 0)

            trade["total_score"] = signal.get("total_score", 0)

            trade["position_size"] = signal.get("position_size", 0)
            trade["risk_amount"] = signal.get("risk_amount", 0)

            trade["volume_ratio"] = volume_ratio
            trade["distance_from_ma"] = distance_from_ma
            trade["body_percent"] = body_percent
            trade["quality_pass"] = quality_pass
            trade["volume_confirmation"] = volume_confirmation

        return trades

    def execute_portfolio(
        self,
        db,
        symbols,
        start_date=None,
        end_date=None
    ):

        portfolio_trades = []

        #
        # Collect trades from all symbols
        #
        for symbol in symbols:

            trades = self.execute_trades(
                db,
                symbol,
                start_date,
                end_date
            )

            for trade in trades:
                trade["symbol"] = symbol

            portfolio_trades.extend(trades)

        #
        # Group by entry date
        #
        daily_trades = defaultdict(list)

        for trade in portfolio_trades:

            daily_trades[
                trade["entry_date"]
            ].append(trade)

        #
        # Return grouped by day
        #
        return daily_trades
    
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
    
    def portfolio_metrics(
        self,
        db: Session,
        symbols: list
    ):

        trades = self.execute_portfolio(
            db,
            symbols
        )

        if len(trades) == 0:

            return {

                "total_trades":0,

                "net_profit":0

            }

        profits = [

            trade["profit"]

            for trade in trades

        ]

        winners = [

            p

            for p in profits

            if p > 0

        ]

        losers = [

            p

            for p in profits

            if p <= 0

        ]

        return {

            "total_trades":len(trades),

            "winning_trades":len(winners),

            "losing_trades":len(losers),

            "win_rate":round(

                len(winners)

                / len(trades)

                *100,

                2

            ),

            "net_profit":round(

                sum(profits),

                2

            ),

            "average_profit":round(

                sum(profits)

                /len(trades),

                2
            ),

            "best_trade":round(

                max(profits),

                2

            ),

            "worst_trade":round(

                min(profits),

                2

            )
        }
    
    def equity_curve(
        self,
        db: Session,
        symbol: str,
        initial_capital: float = 10000000
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
