import logging

from fastapi import APIRouter

router = APIRouter()

# Module-level logger using centralized logging configuration.
logger = logging.getLogger(__name__)


@router.get(
    "/allocate-test",
    operation_id="allocation_engine_health_check",
    summary="Check Daily Allocation Engine",
    description=(
        "Checks whether the Daily Allocation Engine API is available "
        "and ready to receive allocation requests."
    ),
    tags=["Allocation"],
)
def allocate_test():
    """
    Daily Allocation Engine readiness endpoint.

    This endpoint currently performs a readiness check only.
    It does not execute portfolio allocation or modify any data.
    """

    logger.info(
        "Daily Allocation Engine readiness check completed",
        extra={
            "event": "allocation_engine_ready",
            "service": "allocation",
            "status": "ready",
        },
    )

    return {
        "message": "Daily Allocation Engine Ready",
        "service": "allocation",
        "status": "ready",
    }