
import logging
import os
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://backend:8000",
)

TIMEOUT = 300.0


def call_backend(endpoint: str, payload: dict | None = None):
    response = httpx.post(
        f"{BACKEND_URL}{endpoint}",
        json=payload,
        timeout=TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def run_candidate_scan():
    logger.info("Starting daily candidate scan")

    result = call_backend(
        "/forward-testing/scan"
    )

    logger.info(
        "Candidate scan completed: %s",
        result,
    )

    return result


def run_order_execution(signal_date: str, execution_date: str):
    logger.info("Starting paper order execution")

    result = call_backend(
        "/forward-testing/execute",
        {
            "signal_date": signal_date,
            "execution_date": execution_date,
        },
    )

    logger.info("Paper execution result: %s", result)

    return result

def run_position_monitoring():
    market_date = date.today().isoformat()

    logger.info(
        "Starting position monitoring",
        extra={
            "event": "forward_testing_monitoring_started",
            "market_date": market_date,
        },
    )

    result = call_backend(
        "/forward-testing/monitor",
        {
            "market_date": market_date,
        },
    )

    logger.info(
        "Position monitoring completed",
        extra={
            "event": "forward_testing_monitoring_completed",
            "result": result,
        },
    )

    return result
