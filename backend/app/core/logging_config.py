
import json
import logging
import os

from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from app.config.settings import settings


# Request context shared by log records created during an API request.
operation_id_var = ContextVar("operation_id", default=None)
request_id_var = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Format logs as structured JSON."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "file": os.path.basename(record.pathname),
            "function": record.funcName,
            "line": record.lineno,
            "operation_id": operation_id_var.get(),
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }

        # Add explicitly supplied business context.
        for field in (
            "event",
            "symbol",
            "period",
            "interval",
            "duration_ms",
            "cache_status",
            "run_id",
            "trade_id",
            "quantity",
            "reason",
            "method",
            "path",
            "status_code",
        ):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data, default=str)


def configure_logging():
    """Configure console and rotating file logging."""

    root_logger = logging.getLogger()

    if getattr(root_logger, "_athena_configured", False):
        return

    os.makedirs(settings.LOG_DIR, exist_ok=True)

    root_logger.setLevel(settings.LOG_LEVEL.upper())

    formatter = JsonFormatter()

    # Docker captures this output through container stdout.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Also retain logs in a rotating file.
    file_handler = RotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, "athena.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger._athena_configured = True
