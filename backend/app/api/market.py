
import logging
from datetime import date as Date
from time import perf_counter
from typing import Any, Callable

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.sector import Sector
from app.schemas.market_data import HistoryLoadRequest
from app.services.market_service import MarketService
from app.market.symbol_provider import load_nifty200_symbols


router = APIRouter(
    prefix="/market",
    tags=["Market Data"]
)

service = MarketService()
logger = logging.getLogger(__name__)


def run_market_operation(
    operation: str,
    func: Callable[[], Any],
    **context: Any,
) -> Any:
    """
    Executes a market data operation with structured logging.

    Logs:
    - Operation started
    - Operation completed
    - Execution duration
    - Operation failure and exception details

    Request ID is automatically added by the existing JSON logger.
    """

    start_time = perf_counter()

    logger.info(
        f"Market operation started: {operation}",
        extra={
            "event": "market_operation_started",
            "service": "market_data",
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
            f"Market operation completed: {operation}",
            extra={
                "event": "market_operation_completed",
                "service": "market_data",
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
            f"Market operation failed: {operation}",
            extra={
                "event": "market_operation_failed",
                "service": "market_data",
                "operation": operation,
                "status": "failed",
                "duration_ms": duration_ms,
                **context,
            },
        )

        raise


@router.get(
    "/ping",
    summary="Check Market Data Service",
    description="Checks whether the market data service is responding.",
)
def ping():
    """Check market data service availability."""

    return run_market_operation(
        operation="ping",
        func=lambda: service.ping(),
    )


@router.get(
    "/download/{symbol}",
    summary="Download Market Data",
    description="Downloads historical market data for a stock symbol.",
)
def download(symbol: str):
    """Download market data for a stock."""

    return run_market_operation(
        operation="download_market_data",
        func=lambda: service.download(symbol),
        symbol=symbol,
    )


@router.post(
    "/save/{symbol}",
    summary="Save Market Data",
    description="Downloads and saves market data for a stock into the database.",
)
def save_market_data(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Save market data for a stock."""

    return run_market_operation(
        operation="save_market_data",
        func=lambda: service.save_market_data(
            symbol=symbol,
            db=db,
        ),
        symbol=symbol,
    )


@router.get(
    "/all",
    summary="Get All Market Data",
    description="Retrieves all market data stored in the database.",
)
def get_all_market_data(
    db: Session = Depends(get_db),
):
    """Retrieve all stored market data."""

    return run_market_operation(
        operation="get_all_market_data",
        func=lambda: service.get_all_market_data(db),
    )


@router.get(
    "/stats",
    summary="Get Market Statistics",
    description="Retrieves market data statistics from the database.",
)
def market_statistics(
    db: Session = Depends(get_db),
):
    """Retrieve market data statistics."""

    return run_market_operation(
        operation="market_statistics",
        func=lambda: service.market_statistics(db),
    )


@router.delete(
    "/clear",
    summary="Clear All Market Data",
    description="Deletes all stored market data.",
)
def clear_market_data(
    db: Session = Depends(get_db),
):
    """Clear all stored market data."""

    return run_market_operation(
        operation="clear_market_data",
        func=lambda: service.clear_market_data(db),
    )


@router.delete(
    "/{symbol}",
    summary="Delete Stock Market Data",
    description="Deletes stored market data for a specific stock symbol.",
)
def delete_symbol(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Delete market data for a stock."""

    return run_market_operation(
        operation="delete_symbol",
        func=lambda: service.delete_symbol(
            symbol=symbol,
            db=db,
        ),
        symbol=symbol,
    )


@router.get(
    "/{symbol}",
    summary="Get Stock Market Data",
    description="Retrieves stored market data for a specific stock symbol.",
)
def get_symbol_market_data(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Retrieve market data for a stock."""

    return run_market_operation(
        operation="get_symbol_market_data",
        func=lambda: service.get_symbol_market_data(
            symbol=symbol,
            db=db,
        ),
        symbol=symbol,
    )


@router.post(
    "/load-history",
    summary="Load Nifty 200 Historical Data",
    description="Loads historical market data for Nifty 200 stocks.",
)
def load_history(
    request: HistoryLoadRequest,
    db: Session = Depends(get_db),
):
    """Load historical data for Nifty 200 stocks."""

    def execute():
        symbols = load_nifty200_symbols()

        logger.info(
            "Nifty 200 symbols loaded",
            extra={
                "event": "market_symbols_loaded",
                "service": "market_data",
                "symbol_count": len(symbols),
                "universe": "NIFTY200",
            },
        )

        return service.load_history(
            years=request.years,
            db=db,
            symbols=symbols,
        )

    return run_market_operation(
        operation="load_nifty200_history",
        func=execute,
        years=request.years,
        universe="NIFTY200",
    )


@router.post(
    "/history/nifty50",
    summary="Load Nifty 50 Historical Data",
    description="Loads historical market data for Nifty 50 stocks.",
)
def load_nifty50_history(
    years: int = 7,
    db: Session = Depends(get_db),
):
    """Load historical data for Nifty 50 stocks."""

    return run_market_operation(
        operation="load_nifty50_history",
        func=lambda: service.load_nifty50_history(
            years=years,
            db=db,
        ),
        years=years,
        universe="NIFTY50",
    )


@router.get(
    "/history/nifty50/test",
    summary="Test Nifty 50 Historical Data",
    description="Tests Nifty 50 historical data for a specific date. Date format: YYYY-MM-DD.",
)
def test_nifty(
    date: Date,
    db: Session = Depends(get_db),
):
    """Test Nifty 50 historical data for a specific date."""

    return run_market_operation(
        operation="test_nifty50_history",
        func=lambda: service.test_nifty(
            date=date,
            db=db,
        ),
        date=date.isoformat(),
        universe="NIFTY50",
    )


@router.post(
    "/history/sector/{sector}",
    summary="Load Sector Historical Data",
    description="Loads historical market data for stocks belonging to a sector.",
)
def load_sector_history(
    sector: Sector,
    years: int = 7,
    db: Session = Depends(get_db),
):
    """Load historical data for a sector."""

    return run_market_operation(
        operation="load_sector_history",
        func=lambda: service.load_sector_history(
            sector=sector,
            years=years,
            db=db,
        ),
        sector=str(sector),
        years=years,
    )


@router.post(
    "/stock-master",
    summary="Load Stock Master",
    description="Loads the Nifty 200 stock master into the database.",
)
def load_stock_master(
    db: Session = Depends(get_db),
):
    """Load Nifty 200 stock master records."""

    def execute():
        symbols = load_nifty200_symbols()

        logger.info(
            "Stock master symbols loaded",
            extra={
                "event": "stock_master_symbols_loaded",
                "service": "market_data",
                "symbol_count": len(symbols),
                "universe": "NIFTY200",
            },
        )

        return service.load_stock_master(
            db,
            symbols=symbols,
        )

    return run_market_operation(
        operation="load_stock_master",
        func=execute,
        universe="NIFTY200",
    )
