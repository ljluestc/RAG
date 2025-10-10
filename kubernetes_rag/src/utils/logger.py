"""Logger setup for the Kubernetes RAG system."""

import sys
from loguru import logger
from pathlib import Path


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
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file logger if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
            level=log_level,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
        )

    return logger


def get_logger():
    """Get the configured logger instance."""
    return logger
