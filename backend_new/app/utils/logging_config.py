import logging
import json
import sys
from datetime import datetime
from app.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = record.execution_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure structured logging to stdout."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(handler)


def log_event(event_type: str, data: dict, execution_id: str = None, agent_id: str = None) -> None:
    """Log a structured event."""
    logger = logging.getLogger("agentmaster")
    extra = {"event_type": event_type}
    if execution_id:
        extra["execution_id"] = execution_id
    if agent_id:
        extra["agent_id"] = agent_id

    logger.info(json.dumps(data), extra=extra)
