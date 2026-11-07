
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings


logger = logging.getLogger(__name__)


# --------------------------------------------------
# Database Engine
# --------------------------------------------------

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)


# --------------------------------------------------
# Database Session Factory
# --------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# --------------------------------------------------
# Database Dependency
# --------------------------------------------------

def get_db():
    """
    Provides a database session for the request.

    Ensures transactions are rolled back on failure
    and the session is always closed.
    """

    db = SessionLocal()

    try:
        logger.debug(
            "Database session opened",
            extra={
                "event": "database_session_opened"
            }
        )

        yield db

    except Exception:
        db.rollback()

        logger.exception(
            "Database session failed",
            extra={
                "event": "database_session_failed"
            }
        )

        raise

    finally:
        db.close()

        logger.debug(
            "Database session closed",
            extra={
                "event": "database_session_closed"
            }
        )
