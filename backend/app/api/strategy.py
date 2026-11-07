
import logging
from time import perf_counter
from typing import Any, Callable

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.strategy_service import StrategyService


router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"]
)

service = StrategyService()
logger = logging.getLogger(__name__)


def run_strategy_operation(
    operation: str,
    func: Callable[[], Any],
    **context: Any,
) -> Any:
    """
    Executes a strategy operation with structured logging.

    Logs operation start, completion, execution duration,
    and exceptions. Request ID is added by the global JSON logger.
    """

    start_time = perf_counter()

    logger.info(
        f"Strategy operation started: {operation}",
        extra={
            "event": "strategy_operation_started",
            "service": "strategy",
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
            f"Strategy operation completed: {operation}",
            extra={
                "event": "strategy_operation_completed",
                "service": "strategy",
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
            f"Strategy operation failed: {operation}",
            extra={
                "event": "strategy_operation_failed",
                "service": "strategy",
                "operation": operation,
                "status": "failed",
                "duration_ms": duration_ms,
                **context,
            },
        )

        raise


@router.get(
    "/load/{symbol}",
    summary="Load Stock Market Data",
    description="Loads historical market data for a stock from the database.",
)
def load_market_data(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Load market data required for strategy calculations."""

    def execute():
        data = service.load_data(db, symbol)

        return {
            "rows": len(data),
            "symbol": symbol,
        }

    return run_strategy_operation(
        operation="load_market_data",
        func=execute,
        symbol=symbol,
    )


@router.get(
    "/ma/{symbol}",
    summary="Calculate Moving Averages",
    description="Calculates moving averages and returns the latest 20 records.",
)
def moving_average(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Calculate moving averages for a stock."""

    def execute():
        df = service.calculate_ma(db, symbol)

        logger.info(
            "Moving averages calculated",
            extra={
                "event": "moving_averages_calculated",
                "service": "strategy",
                "symbol": symbol,
                "row_count": len(df),
            },
        )

        return df.tail(20).to_dict(
            orient="records"
        )

    return run_strategy_operation(
        operation="calculate_moving_averages",
        func=execute,
        symbol=symbol,
    )


@router.get(
    "/signals/{symbol}",
    summary="Generate Strategy Signals",
    description="Generates trading signals for a stock using the configured strategy.",
)
def strategy_signals(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Generate trading signals for a stock."""

    return run_strategy_operation(
        operation="generate_strategy_signals",
        func=lambda: service.generate_signals(db, symbol),
        symbol=symbol,
    )


@router.get(
    "/latest/{symbol}",
    summary="Get Latest Strategy Signal",
    description="Retrieves the latest trading signal for a stock.",
)
def latest_signal(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Retrieve the latest strategy signal."""

    return run_strategy_operation(
        operation="get_latest_signal",
        func=lambda: service.latest_signal(db, symbol),
        symbol=symbol,
    )


@router.get(
    "/buy/{symbol}",
    summary="Get Buy Signals",
    description="Retrieves buy signals generated for a stock.",
)
def buy_signals(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Retrieve buy signals for a stock."""

    return run_strategy_operation(
        operation="get_buy_signals",
        func=lambda: service.buy_signals(db, symbol),
        symbol=symbol,
    )


@router.get(
    "/sell/{symbol}",
    summary="Get Sell Signals",
    description="Retrieves sell signals generated for a stock.",
)
def sell_signals(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Retrieve sell signals for a stock."""

    return run_strategy_operation(
        operation="get_sell_signals",
        func=lambda: service.sell_signals(db, symbol),
        symbol=symbol,
    )
