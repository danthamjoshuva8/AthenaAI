
from datetime import date, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.forward_testing.storage import (
    PaperOrder,
    PaperPosition,
    PaperPositionEvent,
)
from datetime import datetime

from app.forward_testing.storage import ForwardTestingRun
from sqlalchemy.exc import IntegrityError


logger = logging.getLogger(__name__)


class ForwardTestingStorageService:
    """
    Persists AthenaAI forward-testing orders, positions and exit events.

    Uses the existing SQLAlchemy database session.
    """

    @staticmethod
    def _to_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            return date.fromisoformat(value[:10])

        raise ValueError(f"Invalid date value: {value}")

    @staticmethod
    def _position_to_dict(position: PaperPosition) -> dict:
        """Convert a database position into the manager's input format."""

        return {
            "_storage_id": position.id,
            "symbol": position.symbol,
            "entry_date": position.entry_date.isoformat(),
            "entry_price": position.entry_price,
            "quantity": position.quantity,
            "remaining_quantity": position.remaining_quantity,
            "stop_loss": position.stop_loss,
            "initial_stop_loss": position.initial_stop_loss,
            "initial_risk": position.initial_risk,
            "target_2r": position.target_2r,
            "target_3r": position.target_3r,
            "partial_exit_2r": position.partial_exit_2r,
            "partial_exit_3r": position.partial_exit_3r,
            "trail_active": position.trail_active,
            "realized_pnl": position.realized_pnl,
            "unrealized_pnl": position.unrealized_pnl,
            "status": position.status,
            "exit_strategy": position.exit_strategy,
            "last_updated_date": (
                position.last_updated_date.isoformat()
                if position.last_updated_date else None
            ),
            "exit_date": (
                position.exit_date.isoformat()
                if position.exit_date else None
            ),
            "final_exit_reason": position.final_exit_reason,
        }

    def save_execution_and_positions(
        self,
        db: Session,
        execution_result: dict,
        initialization_result: dict,
        run_id: int,
    ) -> dict:
        """
        Save paper orders and positions initialized from executed orders.

        Every order is associated with a valid RUNNING daily run.
        Prevents duplicate order persistence for the same daily run.
        Returns database position IDs alongside initialized positions.
        """

        order_ids_by_symbol = {}
        saved_orders = 0
        saved_positions = 0

        try:
            # Step 0: Validate and lock the daily run.
            run = (
                db.query(ForwardTestingRun)
                .filter(ForwardTestingRun.id == run_id)
                .with_for_update()
                .first()
            )

            if run is None:
                raise ValueError(
                    f"Forward testing run {run_id} not found"
                )

            if run.status != "RUNNING":
                raise ValueError(
                    f"Cannot save orders for run {run_id} "
                    f"with status {run.status}"
                )

            # Step 0.1: Prevent duplicate order persistence.
            existing_orders = (
                db.query(PaperOrder)
                .filter(PaperOrder.run_id == run_id)
                .count()
            )

            if existing_orders > 0:
                raise ValueError(
                    f"Orders already saved for forward-testing run {run_id}. "
                    "Duplicate execution is not allowed."
                )

            # Step 1: Save all paper orders.
            for order in execution_result.get("orders", []):

                symbol = order.get("symbol", "UNKNOWN").upper()
                order_status = order["status"].upper()

                order_date = self._to_date(
                    order["execution_date"]
                )

                paper_order = PaperOrder(
                    run_id=run_id,
                    symbol=symbol,
                    order_type=order.get("order_type", "BUY"),
                    status=order_status,
                    execution_date=order_date,
                    quantity=order.get("quantity"),
                    signal_entry_price=order.get("signal_entry_price"),
                    execution_price=order.get("execution_price"),
                    stop_loss=order.get("stop_loss"),
                    gross_value=order.get("gross_value"),
                    brokerage=order.get("brokerage"),
                    total_cost=order.get("total_cost"),
                    slippage_bps=order.get("slippage_bps"),
                    risk_amount=order.get("risk_amount"),
                    reason=order.get("reason"),
                )

                db.add(paper_order)
                db.flush()

                saved_orders += 1

                if order_status == "EXECUTED":
                    order_ids_by_symbol.setdefault(
                        symbol, []
                    ).append(paper_order.id)

            # Step 2: Save positions created from executed orders.
            persisted_positions = []

            for position in initialization_result.get("positions", []):

                symbol = position["symbol"].upper()

                # Match each position to its corresponding executed order.
                matching_order_ids = order_ids_by_symbol.get(symbol, [])

                order_id = (
                    matching_order_ids.pop(0)
                    if matching_order_ids
                    else None
                )

                paper_position = PaperPosition(
                    order_id=order_id,
                    symbol=symbol,
                    entry_date=self._to_date(position["entry_date"]),
                    entry_price=position["entry_price"],
                    quantity=position["quantity"],
                    remaining_quantity=position["remaining_quantity"],
                    stop_loss=position["stop_loss"],
                    initial_stop_loss=position["initial_stop_loss"],
                    initial_risk=position["initial_risk"],
                    target_2r=position.get("target_2r"),
                    target_3r=position.get("target_3r"),
                    partial_exit_2r=position.get("partial_exit_2r", False),
                    partial_exit_3r=position.get("partial_exit_3r", False),
                    trail_active=position.get("trail_active", False),
                    realized_pnl=position.get("realized_pnl", 0.0),
                    unrealized_pnl=position.get("unrealized_pnl", 0.0),
                    status=position.get("status", "OPEN"),
                    exit_strategy=position["exit_strategy"],
                )

                db.add(paper_position)
                db.flush()

                saved_positions += 1

                position_copy = dict(position)
                position_copy["_storage_id"] = paper_position.id
                persisted_positions.append(position_copy)

            logger.info(
                "Forward-testing execution and positions saved",
                extra={
                    "event": "forward_testing_storage_saved",
                    "run_id": run_id,
                    "orders_saved": saved_orders,
                    "positions_saved": saved_positions,
                },
            )

            return {
                "status": "SUCCESS",
                "run_id": run_id,
                "orders_saved": saved_orders,
                "positions_saved": saved_positions,
                "positions": persisted_positions,
            }

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to save forward-testing execution and positions",
                extra={
                    "event": "forward_testing_storage_failed",
                    "run_id": run_id,
                },
            )
            raise

    def get_open_positions(self, db: Session) -> list[dict]:
        """Retrieve open positions for the next monitoring cycle."""

        positions = (
            db.query(PaperPosition)
            .filter(PaperPosition.status == "OPEN")
            .order_by(PaperPosition.id.asc())
            .all()
        )

        return [
            self._position_to_dict(position)
            for position in positions
        ]

    def update_position_results(
        self,
        db: Session,
        position_result: dict,
    ) -> dict:
        """
        Update persisted positions and save new exit events.

        Position dictionaries must contain _storage_id.
        The position manager preserves this field when updating
        positions retrieved through get_open_positions().
        """

        updated_count = 0
        event_count = 0

        try:
            all_positions = (
                position_result.get("open_positions", [])
                + position_result.get("closed_positions", [])
            )

            for position in all_positions:

                storage_id = position.get("_storage_id")

                if storage_id is None:
                    raise ValueError(
                        f"Missing _storage_id for {position.get('symbol')}"
                    )

                db_position = (
                    db.query(PaperPosition)
                    .filter(PaperPosition.id == storage_id)
                    .with_for_update()
                    .first()
                )

                if db_position is None:
                    raise ValueError(
                        f"Position ID {storage_id} does not exist."
                    )

                db_position.remaining_quantity = position[
                    "remaining_quantity"
                ]
                db_position.stop_loss = position["stop_loss"]
                db_position.partial_exit_2r = position.get(
                    "partial_exit_2r", False
                )
                db_position.partial_exit_3r = position.get(
                    "partial_exit_3r", False
                )
                db_position.trail_active = position.get(
                    "trail_active", False
                )
                db_position.realized_pnl = position.get(
                    "realized_pnl", 0.0
                )
                db_position.unrealized_pnl = position.get(
                    "unrealized_pnl", 0.0
                )
                db_position.status = position["status"]

                if position.get("last_updated_date"):
                    db_position.last_updated_date = self._to_date(
                        position["last_updated_date"]
                    )

                if position.get("exit_date"):
                    db_position.exit_date = self._to_date(
                        position["exit_date"]
                    )

                db_position.final_exit_reason = position.get(
                    "final_exit_reason"
                )

                updated_count += 1

            # Save every newly generated exit event.
            for event in position_result.get("exit_events", []):

                symbol = event["symbol"].upper()

                matching_position = next(
                    (
                        position
                        for position in all_positions
                        if position["symbol"].upper() == symbol
                    ),
                    None,
                )

                if matching_position is None:
                    raise ValueError(
                        f"Cannot find position for exit event: {symbol}"
                    )

                db_event = PaperPositionEvent(
                    position_id=matching_position["_storage_id"],
                    event_date=self._to_date(event["exit_date"]),
                    action=event["action"],
                    sell_quantity=event["sell_quantity"],
                    remaining_quantity=event["remaining_quantity"],
                    exit_price=event["exit_price"],
                    exit_reason=event["exit_reason"],
                    realized_pnl=event["realized_pnl"],
                    cumulative_realized_pnl=event[
                        "cumulative_realized_pnl"
                    ],
                    details=event,
                )

                db.add(db_event)
                event_count += 1

            db.commit()

            logger.info(
                "Forward-testing positions updated",
                extra={
                    "event": "forward_testing_positions_updated",
                    "positions_updated": updated_count,
                    "exit_events_saved": event_count,
                },
            )

            return {
                "status": "SUCCESS",
                "positions_updated": updated_count,
                "exit_events_saved": event_count,
            }

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to update forward-testing positions",
                extra={
                    "event": "forward_testing_position_update_failed",
                },
            )
            raise

    
    def start_daily_run(
        self,
        db: Session,
        signal_date: date,
        execution_date: date,
    ) -> dict:
        """
        Create one daily run per signal/execution date pair.

        Existing RUNNING, SUCCESS and FAILED runs are never
        automatically restarted. This prevents duplicate execution
        when a previous run may have partially persisted results.

        The unique run_key constraint protects against concurrent
        requests attempting to create the same run.
        """

        run_key = f"{signal_date.isoformat()}_{execution_date.isoformat()}"

        # First check whether this daily run already exists.
        existing_run = (
            db.query(ForwardTestingRun)
            .filter(ForwardTestingRun.run_key == run_key)
            .first()
        )

        if existing_run:
            return {
                "created": False,
                "run_id": existing_run.id,
                "run_key": run_key,
                "status": existing_run.status,
                "result": existing_run.result,
                "message": "Daily run already exists. Automatic re-execution blocked.",
            }

        # Attempt to create a new run.
        run = ForwardTestingRun(
            run_key=run_key,
            signal_date=signal_date,
            execution_date=execution_date,
            status="RUNNING",
        )

        try:
            db.add(run)
            db.commit()
            db.refresh(run)

            return {
                "created": True,
                "run_id": run.id,
                "run_key": run_key,
                "status": "RUNNING",
                "result": None,
                "message": "New daily run created.",
            }

        except IntegrityError:
            # Another request may have inserted the same run_key
            # between our initial lookup and INSERT.
            db.rollback()

            existing_run = (
                db.query(ForwardTestingRun)
                .filter(ForwardTestingRun.run_key == run_key)
                .first()
            )

            if existing_run is None:
                raise

            return {
                "created": False,
                "run_id": existing_run.id,
                "run_key": run_key,
                "status": existing_run.status,
                "result": existing_run.result,
                "message": "Concurrent daily run detected. Duplicate execution blocked.",
            }

        except Exception:
            db.rollback()
            raise

    
    
    
    def complete_daily_run(
        self,
        db: Session,
        run_id: int,
        result: dict,
        commit: bool = True,
    ) -> None:
        try:
            run = (
                db.query(ForwardTestingRun)
                .filter(ForwardTestingRun.id == run_id)
                .with_for_update()
                .first()
            )

            if run is None:
                raise ValueError(
                    f"Forward testing run {run_id} not found"
                )

            if run.status != "RUNNING":
                raise ValueError(
                    f"Cannot complete run {run_id}: "
                    f"current status is {run.status}"
                )

            run.status = "SUCCESS"
            run.result = result
            run.error_message = None
            run.completed_at = datetime.utcnow()

            if commit:
                db.commit()

        except Exception:
            db.rollback()
            raise
        
    def fail_daily_run(
        self,
        db: Session,
        run_id: int,
        error_message: str,
    ) -> None:
        try:
            run = (
                db.query(ForwardTestingRun)
                .filter(ForwardTestingRun.id == run_id)
                .with_for_update()
                .first()
            )

            if run is None:
                raise ValueError(
                    f"Forward testing run {run_id} not found"
                )

            if run.status != "RUNNING":
                raise ValueError(
                    f"Cannot fail run {run_id}: "
                    f"current status is {run.status}"
                )

            run.status = "FAILED"
            run.error_message = error_message
            run.completed_at = datetime.utcnow()

            db.commit()

        except Exception:
            db.rollback()
            raise

