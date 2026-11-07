
import logging
from time import perf_counter

from fastapi import APIRouter

router = APIRouter(
    tags=["Health"]
)

logger = logging.getLogger(__name__)


@router.get(
    "/health",
    operation_id="application_health_check",
    summary="Check Application Health",
    description="Checks whether the AthenaAI application is running and responding to requests.",
)
def health():
    """
    Application health-check endpoint.

    Returns the current application health status.
    """

    start_time = perf_counter()

    logger.info(
        "Application health check started",
        extra={
            "event": "health_check_started",
            "service": "health",
        },
    )

    try:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Application health check completed",
            extra={
                "event": "health_check_completed",
                "service": "health",
                "status": "healthy",
                "duration_ms": duration_ms,
            },
        )

        return {
            "status": "Healthy",
            "service": "AthenaAI",
            "duration_ms": duration_ms,
        }

    except Exception:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "Application health check failed",
            extra={
                "event": "health_check_failed",
                "service": "health",
                "status": "unhealthy",
                "duration_ms": duration_ms,
            },
        )

        raise
