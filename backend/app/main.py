
import logging
import time
import uuid

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from app.core.logging_config import (
    configure_logging,
    operation_id_var,
    request_id_var,
)
from app.core.cache import cache_manager

from app.api import allocation, trade_selection
from app.api.backtest import router as backtest_router
from app.api.database import router as database_router
from app.api.health import router as health_router
from app.api.market import router as market_router
from app.api.strategy import router as strategy_router


# Initialize centralized logging before application startup.
configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage AthenaAI application startup and shutdown.

    Startup:
        1. Log application startup.
        2. Initialize Redis connectivity.

    Shutdown:
        1. Close Redis connections.
        2. Log application shutdown.
    """

    logger.info(
        "AthenaAI application starting",
        extra={"event": "application_startup"}
    )

    # Redis is optional. Application should work without it.
    try:
        cache_manager.connect()
        logger.info(
            "Redis initialization completed",
            extra={"event": "redis_connected"}
        )
    except Exception:
        logger.exception(
            "Redis connection failed. Continuing without Redis.",
            extra={"event": "redis_connection_failed"}
        )

    yield

    try:
        cache_manager.close()
        logger.info(
            "Redis connection closed",
            extra={"event": "redis_disconnected"}
        )
    except Exception:
        logger.exception(
            "Error while closing Redis connection",
            extra={"event": "redis_close_failed"}
        )

    logger.info(
        "AthenaAI application stopped",
        extra={"event": "application_shutdown"}
    )


app = FastAPI(
    title="AthenaAI",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next
):
    """
    Track every incoming API request.

    Generates:
        - Operation ID: Correlates related application operations.
        - Request ID: Uniquely identifies this HTTP request.

    Logs:
        - HTTP method and endpoint.
        - Response status code.
        - Request execution duration.
        - Exceptions.
    """

    request_id = str(uuid.uuid4())

    # Allow callers to provide an operation ID.
    # Generate one when the header is absent.
    operation_id = (
        request.headers.get("X-Operation-ID")
        or str(uuid.uuid4())
    )

    # Set request context for all logs generated during this request.
    request_token = request_id_var.set(request_id)
    operation_token = operation_id_var.set(operation_id)

    start_time = time.perf_counter()

    try:
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logger.info(
            "API request completed",
            extra={
                "event": "api_request_completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )

        # Return correlation IDs to the API caller.
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Operation-ID"] = operation_id

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logger.exception(
            "API request failed",
            extra={
                "event": "api_request_failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            }
        )

        raise

    finally:
        # Prevent request context from leaking into other requests.
        request_id_var.reset(request_token)
        operation_id_var.reset(operation_token)


# Register existing API routers.
app.include_router(health_router)
app.include_router(database_router)
app.include_router(market_router)
app.include_router(strategy_router)
app.include_router(backtest_router)

app.include_router(
    trade_selection.router,
    prefix="/trade-selection",
    tags=["Trade Selection"]
)

app.include_router(
    allocation.router,
    prefix="/allocation",
    tags=["Allocation"]
)


@app.get("/")
def home():
    """Return AthenaAI application status."""

    logger.info(
        "AthenaAI health endpoint accessed",
        extra={"event": "health_check"}
    )

    return {
        "project": "AthenaAI",
        "status": "Running"
    }
