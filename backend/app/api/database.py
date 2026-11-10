
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.base import Base
from app.database.session import engine
from app.forward_testing.storage import (
    PaperOrder,
    PaperPosition,
    PaperPositionEvent,
)


# ---------------------------------------------------------------------
# Router and logger configuration
# ---------------------------------------------------------------------

router = APIRouter(
    prefix="/database",
    tags=["Database"],
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Database health check
# ---------------------------------------------------------------------

@router.get(
    "/status",
    summary="Check Database Connectivity",
    description=(
        "Checks whether AthenaAI can establish a connection "
        "to PostgreSQL by executing a lightweight SELECT 1 query."
    ),
    status_code=status.HTTP_200_OK,
)
def database_status():
    """
    Verify PostgreSQL connectivity.

    Returns:
        Database connection status.

    Raises:
        HTTPException: If the database connection or query fails.
    """

    start_time = perf_counter()

    logger.info(
        "Database connectivity check started",
        extra={
            "event": "database_health_check_started",
            "service": "database",
        },
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Database connectivity check successful",
            extra={
                "event": "database_connected",
                "service": "database",
                "status": "connected",
                "duration_ms": duration_ms,
            },
        )

        return {
            "database": "Connected",
            "status": "healthy",
            "duration_ms": duration_ms,
        }

    except SQLAlchemyError:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "Database connectivity check failed",
            extra={
                "event": "database_connection_failed",
                "service": "database",
                "status": "disconnected",
                "duration_ms": duration_ms,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )


# ---------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------

@router.post(
    "/init",
    summary="Initialize Database Tables",
    description=(
        "Creates database tables defined in SQLAlchemy metadata "
        "that do not already exist."
    ),
    status_code=status.HTTP_200_OK,
)
def initialize_database():
    """
    Initialize database tables using SQLAlchemy metadata.

    Existing tables are not recreated or modified.

    Raises:
        HTTPException: If database initialization fails.
    """

    start_time = perf_counter()

    table_count = len(Base.metadata.tables)

    logger.info(
        "Database initialization started",
        extra={
            "event": "database_initialization_started",
            "service": "database",
            "table_count": table_count,
        },
    )

    try:
        Base.metadata.create_all(bind=engine)

        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Database initialization completed",
            extra={
                "event": "database_initialization_completed",
                "service": "database",
                "table_count": table_count,
                "duration_ms": duration_ms,
            },
        )

        return {
            "message": "Database tables created successfully",
            "table_count": table_count,
            "duration_ms": duration_ms,
        }

    except SQLAlchemyError:
        duration_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "Database initialization failed",
            extra={
                "event": "database_initialization_failed",
                "service": "database",
                "table_count": table_count,
                "duration_ms": duration_ms,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database initialization failed",
        )