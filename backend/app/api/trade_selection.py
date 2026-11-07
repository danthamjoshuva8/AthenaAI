
import logging
from time import perf_counter
from typing import Any, Callable

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.trade_selection_service import TradeSelectionService


router = APIRouter(
    tags=["Trade Selection"]
)

service = TradeSelectionService()
logger = logging.getLogger(__name__)


def run_trade_selection_operation(
    operation: str,
    func: Callable[[], Any],
    **context: Any,
) -> Any:
    """
    Executes a trade selection operation with structured logging.

    Logs operation start, completion, duration, and failures.
    Request ID is automatically added by the global JSON logger.
    """

    start_time = perf_counter()

    logger.info(
        f"Trade selection operation started: {operation}",
        extra={
            "event": "trade_selection_operation_started",
            "service": "trade_selection",
            "operation": operation,
            **context,
        },
    )

    try:
        result = func()

        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            f"Trade selection operation completed: {operation}",
            extra={
                "event": "trade_selection_operation_completed",
                "service": "trade_selection",
                "operation": operation,
                "status": "success",
                "duration_ms": duration_ms,
                **context,
            },
        )

        return result

    except Exception:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            f"Trade selection operation failed: {operation}",
            extra={
                "event": "trade_selection_operation_failed",
                "service": "trade_selection",
                "operation": operation,
                "status": "failed",
                "duration_ms": duration_ms,
                **context,
            },
        )

        raise


@router.get(
    "/scan",
    operation_id="scan_market_for_trade_opportunities",
    summary="Scan Market for Trade Opportunities",
    description="Scans the market and identifies potential trading opportunities.",
)
def scan_market(
    db: Session = Depends(get_db),
):
    """
    Scans the market using the Trade Selection Engine.
    """

    return run_trade_selection_operation(
        operation="scan_market",
        func=lambda: service.scan_market(db),
    )
