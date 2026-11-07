
import logging
import time

from app.ai.services.ai_trade_service import AITradeService
from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.market_condition_engine import MarketConditionEngine
from app.backtesting.monte_carlo_engine import MonteCarloEngine
from app.backtesting.parameter_optimizer import ParameterOptimizer
from app.backtesting.sector_engine import SectorEngine
from app.backtesting.strategy_intelligence import StrategyIntelligence
from app.backtesting.trading_cost_engine import TradingCostEngine
from app.backtesting.walk_forward_optimizer import WalkForwardOptimizer
from app.config.backtest_config import BacktestConfig
from app.config.strategy_config import StrategyConfig
from app.reports.csv_exporter import CsvExporter
from app.reports.json_exporter import JsonExporter
from app.utils.object_utils import ObjectUtils
from .trade_decision import TradeDecision
from collections import defaultdict
from sqlalchemy.orm import Session
import math


logger = logging.getLogger(__name__)


class PortfolioEngine:
    """
    Central engine responsible for initializing and coordinating
    AthenaAI portfolio backtesting components.
    """

    def __init__(self):

        start_time = time.perf_counter()

        logger.info(
            "portfolio_engine_initialization_started",
            extra={
                "event": "portfolio_engine_initialization_started"
            }
        )

        try:
            # Load backtesting configuration.
            self.config = BacktestConfig()

            # Initialize strategy configuration.
            self.strategy_config = StrategyConfig()

            # Initialize core backtesting engine.
            self.backtest_engine = BacktestEngine(
                self.config
            )

            # Initialize trading cost calculations.
            self.cost_engine = TradingCostEngine()

            # Initialize market and sector analysis engines.
            self.market_engine = MarketConditionEngine()
            self.sector_engine = SectorEngine()

            # Initialize optimization engines.
            self.optimizer = ParameterOptimizer()
            self.walk_forward_optimizer = WalkForwardOptimizer()

            # Initialize Monte Carlo simulation engine.
            self.monte_carlo_engine = MonteCarloEngine()

            # Initialize strategy intelligence.
            self.strategy_intelligence_engine = StrategyIntelligence()

            # Initialize AI trade analysis service.
            self.ai_service = AITradeService()

            # Initialize report exporters.
            self.report_exporter = CsvExporter()
            self.JsonExporter = JsonExporter()

            # Initialize object utility service.
            self.helper = ObjectUtils()

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "portfolio_engine_initialized",
                extra={
                    "event": "portfolio_engine_initialized",
                    "components_initialized": 13,
                    "duration_ms": duration_ms
                }
            )

        except Exception:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.exception(
                "portfolio_engine_initialization_failed",
                extra={
                    "event": "portfolio_engine_initialization_failed",
                    "duration_ms": duration_ms
                }
            )

            raise

    
    def load_all_trades(self, db: Session, symbols: list):
        """
        Load trades for all symbols, group them by entry date,
        and rank trades within each trading day by total score.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list.")

            logger.info(
                "portfolio_trades_loading_started",
                extra={
                    "event": "portfolio_trades_loading_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio_trades = []
            failed_symbols = []

            # Load trades for every symbol.
            for index, symbol in enumerate(symbols, start=1):

                symbol_start = time.perf_counter()

                try:
                    if not isinstance(symbol, str) or not symbol.strip():
                        raise ValueError("Invalid trading symbol.")

                    logger.info(
                        "portfolio_symbol_processing_started",
                        extra={
                            "event": "portfolio_symbol_processing_started",
                            "symbol": symbol,
                            "progress": f"{index}/{len(symbols)}"
                        }
                    )

                    trades = self.backtest_engine.execute_trades(
                        db,
                        symbol
                    )

                    if not isinstance(trades, list):
                        raise ValueError(
                            f"Invalid trade results returned for {symbol}."
                        )

                    for trade in trades:

                        if not isinstance(trade, dict):
                            raise ValueError(
                                f"Invalid trade record returned for {symbol}."
                            )

                        trade["symbol"] = symbol

                    portfolio_trades.extend(trades)

                    symbol_duration_ms = round(
                        (time.perf_counter() - symbol_start) * 1000,
                        2
                    )

                    logger.info(
                        "portfolio_symbol_processing_completed",
                        extra={
                            "event": "portfolio_symbol_processing_completed",
                            "symbol": symbol,
                            "trade_count": len(trades),
                            "duration_ms": symbol_duration_ms
                        }
                    )

                except Exception:
                    failed_symbols.append(symbol)

                    logger.exception(
                        "portfolio_symbol_processing_failed",
                        extra={
                            "event": "portfolio_symbol_processing_failed",
                            "symbol": symbol,
                            "progress": f"{index}/{len(symbols)}"
                        }
                    )

                    # Fail fast rather than silently producing an incomplete portfolio.
                    raise

            # Group trades by entry date.
            grouped = defaultdict(list)

            for trade in portfolio_trades:

                if "entry_date" not in trade:
                    raise ValueError(
                        f"Trade for {trade['symbol']} is missing entry_date."
                    )

                grouped[trade["entry_date"]].append(trade)

            ranked_trades = []

            # Rank trades independently for each trading day.
            for entry_date in sorted(grouped.keys()):

                today = grouped[entry_date]

                today.sort(
                    key=lambda trade: trade.get("total_score", 0) or 0,
                    reverse=True
                )

                ranked_trades.extend(today)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "portfolio_trades_loading_completed",
                extra={
                    "event": "portfolio_trades_loading_completed",
                    "symbol_count": len(symbols),
                    "total_trades": len(portfolio_trades),
                    "trading_days": len(grouped),
                    "ranked_trade_count": len(ranked_trades),
                    "duration_ms": duration_ms
                }
            )

            return ranked_trades

        except Exception:
            logger.exception(
                "portfolio_trades_loading_failed",
                extra={
                    "event": "portfolio_trades_loading_failed",
                    "symbol_count": (
                        len(symbols) if isinstance(symbols, list) else None
                    ),
                    "loaded_trade_count": len(portfolio_trades)
                }
            )
            raise


    def build_timeline(self, trades: list):
        """
        Build a chronological portfolio timeline containing BUY,
        2R partial SELL, and final SELL events.

        On the same date, exit events are processed before new BUY events.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be provided as a list.")

            timeline = []

            buy_count = 0
            partial_exit_count = 0
            final_exit_count = 0

            for index, trade in enumerate(trades):

                if not isinstance(trade, dict):
                    raise ValueError(
                        f"Trade at index {index} must be a dictionary."
                    )

                required_fields = [
                    "entry_date",
                    "exit_date",
                    "symbol",
                    "entry_price",
                    "exit_price",
                    "quantity"
                ]

                missing_fields = [
                    field for field in required_fields
                    if field not in trade
                ]

                if missing_fields:
                    raise ValueError(
                        f"Trade at index {index} is missing fields: "
                        f"{missing_fields}"
                    )

                symbol = trade["symbol"]
                quantity = trade["quantity"]

                if (
                    isinstance(quantity, bool)
                    or not isinstance(quantity, int)
                    or quantity <= 0
                ):
                    raise ValueError(
                        f"Trade at index {index} has invalid quantity."
                    )

                # BUY EVENT
                timeline.append({
                    "date": trade["entry_date"],
                    "type": "BUY",
                    "symbol": symbol,
                    "price": trade["entry_price"],
                    "quantity": quantity,
                    "trade": trade
                })

                buy_count += 1

                # 2R PARTIAL EXIT EVENT
                if trade.get("partial_exit_done", False):

                    required_partial_fields = [
                        "target_2r_date",
                        "target_2r",
                        "sold_quantity"
                    ]

                    missing_partial_fields = [
                        field for field in required_partial_fields
                        if field not in trade
                    ]

                    if missing_partial_fields:
                        raise ValueError(
                            f"Trade {symbol} is missing partial exit fields: "
                            f"{missing_partial_fields}"
                        )

                    sold_quantity = trade["sold_quantity"]

                    if (
                        isinstance(sold_quantity, bool)
                        or not isinstance(sold_quantity, int)
                        or sold_quantity <= 0
                        or sold_quantity >= quantity
                    ):
                        raise ValueError(
                            f"Trade {symbol} has invalid partial exit quantity."
                        )

                    timeline.append({
                        "date": trade["target_2r_date"],
                        "type": "SELL_2R",
                        "symbol": symbol,
                        "price": trade["target_2r"],
                        "quantity": sold_quantity,
                        "trade": trade
                    })

                    partial_exit_count += 1

                    # Remaining quantity after the partial exit.
                    final_exit_quantity = quantity - sold_quantity

                else:
                    # No partial exit: all shares are sold at final exit.
                    final_exit_quantity = quantity

                # FINAL EXIT EVENT
                if final_exit_quantity <= 0:
                    raise ValueError(
                        f"Trade {symbol} has invalid final exit quantity."
                    )

                timeline.append({
                    "date": trade["exit_date"],
                    "type": "SELL",
                    "symbol": symbol,
                    "price": trade["exit_price"],
                    "quantity": final_exit_quantity,
                    "trade": trade
                })

                final_exit_count += 1

            # Process exits before new entries on the same date.
            priority = {
                "SELL_2R": 0,
                "SELL": 1,
                "BUY": 2
            }

            timeline.sort(
                key=lambda event: (
                    event["date"],
                    priority[event["type"]]
                )
            )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "portfolio_timeline_built",
                extra={
                    "event": "portfolio_timeline_built",
                    "trade_count": len(trades),
                    "event_count": len(timeline),
                    "buy_events": buy_count,
                    "partial_exit_events": partial_exit_count,
                    "final_exit_events": final_exit_count,
                    "duration_ms": duration_ms
                }
            )

            return timeline

        except Exception:
            logger.exception(
                "portfolio_timeline_build_failed",
                extra={
                    "event": "portfolio_timeline_build_failed",
                    "trade_count": (
                        len(trades) if isinstance(trades, list) else None
                    )
                }
            )
            raise

    
    def execute_portfolio(
        self,
        db: Session,
        symbols: list
    ):
        """
        Execute portfolio trades chronologically while managing shared capital,
        position allocation, daily entry limits, and realized profits.
        """

        start_time = time.perf_counter()

        daily_entries = defaultdict(int)

        executed_trades = []
        skipped_trades = []
        portfolio_events = []
        trade_decisions = []

        open_positions = {}

        try:
            # Validate portfolio configuration.
            initial_capital = self.config.initial_capital
            capital_mode = self.config.capital_mode

            if (
                isinstance(initial_capital, bool)
                or not isinstance(initial_capital, (int, float))
                or not math.isfinite(initial_capital)
                or initial_capital <= 0
            ):
                raise ValueError("Initial capital must be positive and finite.")

            if capital_mode not in ("fixed", "compound", "profit_only"):
                raise ValueError(
                    f"Unsupported capital mode: {capital_mode}"
                )

            if not isinstance(symbols, list) or not symbols:
                raise ValueError("At least one symbol is required.")

            logger.info(
                "portfolio_execution_started",
                extra={
                    "event": "portfolio_execution_started",
                    "symbol_count": len(symbols),
                    "initial_capital": initial_capital,
                    "capital_mode": capital_mode
                }
            )

            # Load all portfolio trades.
            trades = self.load_all_trades(
                db,
                symbols
            )

            # Rank trades by trading day.
            trades = self.rank_daily_trades(trades)

            # Build chronological execution timeline.
            timeline = self.build_timeline(trades)

            portfolio_value = float(initial_capital)
            available_cash = portfolio_value
            weekly_capital = portfolio_value

            current_week = None
            locked_capital = 0.0

            # Execution statistics.
            buy_count = 0
            partial_exit_count = 0
            final_exit_count = 0
            low_score_skips = 0
            daily_limit_skips = 0
            capital_skips = 0

            logger.info(
                "portfolio_timeline_ready",
                extra={
                    "event": "portfolio_timeline_ready",
                    "trade_count": len(trades),
                    "event_count": len(timeline)
                }
            )

            for event in timeline:

                event_date = event["date"]

                # Use ISO year and week to identify trading weeks.
                iso_calendar = event_date.isocalendar()
                event_week = (iso_calendar.year, iso_calendar.week)

                if current_week != event_week:
                    current_week = event_week
                    weekly_capital = portfolio_value

                    logger.debug(
                        "portfolio_weekly_capital_updated",
                        extra={
                            "event": "portfolio_weekly_capital_updated",
                            "week": event_week,
                            "weekly_capital": round(weekly_capital, 2)
                        }
                    )

                symbol = event["symbol"]
                trade = event["trade"]
                event_type = event["type"]

                # --------------------------------------------------
                # BUY EVENT
                # --------------------------------------------------

                if event_type == "BUY":

                    # Minimum trade quality score.
                    trade_score = trade.get("total_score", 0)

                    if (
                        isinstance(trade_score, bool)
                        or not isinstance(trade_score, (int, float))
                        or not math.isfinite(trade_score)
                    ):
                        raise ValueError(
                            f"Invalid trade score for {symbol}."
                        )

                    if trade_score < self.strategy_config.min_trade_score:

                        skipped_trades.append(trade)
                        low_score_skips += 1

                        trade_decisions.append(
                            TradeDecision(
                                symbol=symbol,
                                date=event_date,
                                decision="SKIPPED",
                                reason="LOW_TRADE_SCORE"
                            )
                        )

                        logger.debug(
                            "portfolio_trade_skipped",
                            extra={
                                "event": "portfolio_trade_skipped",
                                "symbol": symbol,
                                "reason": "LOW_TRADE_SCORE",
                                "trade_score": trade_score
                            }
                        )

                        continue

                    # Avoid duplicate positions in the same symbol.
                    if symbol in open_positions:

                        logger.debug(
                            "portfolio_trade_skipped",
                            extra={
                                "event": "portfolio_trade_skipped",
                                "symbol": symbol,
                                "reason": "POSITION_ALREADY_OPEN"
                            }
                        )

                        skipped_trades.append(trade)

                        trade_decisions.append(
                            TradeDecision(
                                symbol=symbol,
                                date=event_date,
                                decision="SKIPPED",
                                reason="POSITION_ALREADY_OPEN"
                            )
                        )

                        continue

                    # Check daily entry limit.
                    if (
                        daily_entries[event_date]
                        >= self.config.max_daily_entries
                    ):

                        skipped_trades.append(trade)
                        daily_limit_skips += 1

                        trade_decisions.append(
                            TradeDecision(
                                symbol=symbol,
                                date=event_date,
                                decision="SKIPPED",
                                reason="DAILY_LIMIT_REACHED"
                            )
                        )

                        logger.debug(
                            "portfolio_trade_skipped",
                            extra={
                                "event": "portfolio_trade_skipped",
                                "symbol": symbol,
                                "reason": "DAILY_LIMIT_REACHED",
                                "date": event_date
                            }
                        )

                        continue

                    # Original position capital requirement.
                    capital_required = trade.get("capital_used")

                    if (
                        isinstance(capital_required, bool)
                        or not isinstance(capital_required, (int, float))
                        or not math.isfinite(capital_required)
                        or capital_required <= 0
                    ):
                        raise ValueError(
                            f"Invalid capital requirement for {symbol}."
                        )

                    # Calculate position capital allocation ratio.
                    risk_ratio = capital_required / initial_capital

                    # FIXED CAPITAL MODE.
                    if capital_mode == "fixed":

                        capital_required = trade["capital_used"]

                    # COMPOUND CAPITAL MODE.
                    elif capital_mode == "compound":

                        if self.config.capital_update == "weekly":
                            capital_required = weekly_capital * risk_ratio
                        else:
                            capital_required = portfolio_value * risk_ratio

                    # PROFIT ONLY CAPITAL MODE.
                    elif capital_mode == "profit_only":

                        effective_capital = max(
                            portfolio_value,
                            initial_capital
                        )

                        if self.config.capital_update == "weekly":

                            effective_capital = max(
                                weekly_capital,
                                initial_capital
                            )

                        capital_required = effective_capital * risk_ratio

                    if (
                        not math.isfinite(capital_required)
                        or capital_required <= 0
                    ):
                        raise ValueError(
                            f"Invalid allocated capital for {symbol}."
                        )

                    # Check available cash.
                    if (
                        self.config.capital_check
                        and capital_required > available_cash
                    ):

                        skipped_trades.append(trade)
                        capital_skips += 1

                        trade_decisions.append(
                            TradeDecision(
                                symbol=symbol,
                                date=event_date,
                                decision="SKIPPED",
                                reason="INSUFFICIENT_CAPITAL",
                                capital_required=capital_required,
                                available_capital=available_cash
                            )
                        )

                        logger.debug(
                            "portfolio_trade_skipped",
                            extra={
                                "event": "portfolio_trade_skipped",
                                "symbol": symbol,
                                "reason": "INSUFFICIENT_CAPITAL",
                                "capital_required": round(capital_required, 2),
                                "available_cash": round(available_cash, 2)
                            }
                        )

                        continue

                    # Reserve portfolio capital.
                    available_cash -= capital_required
                    locked_capital += capital_required

                    capital_limit = portfolio_value

                    if capital_mode != "compound":
                        capital_limit = initial_capital

                    # Validate portfolio capital allocation.
                    if (
                        self.config.capital_check
                        and locked_capital > capital_limit + 0.01
                    ):
                        raise RuntimeError(
                            f"Portfolio capital exceeded for {symbol}. "
                            f"Locked={locked_capital}, "
                            f"Limit={capital_limit}, "
                            f"Available={available_cash}"
                        )

                    # Register open position.
                    open_positions[symbol] = {
                        "trade": trade,
                        "locked_capital": capital_required
                    }

                    executed_trades.append(trade)
                    daily_entries[event_date] += 1
                    buy_count += 1

                    logger.info(
                        "portfolio_position_opened",
                        extra={
                            "event": "portfolio_position_opened",
                            "symbol": symbol,
                            "date": event_date,
                            "trade_score": trade_score,
                            "capital_allocated": round(capital_required, 2),
                            "available_cash": round(available_cash, 2),
                            "locked_capital": round(locked_capital, 2),
                            "open_positions": len(open_positions)
                        }
                    )

                # --------------------------------------------------
                # 2R PARTIAL EXIT EVENT
                # --------------------------------------------------

                elif event_type == "SELL_2R":

                    if symbol not in open_positions:

                        logger.warning(
                            "portfolio_partial_exit_without_position",
                            extra={
                                "event": "portfolio_partial_exit_without_position",
                                "symbol": symbol,
                                "date": event_date
                            }
                        )

                        continue

                    position = open_positions[symbol]

                    original_quantity = trade["quantity"]
                    sold_quantity = event["quantity"]

                    if (
                        original_quantity <= 0
                        or sold_quantity <= 0
                        or sold_quantity >= original_quantity
                    ):
                        raise ValueError(
                            f"Invalid partial exit quantity for {symbol}."
                        )

                    # Release the proportional reserved capital.
                    released = (
                        position["locked_capital"]
                        * sold_quantity
                        / original_quantity
                    )

                    position["locked_capital"] -= released

                    available_cash += released
                    locked_capital -= released

                    partial_exit_count += 1

                    logger.info(
                        "portfolio_partial_exit_executed",
                        extra={
                            "event": "portfolio_partial_exit_executed",
                            "symbol": symbol,
                            "date": event_date,
                            "sold_quantity": sold_quantity,
                            "released_capital": round(released, 2),
                            "remaining_locked_capital": round(
                                position["locked_capital"], 2
                            )
                        }
                    )

                # --------------------------------------------------
                # FINAL EXIT EVENT
                # --------------------------------------------------

                elif event_type == "SELL":

                    if symbol not in open_positions:

                        logger.warning(
                            "portfolio_exit_without_position",
                            extra={
                                "event": "portfolio_exit_without_position",
                                "symbol": symbol,
                                "date": event_date
                            }
                        )

                        continue

                    position = open_positions[symbol]

                    # Release remaining reserved capital.
                    released = position["locked_capital"]

                    available_cash += released
                    locked_capital -= released

                    # Calculate actual turnover, including partial exits.
                    buy_value = (
                        trade["entry_price"]
                        * trade["quantity"]
                    )

                    if trade.get("partial_exit_done", False):

                        partial_quantity = trade["sold_quantity"]
                        final_quantity = trade["quantity"] - partial_quantity

                        sell_value = (
                            trade["target_2r"] * partial_quantity
                            + trade["exit_price"] * final_quantity
                        )

                    else:

                        sell_value = (
                            trade["exit_price"]
                            * trade["quantity"]
                        )

                    # Calculate brokerage, taxes and other trading costs.
                    cost = self.cost_engine.calculate_trade_cost(
                        buy_value,
                        sell_value
                    )

                    if (
                        not isinstance(cost, dict)
                        or "total" not in cost
                        or not isinstance(cost["total"], (int, float))
                        or isinstance(cost["total"], bool)
                        or not math.isfinite(cost["total"])
                    ):
                        raise ValueError(
                            f"Invalid trading cost returned for {symbol}."
                        )

                    trade["trading_cost"] = cost

                    # Apply trading costs to realized trade profit.
                    trade["profit"] -= cost["total"]

                    # Update portfolio value for every capital mode.
                    # Fixed mode keeps fixed position sizing.
                    # Compound and profit_only use the updated value
                    # for subsequent capital allocation.
                    portfolio_value += trade["profit"]
                    available_cash += trade["profit"]

                    if available_cash < -0.01:
                        raise RuntimeError(
                            f"Negative cash balance after closing {symbol}."
                        )

                    del open_positions[symbol]

                    final_exit_count += 1

                    logger.info(
                        "portfolio_position_closed",
                        extra={
                            "event": "portfolio_position_closed",
                            "symbol": symbol,
                            "date": event_date,
                            "gross_profit": round(
                                trade["profit"] + cost["total"], 2
                            ),
                            "trading_cost": round(cost["total"], 2),
                            "net_profit": round(trade["profit"], 2),
                            "portfolio_value": round(portfolio_value, 2),
                            "available_cash": round(available_cash, 2),
                            "locked_capital": round(locked_capital, 2)
                        }
                    )

                else:

                    raise ValueError(
                        f"Unsupported portfolio event type: {event_type}"
                    )

                # --------------------------------------------------
                # PORTFOLIO VALIDATION
                # --------------------------------------------------

                total_assets = available_cash + locked_capital

                if abs(total_assets - portfolio_value) > 1:

                    raise RuntimeError(
                        f"Portfolio balance mismatch on {event_date}. "
                        f"Portfolio={portfolio_value}, "
                        f"Cash={available_cash}, "
                        f"Locked={locked_capital}, "
                        f"Total={total_assets}"
                    )

                # Record portfolio state after each event.
                portfolio_events.append({
                    **event,
                    "available_cash": round(available_cash, 2),
                    "portfolio_value": round(portfolio_value, 2),
                    "locked_capital": round(locked_capital, 2),
                    "open_positions": len(open_positions)
                })

            # --------------------------------------------------
            # FINAL PORTFOLIO SUMMARY
            # --------------------------------------------------

            if open_positions:

                logger.warning(
                    "portfolio_execution_has_open_positions",
                    extra={
                        "event": "portfolio_execution_has_open_positions",
                        "open_position_count": len(open_positions),
                        "symbols": list(open_positions.keys())
                    }
                )

            result = {
                "timeline": portfolio_events,
                "executed_trades": executed_trades,
                "skipped_trades": skipped_trades,
                "trade_decisions": [
                    vars(decision)
                    for decision in trade_decisions
                ],
                "portfolio_summary": {
                    "initial_capital": round(initial_capital, 2),
                    "final_portfolio_value": round(portfolio_value, 2),
                    "available_cash": round(available_cash, 2),
                    "locked_capital": round(locked_capital, 2),
                    "net_profit": round(
                        portfolio_value - initial_capital, 2
                    ),
                    "executed_trade_count": len(executed_trades),
                    "skipped_trade_count": len(skipped_trades),
                    "open_position_count": len(open_positions),
                    "buy_events": buy_count,
                    "partial_exit_events": partial_exit_count,
                    "final_exit_events": final_exit_count,
                    "low_score_skips": low_score_skips,
                    "daily_limit_skips": daily_limit_skips,
                    "capital_skips": capital_skips
                }
            }

            # Validate and clean the final result.
            self.helper.find_bad(result)

            cleaned_result = self.helper.clean(result)

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "portfolio_execution_completed",
                extra={
                    "event": "portfolio_execution_completed",
                    "symbol_count": len(symbols),
                    "executed_trades": len(executed_trades),
                    "skipped_trades": len(skipped_trades),
                    "final_portfolio_value": round(portfolio_value, 2),
                    "net_profit": round(
                        portfolio_value - initial_capital, 2
                    ),
                    "open_positions": len(open_positions),
                    "duration_ms": duration_ms
                }
            )

            return cleaned_result

        except Exception:
            logger.exception(
                "portfolio_execution_failed",
                extra={
                    "event": "portfolio_execution_failed",
                    "symbol_count": (
                        len(symbols) if isinstance(symbols, list) else None
                    ),
                    "executed_trades": len(executed_trades),
                    "skipped_trades": len(skipped_trades),
                    "open_positions": len(open_positions)
                }
            )
            raise

    
    def portfolio_summary(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate overall portfolio performance metrics.

        Calculates trade count, win rate, net profit, average profit,
        best trade, and worst trade.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Portfolio summary started.",
                extra={
                    "event": "portfolio_summary_started",
                    "symbol_count": len(symbols)
                }
            )

            # Execute portfolio backtest.
            portfolio = self.execute_portfolio(db, symbols)

            trades = portfolio.get("executed_trades", [])

            total_trades = len(trades)
            winning = 0
            losing = 0
            net_profit = 0.0

            # None ensures correct best/worst values for all-winning
            # or all-losing portfolios.
            best_trade = None
            worst_trade = None

            for trade in trades:
                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid trade profit encountered."
                    )

                net_profit += profit

                if profit > 0:
                    winning += 1
                else:
                    losing += 1

                best_trade = (
                    profit if best_trade is None
                    else max(best_trade, profit)
                )

                worst_trade = (
                    profit if worst_trade is None
                    else min(worst_trade, profit)
                )

            result = {
                "total_trades": total_trades,
                "winning_trades": winning,
                "losing_trades": losing,

                "win_rate": round(
                    (winning / total_trades) * 100,
                    2
                ) if total_trades else 0,

                "net_profit": round(net_profit, 2),

                "average_profit": round(
                    net_profit / total_trades,
                    2
                ) if total_trades else 0,

                "best_trade": round(best_trade, 2)
                if best_trade is not None else 0,

                "worst_trade": round(worst_trade, 2)
                if worst_trade is not None else 0
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Portfolio summary completed.",
                extra={
                    "event": "portfolio_summary_completed",
                    "total_trades": total_trades,
                    "winning_trades": winning,
                    "losing_trades": losing,
                    "net_profit": result["net_profit"],
                    "win_rate": result["win_rate"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Portfolio summary failed.",
                extra={
                    "event": "portfolio_summary_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise

    
    def portfolio_statistics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate portfolio execution and capital utilization statistics.

        Calculates execution rate, average available cash,
        average and maximum open positions, and capital utilization.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Portfolio statistics started.",
                extra={
                    "event": "portfolio_statistics_started",
                    "symbol_count": len(symbols)
                }
            )

            # Execute portfolio backtest.
            portfolio = self.execute_portfolio(db, symbols)

            executed_trades = portfolio.get("executed_trades", [])
            skipped_trades = portfolio.get("skipped_trades", [])
            timeline = portfolio.get("timeline", [])

            executed_count = len(executed_trades)
            skipped_count = len(skipped_trades)

            total_opportunities = executed_count + skipped_count

            # Cash statistics.
            cash_values = []
            open_position_counts = []
            utilization = []

            for event in timeline:

                available_cash = event.get("available_cash", 0)
                locked_capital = event.get("locked_capital", 0)
                portfolio_value = event.get("portfolio_value", 0)
                open_positions = event.get("open_positions", 0)

                # Validate numeric portfolio values.
                numeric_values = {
                    "available_cash": available_cash,
                    "locked_capital": locked_capital,
                    "portfolio_value": portfolio_value
                }

                for field, value in numeric_values.items():
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError(
                            f"Invalid {field} in portfolio timeline."
                        )

                # Support either an integer count or a positions dictionary.
                if isinstance(open_positions, dict):
                    open_positions = len(open_positions)

                if (
                    isinstance(open_positions, bool)
                    or not isinstance(open_positions, int)
                    or open_positions < 0
                ):
                    raise ValueError(
                        "Invalid open_positions in portfolio timeline."
                    )

                cash_values.append(available_cash)
                open_position_counts.append(open_positions)

                # Capital utilization.
                if portfolio_value > 0:
                    utilization.append(
                        (locked_capital / portfolio_value) * 100
                    )
                else:
                    utilization.append(0.0)

            # Average available cash.
            average_cash = (
                sum(cash_values) / len(cash_values)
                if cash_values else 0
            )

            # Open position statistics.
            average_open_positions = (
                sum(open_position_counts) / len(open_position_counts)
                if open_position_counts else 0
            )

            max_open_positions = (
                max(open_position_counts)
                if open_position_counts else 0
            )

            # Capital utilization statistics.
            average_utilization = (
                sum(utilization) / len(utilization)
                if utilization else 0
            )

            max_utilization = (
                max(utilization)
                if utilization else 0
            )

            result = {
                "total_opportunities": total_opportunities,

                "executed_trades": executed_count,

                "skipped_trades": skipped_count,

                "execution_rate": round(
                    (executed_count / total_opportunities) * 100,
                    2
                ) if total_opportunities else 0,

                "average_cash": round(average_cash, 2),

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

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Portfolio statistics completed.",
                extra={
                    "event": "portfolio_statistics_completed",
                    "total_opportunities": total_opportunities,
                    "executed_trades": executed_count,
                    "skipped_trades": skipped_count,
                    "execution_rate": result["execution_rate"],
                    "average_capital_utilization": result[
                        "average_capital_utilization"
                    ],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Portfolio statistics failed.",
                extra={
                    "event": "portfolio_statistics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise

    
    def trade_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate detailed trade performance analytics.

        Calculates profitability, reward-to-risk, streaks,
        trade distribution, risk metrics, and trade quality score.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Trade analytics started.",
                extra={
                    "event": "trade_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            winning = []
            losing = []

            gross_profit = 0.0
            gross_loss = 0.0

            # Calculate trade-level profit consistently.
            for trade in trades:

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
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
                winning_trades / total * 100
                if total else 0
            )

            average_win = (
                sum(winning) / winning_trades
                if winning_trades else 0
            )

            average_loss = (
                abs(sum(losing)) / losing_trades
                if losing_trades else 0
            )

            net_profit = gross_profit - gross_loss

            # Profit factor is undefined when there are no losses.
            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0
                else None
            )

            # Existing analytics components.
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

            expectancy = self.calculate_expectancy(trades)

            reward_risk_ratio = self.calculate_reward_risk_ratio(
                trades
            )

            trade_score = self.calculate_trade_score(trades)

            result = {
                "total_trades": total,

                "winning_trades": winning_trades,

                "losing_trades": losing_trades,

                "win_rate": round(win_rate, 2),

                "gross_profit": round(gross_profit, 2),

                "gross_loss": round(gross_loss, 2),

                "net_profit": round(net_profit, 2),

                "profit_factor": round(profit_factor, 2)
                if profit_factor is not None else None,

                "average_win": round(
                    trade_values["average_win"], 2
                ),

                "average_loss": round(
                    trade_values["average_loss"], 2
                ),

                "expectancy": round(expectancy, 2),

                "largest_win": round(
                    max(winning) if winning else 0, 2
                ),

                "largest_loss": round(
                    min(losing) if losing else 0, 2
                ),

                "reward_risk_ratio": reward_risk_ratio,

                "max_winning_streak": streaks[
                    "max_winning_streak"
                ],

                "max_losing_streak": streaks[
                    "max_losing_streak"
                ],

                "trade_distribution": distribution,

                "risk_metrics": risk_metrics,

                "trade_score": trade_score
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Trade analytics completed.",
                extra={
                    "event": "trade_analytics_completed",
                    "total_trades": total,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "net_profit": result["net_profit"],
                    "win_rate": result["win_rate"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Trade analytics failed.",
                extra={
                    "event": "trade_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def risk_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate portfolio risk analytics.

        Calculates consecutive wins/losses, maximum drawdown,
        longest drawdown duration, and ending equity.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            initial_capital = self.config.initial_capital

            if (
                isinstance(initial_capital, bool)
                or not isinstance(initial_capital, (int, float))
                or not math.isfinite(initial_capital)
                or initial_capital <= 0
            ):
                raise ValueError(
                    "Initial capital must be a positive finite number."
                )

            logger.info(
                "Risk analytics started.",
                extra={
                    "event": "risk_analytics_started",
                    "symbol_count": len(symbols),
                    "initial_capital": initial_capital
                }
            )

            portfolio = self.execute_portfolio(db, symbols)

            trades = portfolio.get("executed_trades", [])

            # Risk calculations must follow the order in which
            # trades are closed, not necessarily the order they were entered.
            trades = sorted(
                trades,
                key=lambda trade: str(
                    trade.get("exit_date", "")
                )
            )

            max_consecutive_wins = 0
            max_consecutive_losses = 0

            current_wins = 0
            current_losses = 0

            equity = float(initial_capital)
            peak = equity

            max_drawdown = 0.0

            longest_drawdown = 0
            current_drawdown = 0

            for trade in trades:

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
                    )

                #
                # Win / Loss streaks
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
                # Equity and drawdown
                #

                equity += profit

                if equity >= peak:

                    peak = equity
                    current_drawdown = 0

                else:

                    current_drawdown += 1

                    longest_drawdown = max(
                        longest_drawdown,
                        current_drawdown
                    )

                    drawdown = (
                        (peak - equity) / peak
                    ) * 100

                    max_drawdown = max(
                        max_drawdown,
                        drawdown
                    )

            result = {
                "max_consecutive_wins": max_consecutive_wins,

                "max_consecutive_losses": max_consecutive_losses,

                "max_drawdown_percent": round(
                    max_drawdown, 2
                ),

                "longest_drawdown_trades": longest_drawdown,

                "ending_equity": round(equity, 2)
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Risk analytics completed.",
                extra={
                    "event": "risk_analytics_completed",
                    "total_trades": len(trades),
                    "max_drawdown_percent": result[
                        "max_drawdown_percent"
                    ],
                    "max_consecutive_losses": max_consecutive_losses,
                    "ending_equity": result["ending_equity"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Risk analytics failed.",
                extra={
                    "event": "risk_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def holding_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate trade holding-period analytics.

        Calculates average holding periods for all trades,
        winning trades, losing trades, and holding-period extremes.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Holding analytics started.",
                extra={
                    "event": "holding_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            holding_days = []
            winning_days = []
            losing_days = []

            for trade in trades:

                days = trade.get("holding_days")

                if (
                    isinstance(days, bool)
                    or not isinstance(days, (int, float))
                    or not math.isfinite(days)
                    or days < 0
                ):
                    raise ValueError(
                        "Invalid holding_days encountered."
                    )

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
                    )

                holding_days.append(days)

                if profit > 0:
                    winning_days.append(days)
                else:
                    losing_days.append(days)

            result = {
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

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Holding analytics completed.",
                extra={
                    "event": "holding_analytics_completed",
                    "total_trades": len(trades),
                    "average_holding_days": result[
                        "average_holding_days"
                    ],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Holding analytics failed.",
                extra={
                    "event": "holding_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def monthly_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate month-wise portfolio performance analytics.

        Groups executed trades by exit month and calculates
        trade count, wins, losses, win rate, and net profit.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Monthly analytics started.",
                extra={
                    "event": "monthly_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            monthly = {}

            for trade in trades:

                exit_date = trade.get("exit_date")

                if not hasattr(exit_date, "year") or not hasattr(
                    exit_date, "month"
                ):
                    raise ValueError(
                        "Invalid or missing trade exit_date."
                    )

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
                    )

                key = f"{exit_date.year}-{exit_date.month:02d}"

                if key not in monthly:
                    monthly[key] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "profit": 0.0
                    }

                monthly[key]["trades"] += 1
                monthly[key]["profit"] += profit

                if profit > 0:
                    monthly[key]["wins"] += 1
                else:
                    monthly[key]["losses"] += 1

            report = []

            for month, data in sorted(monthly.items()):

                total_trades = data["trades"]

                report.append({
                    "month": month,

                    "trades": total_trades,

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(
                        data["wins"] / total_trades * 100,
                        2
                    ) if total_trades else 0,

                    "profit": round(data["profit"], 2)
                })

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Monthly analytics completed.",
                extra={
                    "event": "monthly_analytics_completed",
                    "total_trades": len(trades),
                    "months_analyzed": len(report),
                    "duration_ms": duration_ms
                }
            )

            return report

        except Exception:
            logger.exception(
                "Monthly analytics failed.",
                extra={
                    "event": "monthly_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def yearly_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate year-wise portfolio performance analytics.

        Groups executed trades by exit year and calculates
        trade count, wins, losses, win rate, and net profit.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Yearly analytics started.",
                extra={
                    "event": "yearly_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            yearly = {}

            for trade in trades:

                exit_date = trade.get("exit_date")

                if not hasattr(exit_date, "year"):
                    raise ValueError(
                        "Invalid or missing trade exit_date."
                    )

                year = exit_date.year

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
                    )

                if year not in yearly:
                    yearly[year] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "profit": 0.0
                    }

                yearly[year]["trades"] += 1
                yearly[year]["profit"] += profit

                if profit > 0:
                    yearly[year]["wins"] += 1
                else:
                    yearly[year]["losses"] += 1

            report = []

            for year, data in sorted(yearly.items()):

                total_trades = data["trades"]

                report.append({
                    "year": year,

                    "trades": total_trades,

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(
                        data["wins"] / total_trades * 100,
                        2
                    ) if total_trades else 0,

                    "profit": round(data["profit"], 2)
                })

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Yearly analytics completed.",
                extra={
                    "event": "yearly_analytics_completed",
                    "total_trades": len(trades),
                    "years_analyzed": len(report),
                    "duration_ms": duration_ms
                }
            )

            return report

        except Exception:
            logger.exception(
                "Yearly analytics failed.",
                extra={
                    "event": "yearly_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def market_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate trade performance analytics grouped by market condition.

        Calculates trade count, wins, losses, win rate, and profit
        for each market classification.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Market analytics started.",
                extra={
                    "event": "market_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            report = {}

            for trade in trades:

                market = self.market_engine.classify_market(trade)

                if not isinstance(market, str) or not market.strip():
                    raise ValueError(
                        "Invalid market classification returned."
                    )

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing trade profit."
                    )

                if market not in report:
                    report[market] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "profit": 0.0
                    }

                report[market]["trades"] += 1
                report[market]["profit"] += profit

                if profit > 0:
                    report[market]["wins"] += 1
                else:
                    report[market]["losses"] += 1

            result = []

            for market, data in sorted(report.items()):

                total_trades = data["trades"]

                result.append({
                    "market": market,

                    "trades": total_trades,

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(
                        data["wins"] / total_trades * 100,
                        2
                    ) if total_trades else 0,

                    "profit": round(data["profit"], 2)
                })

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Market analytics completed.",
                extra={
                    "event": "market_analytics_completed",
                    "total_trades": len(trades),
                    "market_conditions": len(result),
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Market analytics failed.",
                extra={
                    "event": "market_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def sector_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate trade performance analytics grouped by sector.

        Calculates trade count, wins, losses, win rate, and profit
        for each sector.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Sector analytics started.",
                extra={
                    "event": "sector_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            trades = portfolio.get("executed_trades", [])

            sectors = {}

            for trade in trades:

                symbol = trade.get("symbol")

                if not isinstance(symbol, str) or not symbol.strip():
                    raise ValueError(
                        "Invalid or missing trade symbol."
                    )

                sector = self.sector_engine.get_sector(symbol)

                if not isinstance(sector, str) or not sector.strip():
                    raise ValueError(
                        f"Invalid sector classification for {symbol}."
                    )

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        f"Invalid or missing trade profit for {symbol}."
                    )

                if sector not in sectors:
                    sectors[sector] = {
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "profit": 0.0
                    }

                sectors[sector]["trades"] += 1
                sectors[sector]["profit"] += profit

                if profit > 0:
                    sectors[sector]["wins"] += 1
                else:
                    sectors[sector]["losses"] += 1

            report = []

            for sector, data in sorted(sectors.items()):

                total_trades = data["trades"]

                report.append({
                    "sector": sector,

                    "trades": total_trades,

                    "wins": data["wins"],

                    "losses": data["losses"],

                    "win_rate": round(
                        data["wins"] / total_trades * 100,
                        2
                    ) if total_trades else 0,

                    "profit": round(data["profit"], 2)
                })

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Sector analytics completed.",
                extra={
                    "event": "sector_analytics_completed",
                    "total_trades": len(trades),
                    "sectors_analyzed": len(report),
                    "duration_ms": duration_ms
                }
            )

            return report

        except Exception:
            logger.exception(
                "Sector analytics failed.",
                extra={
                    "event": "sector_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def skipped_trade_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Generate analytics for executed and skipped trade opportunities.

        Calculates hypothetical profits and losses associated with
        skipped trades based on their recorded backtest outcomes.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Skipped trade analytics started.",
                extra={
                    "event": "skipped_trade_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)

            executed = portfolio.get("executed_trades", [])
            skipped = portfolio.get("skipped_trades", [])

            missed_profit = 0.0
            missed_loss = 0.0

            profitable_skipped = 0
            losing_skipped = 0

            for trade in skipped:

                profit = trade.get("net_profit")

                if profit is None:
                    profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Invalid or missing skipped trade profit."
                    )

                if profit > 0:
                    profitable_skipped += 1
                    missed_profit += profit

                else:
                    losing_skipped += 1
                    missed_loss += abs(profit)

            total_opportunities = len(executed) + len(skipped)

            result = {
                "total_opportunities": total_opportunities,

                "executed_trades": len(executed),

                "skipped_trades": len(skipped),

                "profitable_skipped": profitable_skipped,

                "losing_skipped": losing_skipped,

                "missed_profit": round(missed_profit, 2),

                "missed_loss": round(missed_loss, 2),

                "net_missed": round(
                    missed_profit - missed_loss,
                    2
                )
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Skipped trade analytics completed.",
                extra={
                    "event": "skipped_trade_analytics_completed",
                    "total_opportunities": total_opportunities,
                    "executed_trades": len(executed),
                    "skipped_trades": len(skipped),
                    "profitable_skipped": profitable_skipped,
                    "net_missed": result["net_missed"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Skipped trade analytics failed.",
                extra={
                    "event": "skipped_trade_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def capital_utilization_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Analyze portfolio capital utilization and cash availability.

        Calculates average, maximum and minimum capital utilization,
        available cash, and open-position statistics.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Capital utilization analytics started.",
                extra={
                    "event": "capital_utilization_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            timeline = portfolio.get("timeline", [])

            utilization = []
            cash = []
            open_positions = []

            for event in timeline:

                portfolio_value = event.get("portfolio_value")
                locked_capital = event.get("locked_capital")
                available_cash = event.get("available_cash")
                positions = event.get("open_positions")

                values = {
                    "portfolio_value": portfolio_value,
                    "locked_capital": locked_capital,
                    "available_cash": available_cash
                }

                for field, value in values.items():
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError(
                            f"Invalid {field} in portfolio timeline."
                        )

                # Support both a position count and a positions dictionary.
                if isinstance(positions, dict):
                    positions = len(positions)

                if (
                    isinstance(positions, bool)
                    or not isinstance(positions, int)
                    or positions < 0
                ):
                    raise ValueError(
                        "Invalid open_positions in portfolio timeline."
                    )

                if portfolio_value > 0:
                    utilization.append(
                        (locked_capital / portfolio_value) * 100
                    )
                else:
                    utilization.append(0.0)

                cash.append(available_cash)
                open_positions.append(positions)

            result = {
                "average_utilization": round(
                    sum(utilization) / len(utilization), 2
                ) if utilization else 0,

                "maximum_utilization": round(
                    max(utilization), 2
                ) if utilization else 0,

                "minimum_utilization": round(
                    min(utilization), 2
                ) if utilization else 0,

                "average_available_cash": round(
                    sum(cash) / len(cash), 2
                ) if cash else 0,

                "minimum_available_cash": round(
                    min(cash), 2
                ) if cash else 0,

                "maximum_open_positions": max(
                    open_positions
                ) if open_positions else 0,

                "average_open_positions": round(
                    sum(open_positions) / len(open_positions), 2
                ) if open_positions else 0
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Capital utilization analytics completed.",
                extra={
                    "event": "capital_utilization_analytics_completed",
                    "timeline_events": len(timeline),
                    "average_utilization": result["average_utilization"],
                    "maximum_utilization": result["maximum_utilization"],
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Capital utilization analytics failed.",
                extra={
                    "event": "capital_utilization_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def overlap_analytics(
        self,
        db: Session,
        symbols: list
    ):
        """
        Analyze simultaneous open-position overlap.

        Calculates maximum concurrent positions and the distribution
        of portfolio timeline events by open-position count.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Overlap analytics started.",
                extra={
                    "event": "overlap_analytics_started",
                    "symbol_count": len(symbols)
                }
            )

            portfolio = self.execute_portfolio(db, symbols)
            timeline = portfolio.get("timeline", [])

            overlap_distribution = {}
            max_overlap = 0

            for event in timeline:

                positions = event.get("open_positions")

                if isinstance(positions, dict):
                    positions = len(positions)

                if (
                    isinstance(positions, bool)
                    or not isinstance(positions, int)
                    or positions < 0
                ):
                    raise ValueError(
                        "Invalid open_positions in portfolio timeline."
                    )

                max_overlap = max(max_overlap, positions)

                overlap_distribution[positions] = (
                    overlap_distribution.get(positions, 0) + 1
                )

            total_events = len(timeline)

            report = []

            for positions in sorted(overlap_distribution):

                count = overlap_distribution[positions]

                report.append({
                    "open_positions": positions,

                    "events": count,

                    "percentage": round(
                        (count / total_events) * 100,
                        2
                    ) if total_events else 0
                })

            result = {
                "maximum_overlap": max_overlap,
                "distribution": report
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Overlap analytics completed.",
                extra={
                    "event": "overlap_analytics_completed",
                    "maximum_overlap": max_overlap,
                    "timeline_events": total_events,
                    "duration_ms": duration_ms
                }
            )

            return result

        except Exception:
            logger.exception(
                "Overlap analytics failed.",
                extra={
                    "event": "overlap_analytics_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def optimize_strategy(
        self,
        db: Session,
        symbols: list
    ):
        """
        Optimize strategy parameters and export the results.

        Uses ParameterOptimizer to evaluate configurations
        and exports the optimization results to CSV.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Strategy optimization started.",
                extra={
                    "event": "strategy_optimization_started",
                    "symbol_count": len(symbols)
                }
            )

            results = self.optimizer.evaluate_configs(
                self,
                db,
                symbols
            )

            if not results:
                raise ValueError(
                    "Strategy optimizer returned no results."
                )

            report_path = self.report_exporter.export_csv(results)

            if not report_path:
                raise RuntimeError(
                    "Strategy optimization report export failed."
                )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Strategy optimization completed.",
                extra={
                    "event": "strategy_optimization_completed",
                    "configurations_evaluated": len(results),
                    "report_path": str(report_path),
                    "duration_ms": duration_ms
                }
            )

            return {
                "report": report_path,
                "results": results
            }

        except Exception:
            logger.exception(
                "Strategy optimization failed.",
                extra={
                    "event": "strategy_optimization_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def generate_walk_forward_windows(
        self,
        start_year: int,
        end_year: int
    ):
        """
        Generate expanding-window walk-forward periods.

        Each window uses all available years from start_year
        through train_end for training, followed by one test year.
        """
        if (
            isinstance(start_year, bool)
            or not isinstance(start_year, int)
            or isinstance(end_year, bool)
            or not isinstance(end_year, int)
        ):
            raise ValueError("Years must be integers.")

        if start_year >= end_year:
            raise ValueError(
                "end_year must be greater than start_year."
            )

        windows = []

        for train_end in range(start_year, end_year):

            windows.append({
                "train_start": start_year,
                "train_end": train_end,
                "test_year": train_end + 1
            })

        logger.info(
            "Walk-forward windows generated.",
            extra={
                "event": "walk_forward_windows_generated",
                "start_year": start_year,
                "end_year": end_year,
                "total_windows": len(windows)
            }
        )

        return windows


    def walk_forward_analysis(
        self,
        db,
        symbols: list
    ):
        """
        Execute walk-forward strategy validation.

        Optimizes strategy parameters on expanding training periods
        and evaluates the selected parameters on subsequent test years.
        """
        start_time = time.perf_counter()

        try:
            if not symbols:
                raise ValueError("Symbols list cannot be empty.")

            logger.info(
                "Walk-forward analysis started.",
                extra={
                    "event": "walk_forward_analysis_started",
                    "symbol_count": len(symbols)
                }
            )

            # Existing analysis period.
            windows = self.generate_walk_forward_windows(
                2022,
                2026
            )

            results = []
            optimization_history = []
            failed_windows = []

            for window in windows:

                window_start = time.perf_counter()

                training_period = (
                    f"{window['train_start']}-"
                    f"{window['train_end']}"
                )

                logger.info(
                    "Walk-forward window started.",
                    extra={
                        "event": "walk_forward_window_started",
                        "training_period": training_period,
                        "test_year": window["test_year"]
                    }
                )

                try:
                    result = self.execute_walk_forward_window(
                        db,
                        window["train_start"],
                        window["train_end"],
                        window["test_year"],
                        symbols
                    )

                    if not isinstance(result, dict):
                        raise ValueError(
                            "Invalid walk-forward result."
                        )

                    required_fields = [
                        "best_parameters",
                        "net_profit",
                        "win_rate"
                    ]

                    for field in required_fields:
                        if field not in result:
                            raise ValueError(
                                f"Missing walk-forward result field: {field}"
                            )

                    for field in ["net_profit", "win_rate"]:
                        value = result[field]

                        if (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(value)
                        ):
                            raise ValueError(
                                f"Invalid {field} in walk-forward result."
                            )

                    optimization_history.append({
                        "training_period": training_period,
                        "test_year": window["test_year"],
                        "best_parameters": result["best_parameters"]
                    })

                    results.append(result)

                    logger.info(
                        "Walk-forward window completed.",
                        extra={
                            "event": "walk_forward_window_completed",
                            "training_period": training_period,
                            "test_year": window["test_year"],
                            "net_profit": result["net_profit"],
                            "win_rate": result["win_rate"],
                            "duration_ms": round(
                                (time.perf_counter() - window_start) * 1000,
                                2
                            )
                        }
                    )

                except Exception as exc:

                    failed_windows.append({
                        "training_period": training_period,
                        "test_year": window["test_year"],
                        "error": str(exc)
                    })

                    logger.exception(
                        "Walk-forward window failed.",
                        extra={
                            "event": "walk_forward_window_failed",
                            "training_period": training_period,
                            "test_year": window["test_year"]
                        }
                    )

                    # Continue evaluating the remaining windows.
                    continue

            average_profit = (
                sum(result["net_profit"] for result in results)
                / len(results)
                if results else 0
            )

            average_win_rate = (
                sum(result["win_rate"] for result in results)
                / len(results)
                if results else 0
            )

            best_window = max(
                results,
                key=lambda result: result["net_profit"],
                default=None
            )

            report = {
                "total_windows": len(results),

                "failed_windows": len(failed_windows),

                "average_profit": round(average_profit, 2),

                "average_win_rate": round(average_win_rate, 2),

                "best_window": best_window,

                "optimization_history": optimization_history,

                "results": results,

                "failures": failed_windows
            }

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            logger.info(
                "Walk-forward analysis completed.",
                extra={
                    "event": "walk_forward_analysis_completed",
                    "total_windows": len(results),
                    "failed_windows": len(failed_windows),
                    "average_profit": report["average_profit"],
                    "average_win_rate": report["average_win_rate"],
                    "duration_ms": duration_ms
                }
            )

            return report

        except Exception:
            logger.exception(
                "Walk-forward analysis failed.",
                extra={
                    "event": "walk_forward_analysis_failed",
                    "symbol_count": len(symbols) if symbols else 0,
                    "duration_ms": round(
                        (time.perf_counter() - start_time) * 1000,
                        2
                    )
                }
            )
            raise


    def execute_walk_forward_window(
        self,
        db,
        train_start,
        train_end,
        test_year,
        symbols: list
    ):
        """
        Optimize strategy parameters on the training period and
        evaluate the optimized strategy on the independent test year.

        Original strategy parameters are restored after execution.
        """

        start_time = time.perf_counter()

        logger.info(
            "Walk-forward window started",
            extra={
                "train_start": train_start,
                "train_end": train_end,
                "test_year": test_year,
                "symbol_count": len(symbols) if isinstance(symbols, list) else 0
            }
        )

        if not isinstance(symbols, list) or not symbols:
            raise ValueError("Symbols must be a non-empty list")

        if not isinstance(test_year, int) or isinstance(test_year, bool):
            raise ValueError("Test year must be an integer")

        if train_start > train_end:
            raise ValueError("Training start cannot be after training end")

        best_parameters = None
        trades = []
        failed_symbols = []

        try:
            # -----------------------------------------
            # 1. Optimize using training period
            # -----------------------------------------

            logger.info(
                "Walk-forward training optimization started",
                extra={
                    "train_start": train_start,
                    "train_end": train_end
                }
            )

            best_parameters = self.walk_forward_optimizer.optimize(
                self,
                db,
                symbols,
                train_start,
                train_end
            )

            if not isinstance(best_parameters, dict):
                raise ValueError("Optimizer returned invalid parameters")

            original_parameters = best_parameters.get("original_parameters")

            if not isinstance(original_parameters, dict):
                raise ValueError(
                    "Optimizer result is missing original_parameters"
                )

            logger.info(
                "Walk-forward optimization completed",
                extra={
                    "test_year": test_year,
                    "best_parameters": {
                        key: value
                        for key, value in best_parameters.items()
                        if key != "original_parameters"
                    }
                }
            )

            # -----------------------------------------
            # 2. Execute only on test year
            # -----------------------------------------

            start_date = date(test_year, 1, 1)
            end_date = date(test_year, 12, 31)

            logger.info(
                "Walk-forward test execution started",
                extra={
                    "test_year": test_year,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )

            for symbol in symbols:
                symbol_start = time.perf_counter()

                try:
                    symbol_trades = self.backtest_engine.execute_trades(
                        db,
                        symbol,
                        start_date,
                        end_date
                    )

                    if not isinstance(symbol_trades, list):
                        raise ValueError(
                            f"Invalid trade result for {symbol}"
                        )

                    trades.extend(symbol_trades)

                    logger.info(
                        "Walk-forward symbol test completed",
                        extra={
                            "symbol": symbol,
                            "trade_count": len(symbol_trades),
                            "duration_seconds": round(
                                time.perf_counter() - symbol_start,
                                4
                            )
                        }
                    )

                except Exception:
                    failed_symbols.append(symbol)

                    logger.exception(
                        "Walk-forward symbol test failed",
                        extra={"symbol": symbol}
                    )

            # -----------------------------------------
            # 3. Calculate test metrics
            # -----------------------------------------

            profits = []

            for trade in trades:
                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError(
                        "Trade contains an invalid profit value"
                    )

                profits.append(float(profit))

            total_trades = len(profits)

            winning_trades = sum(
                1 for profit in profits if profit > 0
            )

            losing_trades = total_trades - winning_trades

            net_profit = sum(profits)

            win_rate = (
                winning_trades * 100 / total_trades
                if total_trades
                else 0
            )

            average_profit = (
                net_profit / total_trades
                if total_trades
                else 0
            )

            best_trade = max(profits) if profits else 0
            worst_trade = min(profits) if profits else 0

            result = {
                "train_start": train_start,
                "train_end": train_end,
                "test_year": test_year,
                "best_parameters": best_parameters,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "net_profit": round(net_profit, 2),
                "average_profit": round(average_profit, 2),
                "best_trade": round(best_trade, 2),
                "worst_trade": round(worst_trade, 2),
                "failed_symbols": failed_symbols,
                "failed_symbol_count": len(failed_symbols)
            }

            logger.info(
                "Walk-forward window completed",
                extra={
                    "test_year": test_year,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": result["win_rate"],
                    "net_profit": result["net_profit"],
                    "failed_symbol_count": len(failed_symbols),
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Walk-forward window failed",
                extra={"test_year": test_year}
            )
            raise

        finally:
            # Always restore original strategy parameters
            if isinstance(best_parameters, dict):
                original_parameters = best_parameters.get(
                    "original_parameters"
                )

                if isinstance(original_parameters, dict):
                    try:
                        self.walk_forward_optimizer.restore_original_parameters(
                            self,
                            original_parameters
                        )

                        logger.info(
                            "Original strategy parameters restored",
                            extra={"test_year": test_year}
                        )

                    except Exception:
                        logger.exception(
                            "Failed to restore original strategy parameters",
                            extra={"test_year": test_year}
                        )


    def monte_carlo_analysis(
        self,
        db,
        symbols,
        simulations=1000
    ):
        """
        Execute historical trades and perform Monte Carlo simulations
        to evaluate portfolio sequence risk.
        """

        start_time = time.perf_counter()

        logger.info(
            "Monte Carlo analysis started",
            extra={
                "symbol_count": len(symbols) if isinstance(symbols, list) else 0,
                "simulations": simulations
            }
        )

        if not isinstance(symbols, list) or not symbols:
            raise ValueError("Symbols must be a non-empty list")

        if (
            not isinstance(simulations, int)
            or isinstance(simulations, bool)
            or simulations <= 0
        ):
            raise ValueError("Simulations must be a positive integer")

        trades = []
        failed_symbols = []

        try:
            # -----------------------------------------
            # 1. Load historical trades
            # -----------------------------------------

            for symbol in symbols:
                symbol_start = time.perf_counter()

                try:
                    symbol_trades = self.backtest_engine.execute_trades(
                        db,
                        symbol
                    )

                    if not isinstance(symbol_trades, list):
                        raise ValueError(
                            f"Invalid trade result for {symbol}"
                        )

                    trades.extend(symbol_trades)

                    logger.info(
                        "Monte Carlo symbol data loaded",
                        extra={
                            "symbol": symbol,
                            "trade_count": len(symbol_trades),
                            "duration_seconds": round(
                                time.perf_counter() - symbol_start,
                                4
                            )
                        }
                    )

                except Exception:
                    failed_symbols.append(symbol)

                    logger.exception(
                        "Monte Carlo symbol data loading failed",
                        extra={"symbol": symbol}
                    )

            if not trades:
                raise ValueError(
                    "No historical trades available for Monte Carlo analysis"
                )

            # -----------------------------------------
            # 2. Run Monte Carlo simulations
            # -----------------------------------------

            logger.info(
                "Monte Carlo simulations started",
                extra={
                    "total_trades": len(trades),
                    "simulations": simulations
                }
            )

            result = self.monte_carlo_engine.simulation_summary(
                trades,
                simulations
            )

            if not isinstance(result, dict):
                raise ValueError(
                    "Monte Carlo engine returned an invalid result"
                )

            # -----------------------------------------
            # 3. Return analysis
            # -----------------------------------------

            result["total_trades"] = len(trades)
            result["simulations"] = simulations
            result["failed_symbols"] = failed_symbols
            result["failed_symbol_count"] = len(failed_symbols)

            logger.info(
                "Monte Carlo analysis completed",
                extra={
                    "total_trades": len(trades),
                    "simulations": simulations,
                    "failed_symbol_count": len(failed_symbols),
                    "duration_seconds": round(
                        time.perf_counter() - start_time,
                        4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Monte Carlo analysis failed")
            raise


    def calculate_expectancy(self, trades):
        """
        Calculate average expected profit or loss per trade.

        Expectancy = (Win Rate × Average Win)
                - (Loss Rate × Average Loss)
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return 0

            profits = []

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                profits.append(float(profit))

            winning_profits = [
                profit for profit in profits if profit > 0
            ]

            losing_profits = [
                profit for profit in profits if profit < 0
            ]

            total_trades = len(profits)

            win_rate = len(winning_profits) / total_trades
            loss_rate = len(losing_profits) / total_trades

            average_win = (
                sum(winning_profits) / len(winning_profits)
                if winning_profits else 0
            )

            average_loss = (
                abs(sum(losing_profits) / len(losing_profits))
                if losing_profits else 0
            )

            expectancy = (
                win_rate * average_win
            ) - (
                loss_rate * average_loss
            )

            result = round(expectancy, 2)

            logger.info(
                "Trade expectancy calculated",
                extra={
                    "total_trades": total_trades,
                    "winning_trades": len(winning_profits),
                    "losing_trades": len(losing_profits),
                    "win_rate": round(win_rate * 100, 2),
                    "expectancy": result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Trade expectancy calculation failed")
            raise


    def calculate_profit_factor(self, trades):
        """
        Calculate profit factor.

        Profit Factor = Gross Profit / Absolute Gross Loss

        Returns None when there are no losing trades.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return 0

            profits = []

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                profits.append(float(profit))

            gross_profit = sum(
                profit for profit in profits if profit > 0
            )

            gross_loss = abs(
                sum(profit for profit in profits if profit < 0)
            )

            profit_factor = (
                round(gross_profit / gross_loss, 2)
                if gross_loss > 0
                else None
            )

            logger.info(
                "Profit factor calculated",
                extra={
                    "total_trades": len(profits),
                    "gross_profit": round(gross_profit, 2),
                    "gross_loss": round(gross_loss, 2),
                    "profit_factor": profit_factor,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return profit_factor

        except Exception:
            logger.exception("Profit factor calculation failed")
            raise


    def calculate_average_trade_values(self, trades):
        """
        Calculate average winning and losing trade values.
        Zero-profit trades are excluded from both calculations.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return {
                    "average_win": 0,
                    "average_loss": 0
                }

            winning_profits = []
            losing_profits = []

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                profit = float(profit)

                if profit > 0:
                    winning_profits.append(profit)

                elif profit < 0:
                    losing_profits.append(profit)

            average_win = (
                sum(winning_profits) / len(winning_profits)
                if winning_profits else 0
            )

            average_loss = (
                abs(sum(losing_profits) / len(losing_profits))
                if losing_profits else 0
            )

            result = {
                "average_win": round(average_win, 2),
                "average_loss": round(average_loss, 2)
            }

            logger.info(
                "Average trade values calculated",
                extra={
                    "total_trades": len(trades),
                    "winning_trades": len(winning_profits),
                    "losing_trades": len(losing_profits),
                    "average_win": result["average_win"],
                    "average_loss": result["average_loss"],
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Average trade values calculation failed")
            raise


    def calculate_reward_risk_ratio(self, trades):
        """
        Calculate reward-to-risk ratio using average winning
        and average losing trade values.
        """

        start_time = time.perf_counter()

        try:
            trade_values = self.calculate_average_trade_values(trades)

            average_win = trade_values["average_win"]
            average_loss = trade_values["average_loss"]

            reward_risk_ratio = (
                round(average_win / average_loss, 2)
                if average_loss > 0
                else None
            )

            logger.info(
                "Reward-risk ratio calculated",
                extra={
                    "average_win": average_win,
                    "average_loss": average_loss,
                    "reward_risk_ratio": reward_risk_ratio,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return reward_risk_ratio

        except Exception:
            logger.exception("Reward-risk ratio calculation failed")
            raise


    def calculate_trade_streaks(self, trades):
        """
        Calculate maximum consecutive winning and losing trades.

        Zero-profit trades break both streaks.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            current_win = 0
            current_loss = 0

            max_win = 0
            max_loss = 0

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                if profit > 0:
                    current_win += 1
                    current_loss = 0

                elif profit < 0:
                    current_loss += 1
                    current_win = 0

                else:
                    current_win = 0
                    current_loss = 0

                max_win = max(max_win, current_win)
                max_loss = max(max_loss, current_loss)

            result = {
                "max_winning_streak": max_win,
                "max_losing_streak": max_loss
            }

            logger.info(
                "Trade streaks calculated",
                extra={
                    "total_trades": len(trades),
                    "max_winning_streak": max_win,
                    "max_losing_streak": max_loss,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Trade streak calculation failed")
            raise
    

    def calculate_trade_distribution(self, trades):
        """
        Categorize trades based on percentage profit or loss.

        Percentage = (Trade Profit / Entry Price) * 100

        Note: This preserves the original distribution methodology.
        """

        start_time = time.perf_counter()

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

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")
                entry_price = trade.get("entry_price")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                if (
                    isinstance(entry_price, bool)
                    or not isinstance(entry_price, (int, float))
                    or not math.isfinite(entry_price)
                    or entry_price <= 0
                ):
                    raise ValueError("Trade contains an invalid entry price")

                risk_percent = (profit / entry_price) * 100

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

            logger.info(
                "Trade distribution calculated",
                extra={
                    "total_trades": len(trades),
                    "distribution": distribution,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return distribution

        except Exception:
            logger.exception("Trade distribution calculation failed")
            raise


    def calculate_risk_metrics(self, trades):
        """
        Calculate win-loss ratio and payoff ratio.

        Win-loss ratio = Number of Wins / Number of Losses

        Payoff ratio = Average Win / Average Loss
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return {
                    "win_loss_ratio": 0,
                    "payoff_ratio": 0
                }

            winning_profits = []
            losing_profits = []

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

                if profit > 0:
                    winning_profits.append(float(profit))

                elif profit < 0:
                    losing_profits.append(float(profit))

            total_wins = len(winning_profits)
            total_losses = len(losing_profits)

            average_win = (
                sum(winning_profits) / total_wins
                if total_wins else 0
            )

            average_loss = (
                abs(sum(losing_profits) / total_losses)
                if total_losses else 0
            )

            win_loss_ratio = (
                round(total_wins / total_losses, 2)
                if total_losses else None
            )

            payoff_ratio = (
                round(average_win / average_loss, 2)
                if average_loss > 0 else None
            )

            result = {
                "win_loss_ratio": win_loss_ratio,
                "payoff_ratio": payoff_ratio
            }

            logger.info(
                "Risk metrics calculated",
                extra={
                    "total_trades": len(trades),
                    "winning_trades": total_wins,
                    "losing_trades": total_losses,
                    "average_win": round(average_win, 2),
                    "average_loss": round(average_loss, 2),
                    "win_loss_ratio": win_loss_ratio,
                    "payoff_ratio": payoff_ratio,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Risk metrics calculation failed")
            raise


    def generate_trade_report(self, trades):
        """
        Generate a consolidated trade performance, risk,
        streak, and distribution report.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            logger.info(
                "Trade report generation started",
                extra={"total_trades": len(trades)}
            )

            # Calculate reusable analytics
            trade_values = self.calculate_average_trade_values(trades)
            streaks = self.calculate_trade_streaks(trades)
            distribution = self.calculate_trade_distribution(trades)
            risk_metrics = self.calculate_risk_metrics(trades)

            winning_trades = sum(
                1 for trade in trades if trade["profit"] > 0
            )

            losing_trades = sum(
                1 for trade in trades if trade["profit"] < 0
            )

            total_trades = len(trades)

            win_rate = (
                winning_trades * 100 / total_trades
                if total_trades else 0
            )

            # Calculate performance metrics
            expectancy = self.calculate_expectancy(trades)
            profit_factor = self.calculate_profit_factor(trades)
            reward_risk_ratio = self.calculate_reward_risk_ratio(trades)

            result = {
                "summary": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "breakeven_trades": (
                        total_trades - winning_trades - losing_trades
                    ),
                    "win_rate": round(win_rate, 2)
                },
                "performance": {
                    "expectancy": expectancy,
                    "profit_factor": profit_factor,
                    "average_win": trade_values["average_win"],
                    "average_loss": trade_values["average_loss"],
                    "reward_risk_ratio": reward_risk_ratio
                },
                "risk": {
                    **risk_metrics,
                    **streaks
                },
                "distribution": distribution
            }

            logger.info(
                "Trade report generated successfully",
                extra={
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": round(win_rate, 2),
                    "expectancy": expectancy,
                    "profit_factor": profit_factor,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Trade report generation failed")
            raise


    def calculate_trade_score(self, trades):
        """
        Calculate strategy performance score out of 100.

        Components:
            Win Rate:       30 points
            Profit Factor:  30 points
            Reward Risk:    20 points
            Expectancy:     20 points
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return 0

            # Validate trades
            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                profit = trade.get("profit")

                if (
                    isinstance(profit, bool)
                    or not isinstance(profit, (int, float))
                    or not math.isfinite(profit)
                ):
                    raise ValueError("Trade contains an invalid profit value")

            # Calculate performance metrics
            expectancy = self.calculate_expectancy(trades)
            profit_factor = self.calculate_profit_factor(trades)
            reward_risk = self.calculate_reward_risk_ratio(trades)

            winning_trades = sum(
                1 for trade in trades if trade["profit"] > 0
            )

            win_rate = winning_trades * 100 / len(trades)

            # Win rate: Maximum 30 points
            win_rate_score = min(win_rate, 30)

            # Profit factor: Maximum 30 points
            profit_factor_score = (
                min(profit_factor * 10, 30)
                if profit_factor is not None
                else 30 if any(trade["profit"] > 0 for trade in trades)
                else 0
            )

            # Reward-risk ratio: Maximum 20 points
            reward_risk_score = (
                min(reward_risk * 10, 20)
                if reward_risk is not None
                else 20 if any(trade["profit"] > 0 for trade in trades)
                else 0
            )

            # Expectancy: 20 points
            expectancy_score = 20 if expectancy > 0 else 0

            score = (
                win_rate_score
                + profit_factor_score
                + reward_risk_score
                + expectancy_score
            )

            result = round(min(score, 100), 2)

            logger.info(
                "Trade score calculated",
                extra={
                    "total_trades": len(trades),
                    "win_rate": round(win_rate, 2),
                    "expectancy": expectancy,
                    "profit_factor": profit_factor,
                    "reward_risk_ratio": reward_risk,
                    "win_rate_score": round(win_rate_score, 2),
                    "profit_factor_score": round(profit_factor_score, 2),
                    "reward_risk_score": round(reward_risk_score, 2),
                    "expectancy_score": expectancy_score,
                    "final_score": result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Trade score calculation failed")
            raise
    

    def strategy_health(self, db, symbols):
        """
        Evaluate strategy health using historical trade analytics.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list")

            logger.info(
                "Strategy health analysis started",
                extra={"symbol_count": len(symbols)}
            )

            analytics = self.trade_analytics(db, symbols)

            if not isinstance(analytics, dict):
                raise ValueError("Trade analytics returned invalid data")

            result = self.strategy_intelligence_engine.strategy_health(
                analytics
            )

            logger.info(
                "Strategy health analysis completed",
                extra={
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy health analysis failed")
            raise


    def strategy_confidence(self, db, symbols):
        """
        Evaluate strategy confidence using historical trade analytics.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list")

            logger.info(
                "Strategy confidence analysis started",
                extra={"symbol_count": len(symbols)}
            )

            analytics = self.trade_analytics(db, symbols)

            if not isinstance(analytics, dict):
                raise ValueError("Trade analytics returned invalid data")

            result = self.strategy_intelligence_engine.strategy_confidence(
                analytics
            )

            logger.info(
                "Strategy confidence analysis completed",
                extra={
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy confidence analysis failed")
            raise


    def market_regime(self, db, symbol):
        """
        Identify the current market regime using closing price
        and the long-term moving average.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError("Symbol must be a non-empty string")

            logger.info(
                "Market regime analysis started",
                extra={"symbol": symbol}
            )

            df = self.backtest_engine.strategy.calculate_moving_averages(
                db,
                symbol
            )

            if df is None or df.empty:
                logger.warning(
                    "Market regime unavailable: no market data",
                    extra={"symbol": symbol}
                )

                return {
                    "market_regime": "Unknown"
                }

            required_columns = ["close", "MA_LONG"]

            missing_columns = [
                column for column in required_columns
                if column not in df.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"Missing market data columns: {missing_columns}"
                )

            latest = df.iloc[-1]

            latest_close = latest["close"]
            long_ma = latest["MA_LONG"]

            if (
                pd.isna(latest_close)
                or pd.isna(long_ma)
                or not math.isfinite(float(latest_close))
                or not math.isfinite(float(long_ma))
            ):
                logger.warning(
                    "Market regime unavailable: invalid moving average data",
                    extra={"symbol": symbol}
                )

                return {
                    "market_regime": "Unknown"
                }

            result = self.strategy_intelligence_engine.market_regime(
                latest_close=latest_close,
                long_ma=long_ma
            )

            if not isinstance(result, dict):
                raise ValueError("Market regime engine returned invalid data")

            logger.info(
                "Market regime analysis completed",
                extra={
                    "symbol": symbol,
                    "latest_close": float(latest_close),
                    "long_ma": float(long_ma),
                    "market_regime": result.get("market_regime"),
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Market regime analysis failed",
                extra={"symbol": symbol}
            )
            raise


    def strategy_recommendation(self, db, symbol, symbols):
        """
        Generate a strategy recommendation using strategy health,
        confidence, and current market regime.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list")

            logger.info(
                "Strategy recommendation started",
                extra={
                    "symbol": symbol,
                    "symbol_count": len(symbols)
                }
            )

            analytics = self.trade_analytics(db, symbols)

            if not isinstance(analytics, dict):
                raise ValueError("Trade analytics returned invalid data")

            health = self.strategy_intelligence_engine.strategy_health(
                analytics
            )

            confidence = self.strategy_intelligence_engine.strategy_confidence(
                analytics
            )

            regime = self.market_regime(db, symbol)

            market_regime_value = regime.get("market_regime", "Unknown")

            result = self.strategy_intelligence_engine.strategy_recommendation(
                health,
                confidence,
                market_regime_value
            )

            logger.info(
                "Strategy recommendation completed",
                extra={
                    "symbol": symbol,
                    "market_regime": market_regime_value,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Strategy recommendation failed",
                extra={"symbol": symbol}
            )
            raise


    def risk_recommendation(self, db, symbols):
        """
        Generate risk recommendations using strategy health
        and confidence analytics.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list")

            logger.info(
                "Risk recommendation started",
                extra={"symbol_count": len(symbols)}
            )

            analytics = self.trade_analytics(db, symbols)

            if not isinstance(analytics, dict):
                raise ValueError("Trade analytics returned invalid data")

            health = self.strategy_intelligence_engine.strategy_health(
                analytics
            )

            confidence = self.strategy_intelligence_engine.strategy_confidence(
                analytics
            )

            result = self.strategy_intelligence_engine.risk_recommendation(
                health,
                confidence
            )

            logger.info(
                "Risk recommendation completed",
                extra={
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Risk recommendation failed")
            raise


    def strategy_summary(self, db, symbol, symbols):
        """
        Generate a complete strategy summary containing:
        health, confidence, market regime, strategy recommendation,
        and risk recommendation.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(symbols, list) or not symbols:
                raise ValueError("Symbols must be a non-empty list")

            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError("Symbol must be a non-empty string")

            logger.info(
                "Strategy summary generation started",
                extra={
                    "symbol": symbol,
                    "symbol_count": len(symbols)
                }
            )

            # Calculate analytics only once
            analytics = self.trade_analytics(db, symbols)

            if not isinstance(analytics, dict):
                raise ValueError("Trade analytics returned invalid data")

            health = self.strategy_intelligence_engine.strategy_health(
                analytics
            )

            confidence = self.strategy_intelligence_engine.strategy_confidence(
                analytics
            )

            regime = self.market_regime(db, symbol)

            recommendation = (
                self.strategy_intelligence_engine.strategy_recommendation(
                    health,
                    confidence,
                    regime.get("market_regime", "Unknown")
                )
            )

            risk = self.strategy_intelligence_engine.risk_recommendation(
                health,
                confidence
            )

            result = self.strategy_intelligence_engine.strategy_summary(
                health,
                confidence,
                regime,
                recommendation,
                risk
            )

            logger.info(
                "Strategy summary generated successfully",
                extra={
                    "symbol": symbol,
                    "market_regime": regime.get("market_regime"),
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Strategy summary generation failed",
                extra={"symbol": symbol}
            )
            raise


    def strategy_intelligence(self, db, symbol, symbols):
        """
        Generate the complete strategy intelligence report.
        """

        start_time = time.perf_counter()

        try:
            logger.info(
                "Strategy intelligence generation started",
                extra={"symbol": symbol}
            )

            summary = self.strategy_summary(
                db,
                symbol,
                symbols
            )

            result = self.strategy_intelligence_engine.strategy_intelligence(
                summary
            )

            logger.info(
                "Strategy intelligence generated successfully",
                extra={
                    "symbol": symbol,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception(
                "Strategy intelligence generation failed",
                extra={"symbol": symbol}
            )
            raise


    def rank_daily_trades(self, trades: list):
        """
        Group trades by entry date and rank each day's trades
        by total_score in descending order.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(trades, list):
                raise ValueError("Trades must be a list")

            if not trades:
                return []

            grouped = defaultdict(list)

            # -----------------------------------------
            # 1. Group trades by entry date
            # -----------------------------------------

            for trade in trades:
                if not isinstance(trade, dict):
                    raise ValueError("Each trade must be a dictionary")

                entry_date = trade.get("entry_date")

                if entry_date is None:
                    raise ValueError("Trade is missing entry_date")

                score = trade.get("total_score", 0)

                if (
                    isinstance(score, bool)
                    or not isinstance(score, (int, float))
                    or not math.isfinite(score)
                ):
                    raise ValueError("Trade contains an invalid total_score")

                grouped[entry_date].append(trade)

            # -----------------------------------------
            # 2. Rank each day separately
            # -----------------------------------------

            ranked = []

            for entry_date in sorted(grouped.keys()):
                today = grouped[entry_date]

                today.sort(
                    key=lambda trade: trade.get("total_score", 0),
                    reverse=True
                )

                ranked.extend(today)

            logger.info(
                "Daily trades ranked successfully",
                extra={
                    "total_trades": len(trades),
                    "trading_days": len(grouped),
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return ranked

        except Exception:
            logger.exception("Daily trade ranking failed")
            raise
