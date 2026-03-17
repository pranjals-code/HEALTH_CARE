"""
Centralized logging configuration for the application.
"""

import logging
import os
from logging.config import dictConfig


def configure_logging() -> None:
    """Configure process-wide logging once."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
