
import logging
import time
from collections import defaultdict

from sqlalchemy.orm import Session

from app.backtesting.exits.strategy_factory import ExitStrategyFactory
from app.config.backtest_config import BacktestConfig
from app.services.trade_selection_service import TradeSelectionService
from app.strategy.strategy_factory import StrategyFactory


logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Core backtesting engine.

    Initializes the configured trading strategy, trade selection service,
    exit strategy, capital allocation, and risk parameters.
    """

    def __init__(
        self,
        config: BacktestConfig
    ):
        started_at = time.perf_counter()

        logger.info(
            "Backtest engine initialization started",
            extra={
                "event": "backtest_engine_initialization_started"
            }
        )

        try:
            if config is None:
                raise ValueError("Backtest configuration cannot be None.")

            self.config = config

            # Initialize the strategy factory and configured entry strategy.
            self.factory = StrategyFactory()

            self.strategy = self.factory.create(
                self.config.strategy.strategy_name,
                self.config
            )

            # Initialize trade selection service.
            self.trade_selection = TradeSelectionService()

            # Initialize the configured exit strategy.
            self.exit_strategy = ExitStrategyFactory.create(
                self.config.exit_strategy
            )

            # Initialize capital and risk allocation.
            self.initial_capital = float(
                self.config.initial_capital
            )

            self.risk_percent = 1.0

            if self.initial_capital <= 0:
                raise ValueError(
                    "Initial capital must be greater than zero."
                )

            self.risk_amount = (
                self.initial_capital * self.risk_percent
            ) / 100

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Backtest engine initialized successfully",
                extra={
                    "event": "backtest_engine_initialization_completed",
                    "strategy_name": self.config.strategy.strategy_name,
                    "exit_strategy": str(self.config.exit_strategy),
                    "initial_capital": self.initial_capital,
                    "risk_percent": self.risk_percent,
                    "risk_amount": round(self.risk_amount, 2),
                    "duration_ms": duration_ms
                }
            )

        except Exception:
            logger.exception(
                "Backtest engine initialization failed",
                extra={
                    "event": "backtest_engine_initialization_failed",
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise


    def load_signals(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):
        """
        Generate trading signals, build trade candidates,
        rank candidates, and enrich BUY signals with candidate data.
        """
        started_at = time.perf_counter()

        logger.info(
            "Signal loading started",
            extra={
                "event": "backtest_signal_loading_started",
                "symbol": symbol,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None
            }
        )

        try:
            signals = self.strategy.generate_signals(
                db,
                symbol,
                start_date,
                end_date
            )

            signal_count = len(signals)

            candidates = self.trade_selection.build_candidates(
                db=db,
                symbol=symbol,
                signals=signals
            )

            candidate_count = len(candidates)

            candidates = self.trade_selection.rank_candidates(
                candidates
            )

            ranked_count = len(candidates)

            # Map ranked candidates to their corresponding signal dates.
            buy_map = {
                candidate.signal_date: candidate
                for candidate in candidates
            }

            enriched_count = 0

            for signal in signals:

                # Attach the symbol for downstream trade identification.
                signal.setdefault("symbol", symbol)

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

                enriched_count += 1

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Signal loading completed",
                extra={
                    "event": "backtest_signal_loading_completed",
                    "symbol": symbol,
                    "signal_count": signal_count,
                    "candidate_count": candidate_count,
                    "ranked_candidate_count": ranked_count,
                    "enriched_buy_signal_count": enriched_count,
                    "duration_ms": duration_ms
                }
            )

            return signals

        except Exception:
            logger.exception(
                "Signal loading failed",
                extra={
                    "event": "backtest_signal_loading_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def _open_position(
        self,
        row: dict
    ):
        """
        Open a new long position using the configured risk amount.

        Calculates position quantity based on entry-to-stop-loss risk
        and establishes the 2R and 3R profit targets.
        """
        symbol = row.get("symbol", "UNKNOWN")

        try:
            entry_price = float(row["entry_price"])
            stop_loss = float(row["stop_loss"])

            risk_per_share = entry_price - stop_loss

            if risk_per_share <= 0:
                logger.warning(
                    "Position rejected due to invalid risk",
                    extra={
                        "event": "backtest_position_rejected",
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "risk_per_share": risk_per_share,
                        "reason": "invalid_risk_per_share"
                    }
                )
                return None

            target_2r = entry_price + (2 * risk_per_share)
            target_3r = entry_price + (3 * risk_per_share)

            quantity = int(
                self.risk_amount / risk_per_share
            )

            if quantity < 1:
                logger.warning(
                    "Position rejected because calculated quantity is below one",
                    extra={
                        "event": "backtest_position_rejected",
                        "symbol": symbol,
                        "risk_per_share": round(risk_per_share, 2),
                        "risk_amount": round(self.risk_amount, 2),
                        "reason": "insufficient_risk_budget"
                    }
                )
                return None

            capital_used = quantity * entry_price

            position = {
                "symbol": symbol,

                "entry_date": row["date"],
                "entry_price": entry_price,
                "stop_loss": stop_loss,

                "risk_per_share": round(risk_per_share, 2),

                "quantity": quantity,
                "remaining_quantity": quantity,

                "capital_used": round(capital_used, 2),

                "target_2r": round(target_2r, 2),
                "target_3r": round(target_3r, 2),

                "partial_exit_2r": False,
                "partial_exit_3r": False,

                "realized_profit": 0.0,

                "events": [],

                "trail_active": False
            }

            logger.info(
                "Backtest position opened",
                extra={
                    "event": "backtest_position_opened",
                    "symbol": symbol,
                    "entry_date": str(row["date"]),
                    "entry_price": round(entry_price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "risk_per_share": round(risk_per_share, 2),
                    "quantity": quantity,
                    "capital_used": round(capital_used, 2),
                    "target_2r": round(target_2r, 2),
                    "target_3r": round(target_3r, 2)
                }
            )

            return position

        except Exception:
            logger.exception(
                "Failed to open backtest position",
                extra={
                    "event": "backtest_position_open_failed",
                    "symbol": symbol
                }
            )
            raise

    def _build_position_row(
        self,
        row: dict,
        action: str,
        trade_context: dict,
        position_open: bool,
        exit_reason=None,
        exit_price=None
    ):
        """
        Build a daily position snapshot for backtest reporting.

        Captures entry details, risk information, targets,
        remaining quantity, and exit information.
        """

        return {
            "symbol": row.get("symbol"),

            "date": row["date"],
            "close": row["close"],

            "entry_price": (
                None
                if trade_context is None
                else round(trade_context["entry_price"], 2)
            ),

            "stop_loss": (
                None
                if trade_context is None
                else round(trade_context["stop_loss"], 2)
            ),

            "exit_price": (
                None
                if exit_price is None
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
        exit_reason: str
    ):
        """
        Build the completed trade record.

        Calculates average exit price, realized profit, return percentage,
        holding period, and trade execution details.
        """
        quantity = position["quantity"]
        capital_used = position["capital_used"]

        if quantity <= 0:
            raise ValueError("Position quantity must be greater than zero.")

        if capital_used <= 0:
            raise ValueError("Position capital used must be greater than zero.")

        if position["remaining_quantity"] != 0:
            raise ValueError(
                "Cannot build a completed trade with remaining quantity."
            )

        realized_profit = position["realized_profit"]

        # Derive the weighted average exit price from total realized P&L.
        average_exit_price = (
            position["entry_price"]
            + (realized_profit / quantity)
        )

        profit_points = (
            average_exit_price - position["entry_price"]
        )

        profit_percent = (
            realized_profit / capital_used
        ) * 100

        holding_days = (
            exit_row["date"] - position["entry_date"]
        ).days

        return {
            "symbol": position.get("symbol"),

            "entry_date": position["entry_date"],
            "exit_date": exit_row["date"],

            "entry_price": round(
                position["entry_price"], 2
            ),

            "exit_price": round(
                average_exit_price, 2
            ),

            "stop_loss": round(
                position["stop_loss"], 2
            ),

            "holding_days": holding_days,

            "profit_points": round(
                profit_points, 2
            ),

            "profit_percent": round(
                profit_percent, 2
            ),

            "exit_reason": exit_reason,

            "quantity": quantity,

            "capital_used": round(
                capital_used, 2
            ),

            "risk_per_share": position["risk_per_share"],

            "profit": round(
                realized_profit, 2
            ),

            "target_2r": position["target_2r"],
            "target_3r": position["target_3r"],

            "sold_quantity": (
                quantity - position["remaining_quantity"]
            ),

            "remaining_quantity": 0,

            "partial_exit_2r": position["partial_exit_2r"],
            "partial_exit_3r": position["partial_exit_3r"],

            "events": list(position["events"])
        }

    def _process_signals(
        self,
        signals: list
    ):
        """
        Process trading signals and manage open positions.

        Supports:
        - BUY signal execution
        - Initial stop-loss execution
        - Partial exits
        - Full exits
        - Trailing-stop strategies
        - Completed trade generation

        Returns:
            tuple: (position_history, completed_trades)
        """
        started_at = time.perf_counter()

        position = None

        positions = []
        trades = []

        buy_count = 0
        partial_exit_count = 0
        stop_loss_count = 0

        logger.info(
            "Backtest signal processing started",
            extra={
                "event": "backtest_signal_processing_started",
                "signal_count": len(signals)
            }
        )

        try:
            for row in signals:

                action = "HOLD"
                exit_reason = None
                exit_price = None

                row_position = position

                # --------------------------------------------------
                # Open a new position
                # --------------------------------------------------

                if position is None:

                    if row["signal"] == "BUY":

                        position = self._open_position(row)

                        if position is None:

                            positions.append(
                                self._build_position_row(
                                    row,
                                    "HOLD",
                                    None,
                                    False
                                )
                            )

                            continue

                        position["events"].append({
                            "type": "BUY",
                            "date": row["date"],
                            "price": position["entry_price"],
                            "quantity": position["quantity"]
                        })

                        buy_count += 1

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

                # --------------------------------------------------
                # Initial stop-loss handling
                # --------------------------------------------------

                # Some trailing strategies move stop_loss to the 2R level.
                # Do not let the generic initial stop-loss handler intercept
                # those exits before the configured exit strategy processes them.
                trailing_stop_active = (
                    position.get("trail_active", False)
                    or (
                        position.get("partial_exit_2r", False)
                        and position["stop_loss"] >= position["target_2r"]
                    )
                )

                if (
                    not trailing_stop_active
                    and row["low"] <= position["stop_loss"]
                ):

                    stop_price = position["stop_loss"]

                    sell_quantity = position["remaining_quantity"]

                    final_profit = (
                        stop_price - position["entry_price"]
                    ) * sell_quantity

                    position["realized_profit"] += final_profit

                    position["events"].append({
                        "type": "STOP_LOSS",
                        "date": row["date"],
                        "price": stop_price,
                        "quantity": sell_quantity,
                        "profit": round(final_profit, 2)
                    })

                    position["remaining_quantity"] = 0

                    trade = self._build_trade_record(
                        position,
                        row,
                        "STOP_LOSS"
                    )

                    trades.append(trade)

                    stop_loss_count += 1

                    logger.info(
                        "Backtest stop loss executed",
                        extra={
                            "event": "backtest_stop_loss_executed",
                            "symbol": position.get("symbol"),
                            "date": str(row["date"]),
                            "exit_price": round(stop_price, 2),
                            "quantity": sell_quantity,
                            "profit": round(final_profit, 2)
                        }
                    )

                    exit_reason = "STOP_LOSS"
                    exit_price = stop_price
                    action = "SELL"

                    row_position = position
                    position = None

                    positions.append(
                        self._build_position_row(
                            row,
                            action,
                            row_position,
                            False,
                            exit_reason,
                            exit_price
                        )
                    )

                    continue

                # --------------------------------------------------
                # Configured exit strategy
                # --------------------------------------------------

                result = self.exit_strategy.process(
                    position,
                    row
                )

                if result is not None:

                    close_position = result["close_position"]

                    exit_reason = result["exit_reason"]
                    exit_price = float(result["exit_price"])

                    remaining_quantity = position["remaining_quantity"]

                    sell_quantity = int(
                        result.get(
                            "sell_quantity",
                            remaining_quantity
                        )
                    )

                    # Validate the exit quantity before changing the position.
                    if sell_quantity <= 0:
                        raise ValueError(
                            "Exit quantity must be greater than zero."
                        )

                    if sell_quantity > remaining_quantity:
                        raise ValueError(
                            "Exit quantity exceeds remaining position quantity."
                        )

                    if close_position and sell_quantity != remaining_quantity:
                        raise ValueError(
                            "Full exit quantity must equal remaining position quantity."
                        )

                    if not close_position and sell_quantity >= remaining_quantity:
                        raise ValueError(
                            "Partial exit must leave a positive remaining quantity."
                        )

                    realized_profit = (
                        exit_price - position["entry_price"]
                    ) * sell_quantity

                    position["realized_profit"] += realized_profit

                    position["remaining_quantity"] -= sell_quantity

                    # --------------------------------------------------
                    # Partial exit
                    # --------------------------------------------------

                    if not close_position:

                        action = "PARTIAL_SELL"

                        partial_exit_count += 1

                        position["events"].append({
                            "type": exit_reason,
                            "date": row["date"],
                            "price": exit_price,
                            "quantity": sell_quantity,
                            "profit": round(realized_profit, 2)
                        })

                        row_position = position

                        logger.info(
                            "Backtest partial exit executed",
                            extra={
                                "event": "backtest_partial_exit_executed",
                                "symbol": position.get("symbol"),
                                "date": str(row["date"]),
                                "exit_reason": exit_reason,
                                "exit_price": round(exit_price, 2),
                                "sold_quantity": sell_quantity,
                                "remaining_quantity": position["remaining_quantity"],
                                "profit": round(realized_profit, 2)
                            }
                        )

                    # --------------------------------------------------
                    # Full exit
                    # --------------------------------------------------

                    else:

                        action = "SELL"

                        position["events"].append({
                            "type": exit_reason,
                            "date": row["date"],
                            "price": exit_price,
                            "quantity": sell_quantity,
                            "profit": round(realized_profit, 2)
                        })

                        position["remaining_quantity"] = 0

                        trade = self._build_trade_record(
                            position,
                            row,
                            exit_reason
                        )

                        trades.append(trade)

                        row_position = position

                        logger.info(
                            "Backtest position closed",
                            extra={
                                "event": "backtest_position_closed",
                                "symbol": position.get("symbol"),
                                "date": str(row["date"]),
                                "exit_reason": exit_reason,
                                "exit_price": round(exit_price, 2),
                                "quantity": sell_quantity,
                                "total_profit": trade["profit"],
                                "profit_percent": trade["profit_percent"],
                                "holding_days": trade["holding_days"]
                            }
                        )

                        position = None

                # --------------------------------------------------
                # Record daily position snapshot
                # --------------------------------------------------

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

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Backtest signal processing completed",
                extra={
                    "event": "backtest_signal_processing_completed",
                    "signal_count": len(signals),
                    "buy_count": buy_count,
                    "partial_exit_count": partial_exit_count,
                    "stop_loss_count": stop_loss_count,
                    "completed_trade_count": len(trades),
                    "open_position": position is not None,
                    "duration_ms": duration_ms
                }
            )

            return positions, trades

        except Exception:
            logger.exception(
                "Backtest signal processing failed",
                extra={
                    "event": "backtest_signal_processing_failed",
                    "signal_count": len(signals),
                    "completed_trade_count": len(trades),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def simulate_positions(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):
        """
        Generate and simulate positions for a given symbol.

        Returns daily position history, including entry, partial exit,
        stop-loss, and final exit information.
        """
        started_at = time.perf_counter()

        logger.info(
            "Position simulation started",
            extra={
                "event": "backtest_position_simulation_started",
                "symbol": symbol,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None
            }
        )

        try:
            signals = self.load_signals(
                db,
                symbol,
                start_date,
                end_date
            )

            positions, trades = self._process_signals(
                signals
            )

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Position simulation completed",
                extra={
                    "event": "backtest_position_simulation_completed",
                    "symbol": symbol,
                    "signal_count": len(signals),
                    "position_row_count": len(positions),
                    "completed_trade_count": len(trades),
                    "duration_ms": duration_ms
                }
            )

            return positions

        except Exception:
            logger.exception(
                "Position simulation failed",
                extra={
                    "event": "backtest_position_simulation_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def execute_trades(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):
        """
        Execute a backtest for a symbol and enrich completed trades
        with their corresponding entry signal metrics.
        """
        started_at = time.perf_counter()

        logger.info(
            "Trade execution started",
            extra={
                "event": "backtest_trade_execution_started",
                "symbol": symbol,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None
            }
        )

        try:
            signals = self.load_signals(
                db,
                symbol,
                start_date,
                end_date
            )

            if not signals:
                logger.info(
                    "No signals available for trade execution",
                    extra={
                        "event": "backtest_trade_execution_no_signals",
                        "symbol": symbol,
                        "duration_ms": round(
                            (time.perf_counter() - started_at) * 1000,
                            2
                        )
                    }
                )
                return []

            _, trades = self._process_signals(signals)

            # Map BUY signals to their entry dates for trade enrichment.
            buy_signals = {
                signal["date"]: signal
                for signal in signals
                if signal["signal"] == "BUY"
            }

            enriched_count = 0

            for trade in trades:

                # Attach symbol to the trade record.
                trade["symbol"] = symbol

                signal = buy_signals.get(trade["entry_date"])

                if signal is None:
                    logger.warning(
                        "Entry signal not found for completed trade",
                        extra={
                            "event": "backtest_trade_signal_not_found",
                            "symbol": symbol,
                            "entry_date": str(trade["entry_date"])
                        }
                    )
                    continue

                volume = signal.get("volume") or 0
                volume20 = signal.get("volume20") or 0

                volume_ratio = (
                    volume / volume20
                    if volume20 > 0
                    else 0
                )

                # Attach ranking and technical metrics.
                trade["market_score"] = signal.get("market_score", 0)
                trade["sector_score"] = signal.get("sector_score", 0)
                trade["total_score"] = signal.get("total_score", 0)

                trade["position_size"] = signal.get("position_size", 0)
                trade["risk_amount"] = signal.get("risk_amount", 0)

                trade["volume_ratio"] = volume_ratio
                trade["distance_from_ma"] = signal.get("distance_from_ma", 0)
                trade["body_percent"] = signal.get("body_percent", 0)

                trade["quality_pass"] = signal.get("quality_pass", False)
                trade["volume_confirmation"] = signal.get(
                    "volume_confirmation",
                    False
                )

                trade["atr"] = signal.get("atr")
                trade["atr_percent"] = signal.get("atr_percent")

                trade["ma15_slope"] = signal.get("ma15_slope")
                trade["ma30_slope"] = signal.get("ma30_slope")
                trade["ma150_slope"] = signal.get("ma150_slope")

                trade["distance_from_15ma"] = signal.get(
                    "distance_from_15ma"
                )
                trade["distance_from_30ma"] = signal.get(
                    "distance_from_30ma"
                )
                trade["distance_from_150ma"] = signal.get(
                    "distance_from_150ma"
                )

                trade["ma15_30_gap"] = signal.get("ma15_30_gap")
                trade["ma30_150_gap"] = signal.get("ma30_150_gap")

                enriched_count += 1

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Trade execution completed",
                extra={
                    "event": "backtest_trade_execution_completed",
                    "symbol": symbol,
                    "signal_count": len(signals),
                    "completed_trade_count": len(trades),
                    "enriched_trade_count": enriched_count,
                    "duration_ms": duration_ms
                }
            )

            return trades

        except Exception:
            logger.exception(
                "Trade execution failed",
                extra={
                    "event": "backtest_trade_execution_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def execute_portfolio(
        self,
        db: Session,
        symbols: list,
        start_date=None,
        end_date=None
    ):
        """
        Execute backtests across multiple symbols.

        Collects completed trades and groups them by entry date.
        """
        started_at = time.perf_counter()

        logger.info(
            "Portfolio backtest started",
            extra={
                "event": "backtest_portfolio_execution_started",
                "symbol_count": len(symbols),
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None
            }
        )

        try:
            portfolio_trades = []

            successful_symbols = 0
            failed_symbols = []

            for symbol in symbols:

                try:
                    trades = self.execute_trades(
                        db,
                        symbol,
                        start_date,
                        end_date
                    )

                    portfolio_trades.extend(trades)
                    successful_symbols += 1

                except Exception:
                    failed_symbols.append(symbol)

                    logger.exception(
                        "Symbol backtest failed during portfolio execution",
                        extra={
                            "event": "backtest_portfolio_symbol_failed",
                            "symbol": symbol
                        }
                    )

                    # Do not silently return an incomplete portfolio.
                    raise

            # Sort completed trades chronologically.
            portfolio_trades.sort(
                key=lambda trade: trade["entry_date"]
            )

            # Group trades by entry date.
            daily_trades = defaultdict(list)

            for trade in portfolio_trades:
                daily_trades[trade["entry_date"]].append(trade)

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Portfolio backtest completed",
                extra={
                    "event": "backtest_portfolio_execution_completed",
                    "symbol_count": len(symbols),
                    "successful_symbol_count": successful_symbols,
                    "failed_symbols": failed_symbols,
                    "total_trade_count": len(portfolio_trades),
                    "trading_days": len(daily_trades),
                    "duration_ms": duration_ms
                }
            )

            return daily_trades

        except Exception:
            logger.exception(
                "Portfolio backtest failed",
                extra={
                    "event": "backtest_portfolio_execution_failed",
                    "symbol_count": len(symbols),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def performance_metrics(
        self,
        db: Session,
        symbol: str
    ):
        """
        Calculate performance metrics for completed trades of a symbol.

        Calculates total trades, winning and losing trades, win rate,
        net profit, average profit, best trade, and worst trade.
        """
        started_at = time.perf_counter()

        logger.info(
            "Performance metrics calculation started",
            extra={
                "event": "backtest_performance_metrics_started",
                "symbol": symbol
            }
        )

        try:
            trades = self.execute_trades(
                db,
                symbol
            )

            total_trades = len(trades)

            if total_trades == 0:

                result = {
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

            else:
                profits = [
                    trade["profit"]
                    for trade in trades
                ]

                winning = [
                    profit
                    for profit in profits
                    if profit > 0
                ]

                losing = [
                    profit
                    for profit in profits
                    if profit <= 0
                ]

                result = {
                    "symbol": symbol,

                    "total_trades": total_trades,

                    "winning_trades": len(winning),

                    "losing_trades": len(losing),

                    "win_rate": round(
                        len(winning) / total_trades * 100,
                        2
                    ),

                    "net_profit": round(
                        sum(profits),
                        2
                    ),

                    "average_profit": round(
                        sum(profits) / total_trades,
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

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2
            )

            logger.info(
                "Performance metrics calculation completed",
                extra={
                    "event": "backtest_performance_metrics_completed",
                    "symbol": symbol,
                    "total_trades": result["total_trades"],
                    "winning_trades": result["winning_trades"],
                    "losing_trades": result["losing_trades"],
                    "win_rate": result["win_rate"],
                    "net_profit": result["net_profit"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Performance metrics calculation failed",
                extra={
                    "event": "backtest_performance_metrics_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise
    
    def portfolio_metrics(
        self,
        db: Session,
        symbols: list,
        start_date=None,
        end_date=None
    ):
        """
        Calculate combined performance metrics across multiple symbols.

        Flattens the daily grouped portfolio trades and calculates
        win rate, net profit, average profit, best trade, and worst trade.
        """
        started_at = time.perf_counter()

        logger.info(
            "Portfolio metrics calculation started",
            extra={
                "event": "backtest_portfolio_metrics_started",
                "symbol_count": len(symbols)
            }
        )

        try:
            daily_trades = self.execute_portfolio(
                db,
                symbols,
                start_date,
                end_date
            )

            # execute_portfolio returns trades grouped by entry date.
            trades = [
                trade
                for daily_group in daily_trades.values()
                for trade in daily_group
            ]

            total_trades = len(trades)

            if total_trades == 0:
                result = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "net_profit": 0,
                    "average_profit": 0,
                    "best_trade": 0,
                    "worst_trade": 0
                }

            else:
                profits = [
                    trade["profit"]
                    for trade in trades
                ]

                winners = [
                    profit for profit in profits
                    if profit > 0
                ]

                losers = [
                    profit for profit in profits
                    if profit <= 0
                ]

                result = {
                    "total_trades": total_trades,

                    "winning_trades": len(winners),

                    "losing_trades": len(losers),

                    "win_rate": round(
                        len(winners) / total_trades * 100,
                        2
                    ),

                    "net_profit": round(
                        sum(profits),
                        2
                    ),

                    "average_profit": round(
                        sum(profits) / total_trades,
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

            logger.info(
                "Portfolio metrics calculation completed",
                extra={
                    "event": "backtest_portfolio_metrics_completed",
                    "symbol_count": len(symbols),
                    "total_trades": result["total_trades"],
                    "winning_trades": result["winning_trades"],
                    "losing_trades": result["losing_trades"],
                    "win_rate": result["win_rate"],
                    "net_profit": result["net_profit"],
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Portfolio metrics calculation failed",
                extra={
                    "event": "backtest_portfolio_metrics_failed",
                    "symbol_count": len(symbols),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def equity_curve(
        self,
        db: Session,
        symbol: str,
        initial_capital: float = 10000000
    ):
        """
        Calculate the equity curve using completed trade profits.

        Trades are processed chronologically by exit date.
        """
        started_at = time.perf_counter()

        logger.info(
            "Equity curve calculation started",
            extra={
                "event": "backtest_equity_curve_started",
                "symbol": symbol,
                "initial_capital": initial_capital
            }
        )

        try:
            if initial_capital <= 0:
                raise ValueError(
                    "Initial capital must be greater than zero."
                )

            trades = self.execute_trades(
                db,
                symbol
            )

            # Process realized profits in chronological exit order.
            trades = sorted(
                trades,
                key=lambda trade: trade["exit_date"]
            )

            capital = initial_capital
            curve = []

            for trade in trades:

                profit = trade["profit"]

                capital += profit

                curve.append({
                    "exit_date": trade["exit_date"],
                    "capital": round(capital, 2),
                    "profit": round(profit, 2)
                })

            result = {
                "symbol": symbol,

                "initial_capital": round(initial_capital, 2),

                "final_capital": round(capital, 2),

                "equity_curve": curve
            }

            logger.info(
                "Equity curve calculation completed",
                extra={
                    "event": "backtest_equity_curve_completed",
                    "symbol": symbol,
                    "completed_trade_count": len(trades),
                    "initial_capital": round(initial_capital, 2),
                    "final_capital": round(capital, 2),
                    "net_profit": round(capital - initial_capital, 2),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Equity curve calculation failed",
                extra={
                    "event": "backtest_equity_curve_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise

    def drawdown_metrics(
        self,
        db: Session,
        symbol: str
    ):
        """
        Calculate maximum and current drawdown from the equity curve.

        Includes initial capital when identifying the running equity peak.
        """
        started_at = time.perf_counter()

        logger.info(
            "Drawdown calculation started",
            extra={
                "event": "backtest_drawdown_calculation_started",
                "symbol": symbol
            }
        )

        try:
            equity = self.equity_curve(
                db,
                symbol
            )

            curve = equity["equity_curve"]

            initial_capital = equity["initial_capital"]

            # Start with initial capital as the first equity peak.
            peak = initial_capital

            max_drawdown = 0.0
            current_drawdown = 0.0

            for point in curve:

                capital = point["capital"]

                peak = max(peak, capital)

                drawdown = (
                    (peak - capital) / peak
                ) * 100

                max_drawdown = max(
                    max_drawdown,
                    drawdown
                )

                current_drawdown = drawdown

            result = {
                "symbol": symbol,

                "peak_capital": round(peak, 2),

                "max_drawdown": round(max_drawdown, 2),

                "current_drawdown": round(current_drawdown, 2)
            }

            logger.info(
                "Drawdown calculation completed",
                extra={
                    "event": "backtest_drawdown_calculation_completed",
                    "symbol": symbol,
                    "peak_capital": result["peak_capital"],
                    "max_drawdown": result["max_drawdown"],
                    "current_drawdown": result["current_drawdown"],
                    "equity_point_count": len(curve),
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Drawdown calculation failed",
                extra={
                    "event": "backtest_drawdown_calculation_failed",
                    "symbol": symbol,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        2
                    )
                }
            )
            raise