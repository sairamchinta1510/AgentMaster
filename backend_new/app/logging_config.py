"""
Structured logging configuration for AgentMaster backend.
Configures JSON-formatted logging to stdout per global constraints.
"""

import logging
import json
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime


def setup_logging(log_level=logging.INFO):
    """
    Configure structured JSON logging to stdout.

    Args:
        log_level: Logging level (default: INFO)
    """
    # Create logger
    logger = logging.getLogger("agentmaster")
    logger.setLevel(log_level)

    # Remove any existing handlers
    logger.handlers.clear()

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Initialize logger on module import
logger = setup_logging()


def get_logger(name=None):
    """
    Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance
    """
    if name:
        return logging.getLogger(f"agentmaster.{name}")
    return logger
