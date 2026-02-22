"""Logger setup for the Kubernetes RAG system."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str | None = None):
    """
    Set up the logger with custom configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to save logs
    """
    # Remove default logger
    logger.remove()

    # Add custom logger to stdout
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # Structured JSON file sink — machine-readable for log aggregation
    json_log_path = Path("logs/rag.jsonl")
    json_log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(json_log_path),
        serialize=True,  # loguru JSON serialization
        level=log_level,
        rotation="50 MB",
        retention="7 days",
        compression="gz",
    )

    # Add additional plain-text file logger if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                "{name}:{function} - {message}"
            ),
            level=log_level,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
        )

    return logger


def get_logger():
    """Get the configured logger instance."""
    return logger
