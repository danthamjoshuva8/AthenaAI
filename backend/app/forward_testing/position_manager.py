
import logging
from datetime import date
from typing import Any

from app.config.backtest_config import ExitStrategyType
from app.backtesting.exits.strategy_factory import ExitStrategyFactory


logger = logging.getLogger(__name__)


class ForwardTestingPositionManager:
    """
    Manages open paper positions and evaluates exit conditions.

    Reuses AthenaAI's existing exit strategies through
    ExitStrategyFactory.

    Responsibilities:
        - Initialize positions from executed paper orders.
        - Calculate 2R and 3R targets.
        - Monitor initial stop-loss.
        - Process existing exit strategy decisions.
        - Update remaining quantity after partial exits.
        - Calculate realized and unrealized P&L.
        - Track open and closed positions.

    This manager does not submit broker orders or persist positions.
    """

    def __init__(
        self,
        exit_strategy: ExitStrategyType,
    ):
        self.exit_strategy_type = exit_strategy
        self.exit_strategy = ExitStrategyFactory.create(
            exit_strategy
        )

    def initialize_positions(
        self,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Initialize positions from successfully executed paper orders.

        Expected input:
            execution_result["orders"]

        Required executed order fields:
            symbol, quantity, execution_price, stop_loss,
            execution_date
        """

        positions = []
        rejected = []

        orders = execution_result.get("orders", [])

        for order in orders:

            if order.get("status") != "EXECUTED":
                continue

            symbol = str(order.get("symbol", "")).upper()

            try:
                quantity = int(order["quantity"])
                entry_price = float(order["execution_price"])
                stop_loss = float(order["stop_loss"])
                entry_date = order["execution_date"]

                if quantity <= 0:
                    raise ValueError("Invalid executed quantity.")

                if entry_price <= 0 or stop_loss <= 0:
                    raise ValueError("Invalid entry or stop-loss price.")

                if stop_loss >= entry_price:
                    raise ValueError(
                        "Stop loss must be below actual execution price."
                    )

                initial_risk = entry_price - stop_loss

                position = {
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "quantity": quantity,
                    "remaining_quantity": quantity,
                    "stop_loss": stop_loss,
                    "initial_stop_loss": stop_loss,
                    "initial_risk": initial_risk,
                    "target_2r": round(
                        entry_price + (initial_risk * 2), 2
                    ),
                    "target_3r": round(
                        entry_price + (initial_risk * 3), 2
                    ),
                    "partial_exit_2r": False,
                    "partial_exit_3r": False,
                    "trail_active": False,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "status": "OPEN",
                    "exit_strategy": self.exit_strategy_type.value,
                }

                positions.append(position)

                logger.info(
                    "Forward-testing position initialized",
                    extra={
                        "event": "forward_position_initialized",
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "stop_loss": stop_loss,
                        "target_2r": position["target_2r"],
                        "target_3r": position["target_3r"],
                    },
                )

            except (KeyError, TypeError, ValueError) as exc:

                rejected.append({
                    "symbol": symbol or "UNKNOWN",
                    "reason": str(exc),
                })

                logger.exception(
                    "Forward-testing position initialization failed",
                    extra={
                        "event": "forward_position_initialization_failed",
                        "symbol": symbol or "UNKNOWN",
                    },
                )

        return {
            "status": "SUCCESS",
            "initialized_count": len(positions),
            "rejected_count": len(rejected),
            "positions": positions,
            "rejected": rejected,
        }

    @staticmethod
    def _calculate_realized_pnl(
        entry_price: float,
        exit_price: float,
        quantity: int,
    ) -> float:
        """Calculate realized P&L for a paper sell."""

        return round(
            (exit_price - entry_price) * quantity,
            2,
        )

    def _apply_exit_decision(
        self,
        position: dict[str, Any],
        decision: dict[str, Any],
        market_date: date,
    ) -> dict[str, Any]:
        """
        Apply the exit decision returned by an existing strategy.

        Existing strategies return decisions but do not consistently
        decrement remaining_quantity. This method handles that state.
        """

        sell_quantity = int(decision["sell_quantity"])
        remaining_quantity = int(position["remaining_quantity"])
        exit_price = float(decision["exit_price"])

        if sell_quantity <= 0:
            raise ValueError("Exit quantity must be greater than zero.")

        if sell_quantity > remaining_quantity:
            raise ValueError(
                "Exit quantity cannot exceed remaining position quantity."
            )

        if exit_price <= 0:
            raise ValueError("Exit price must be greater than zero.")

        realized_pnl = self._calculate_realized_pnl(
            entry_price=position["entry_price"],
            exit_price=exit_price,
            quantity=sell_quantity,
        )

        position["remaining_quantity"] -= sell_quantity
        position["realized_pnl"] = round(
            position["realized_pnl"] + realized_pnl,
            2,
        )

        if position["remaining_quantity"] == 0:
            position["status"] = "CLOSED"
            position["exit_date"] = market_date.isoformat()
            position["final_exit_reason"] = decision["exit_reason"]
        else:
            position["status"] = "OPEN"

        event = {
            "symbol": position["symbol"],
            "exit_date": market_date.isoformat(),
            "action": decision["action"],
            "sell_quantity": sell_quantity,
            "remaining_quantity": position["remaining_quantity"],
            "exit_price": exit_price,
            "exit_reason": decision["exit_reason"],
            "realized_pnl": realized_pnl,
            "cumulative_realized_pnl": position["realized_pnl"],
            "status": position["status"],
        }

        logger.info(
            "Forward-testing exit processed",
            extra={
                "event": "forward_position_exit_processed",
                **event,
            },
        )

        return event

    def _check_initial_stop_loss(
        self,
        position: dict[str, Any],
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Check the original stop-loss before evaluating the strategy.

        Conservative daily OHLC assumption:
            - If the market opens below the stop, use the open.
            - Otherwise, if the low reaches the stop, use the stop.

        This avoids assuming a favorable intraday price when
        candle data cannot establish the exact price sequence.
        """

        stop_loss = float(position["stop_loss"])
        opening_price = float(row["open"])
        low_price = float(row["low"])

        if opening_price <= stop_loss:
            exit_price = opening_price
        elif low_price <= stop_loss:
            exit_price = stop_loss
        else:
            return None

        return {
            "close_position": True,
            "action": "CLOSE",
            "sell_quantity": position["remaining_quantity"],
            "exit_price": exit_price,
            "exit_reason": "STOP_LOSS",
        }

    def process_positions(
        self,
        positions: list[dict[str, Any]],
        market_data_by_symbol: dict[str, dict[str, Any]],
        market_date: date,
    ) -> dict[str, Any]:
        """
        Evaluate all open positions against completed daily market candles.

        Expected market data:
            {
                "RELIANCE": {
                    "open": 1450.0,
                    "high": 1470.0,
                    "low": 1440.0,
                    "close": 1460.0,
                    "signal": "HOLD"
                }
            }

        The signal must be generated from the same completed candle.
        """

        open_positions = []
        closed_positions = []
        exit_events = []
        skipped_positions = []

        for original_position in positions:

            if original_position.get("status") != "OPEN":
                if original_position.get("status") == "CLOSED":
                    closed_positions.append(original_position)
                continue

            # Preserve position state while evaluating the strategy.
            position = original_position.copy()

            symbol = str(
                position.get("symbol", "")
            ).upper()

            row = market_data_by_symbol.get(symbol)

            if row is None:
                open_positions.append(position)

                skipped_positions.append({
                    "symbol": symbol,
                    "reason": "Market data unavailable",
                })
                continue

            try:
                required_fields = ("open", "high", "low", "close")

                if any(field not in row for field in required_fields):
                    raise ValueError(
                        "Market candle is missing required OHLC fields."
                    )

                opening_price = float(row["open"])
                high_price = float(row["high"])
                low_price = float(row["low"])
                close_price = float(row["close"])

                if (
                    min(
                        opening_price,
                        high_price,
                        low_price,
                        close_price,
                    ) <= 0
                    or high_price < low_price
                ):
                    raise ValueError("Invalid market OHLC values.")

                strategy_row = {
                    **row,
                    "open": opening_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "signal": row.get("signal", "HOLD"),
                }

                # Step 1: Check initial or active stop-loss.
                decision = self._check_initial_stop_loss(
                    position,
                    strategy_row,
                )

                # Step 2: If the stop was not reached, evaluate
                # the selected existing exit strategy.
                if decision is None:
                    decision = self.exit_strategy.process(
                        position,
                        strategy_row,
                    )

                # Step 3: Apply the returned exit decision.
                if decision is not None:

                    event = self._apply_exit_decision(
                        position=position,
                        decision=decision,
                        market_date=market_date,
                    )

                    exit_events.append(event)

                # Step 4: Update unrealized P&L.
                position["unrealized_pnl"] = round(
                    (
                        close_price - position["entry_price"]
                    ) * position["remaining_quantity"],
                    2,
                )

                position["last_updated_date"] = (
                    market_date.isoformat()
                )

                if position["status"] == "CLOSED":
                    closed_positions.append(position)
                else:
                    open_positions.append(position)

            except Exception as exc:

                logger.exception(
                    "Forward-testing position processing failed",
                    extra={
                        "event": "forward_position_processing_failed",
                        "symbol": symbol,
                        "market_date": market_date.isoformat(),
                    },
                )

                # Preserve the position when processing fails.
                open_positions.append(original_position)

                skipped_positions.append({
                    "symbol": symbol,
                    "reason": str(exc),
                })

        total_realized_pnl = round(
            sum(
                position.get("realized_pnl", 0.0)
                for position in open_positions + closed_positions
            ),
            2,
        )

        total_unrealized_pnl = round(
            sum(
                position.get("unrealized_pnl", 0.0)
                for position in open_positions
            ),
            2,
        )

        return {
            "status": "SUCCESS",
            "market_date": market_date.isoformat(),
            "positions_processed": (
                len(open_positions) + len(closed_positions)
            ),
            "open_positions_count": len(open_positions),
            "closed_positions_count": len(closed_positions),
            "exit_events_count": len(exit_events),
            "total_realized_pnl": total_realized_pnl,
            "total_unrealized_pnl": total_unrealized_pnl,
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "exit_events": exit_events,
            "skipped_positions": skipped_positions,
        }
