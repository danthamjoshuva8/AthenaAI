
import logging
from datetime import date
from time import perf_counter

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.forward_testing_service import (
    ForwardTestingService,
)


router = APIRouter(
    prefix="/forward-testing",
    tags=["Forward Testing"],
)

service = ForwardTestingService()
logger = logging.getLogger(__name__)


class ExecutionRequest(BaseModel):
    signal_date: date
    execution_date: date


class MonitoringRequest(BaseModel):
    market_date: date


@router.post(
    "/scan",
    operation_id="scan_latest_forward_testing_session",
    summary="Scan Latest Forward Testing Session",
    description=(
        "Generates trade candidates using only the latest "
        "available market session."
    ),
)
def scan_latest_session(
    db: Session = Depends(get_db),
):
    start_time = perf_counter()

    logger.info(
        "Forward-testing API scan started",
        extra={
            "event": "forward_testing_api_scan_started",
            "service": "forward_testing",
        },
    )

    try:
        result = service.scan_latest_session(db)

        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Forward-testing API scan completed",
            extra={
                "event": "forward_testing_api_scan_completed",
                "service": "forward_testing",
                "status": "success",
                "scan_date": result["scan_date"],
                "candidates_count": result["candidates_count"],
                "duration_ms": duration_ms,
            },
        )

        return result

    except Exception:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "Forward-testing API scan failed",
            extra={
                "event": "forward_testing_api_scan_failed",
                "service": "forward_testing",
                "status": "failed",
                "duration_ms": duration_ms,
            },
        )

        raise


@router.post(
    "/execute",
    operation_id="execute_forward_testing_orders",
    summary="Execute Forward Testing Orders",
    description=(
        "Approves candidates and executes paper orders "
        "using the specified execution session."
    ),
)
def execute_forward_testing_orders(
    request: ExecutionRequest,
    db: Session = Depends(get_db),
):
    start_time = perf_counter()

    logger.info(
        "Forward-testing execution started",
        extra={
            "event": "forward_testing_execution_started",
            "signal_date": request.signal_date.isoformat(),
            "execution_date": request.execution_date.isoformat(),
        },
    )

    try:
        result = service.execute_daily_orders(
            db=db,
            signal_date=request.signal_date,
            execution_date=request.execution_date,
        )

        logger.info(
            "Forward-testing execution completed",
            extra={
                "event": "forward_testing_execution_completed",
                "status": result.get("status"),
                "duration_ms": round(
                    (perf_counter() - start_time) * 1000,
                    2,
                ),
            },
        )

        return result

    except Exception:
        logger.exception(
            "Forward-testing execution failed",
            extra={
                "event": "forward_testing_execution_failed",
            },
        )
        raise


@router.post(
    "/monitor",
    operation_id="monitor_forward_testing_positions",
    summary="Monitor Forward Testing Positions",
    description=(
        "Monitors persisted open positions using "
        "the specified completed market session."
    ),
)
def monitor_forward_testing_positions(
    request: MonitoringRequest,
    db: Session = Depends(get_db),
):
    start_time = perf_counter()

    logger.info(
        "Forward-testing position monitoring started",
        extra={
            "event": "forward_testing_monitoring_started",
            "market_date": request.market_date.isoformat(),
        },
    )

    try:
        result = service.monitor_positions(
            db=db,
            market_date=request.market_date,
        )

        logger.info(
            "Forward-testing position monitoring completed",
            extra={
                "event": "forward_testing_monitoring_completed",
                "status": result.get("status"),
                "duration_ms": round(
                    (perf_counter() - start_time) * 1000,
                    2,
                ),
            },
        )

        return result

    except Exception:
        logger.exception(
            "Forward-testing position monitoring failed",
            extra={
                "event": "forward_testing_monitoring_failed",
            },
        )
        raise
