#!/usr/bin/env python3
"""
Structured logging configuration for security-central.

Provides consistent logging across all scripts with:
- Multiple output formats (text/JSON)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured context (extra fields)
- File and console output
"""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string with log data
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields from logger.info("msg", extra={'key': 'value'})
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Add context to log records."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize filter with context.

        Args:
            context: Dictionary of context to add to all log records
        """
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to record.

        Args:
            record: Log record to filter

        Returns:
            Always True (don't filter out records)
        """
        if not hasattr(record, 'extra_data'):
            record.extra_data = {}
        record.extra_data.update(self.context)
        return True


def setup_logging(
    name: str,
    level: int = logging.INFO,
    json_format: bool = False,
    log_file: Optional[str] = None,
    console_output: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """Set up structured logging for a script.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format instead of text (default: False)
        log_file: Optional file path to write logs to
        console_output: Write logs to console (default: True)
        context: Optional context dict to add to all log records

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging(__name__, level=logging.DEBUG)
        >>> logger.info("Starting scan", extra={'repo_count': 4})
        >>> logger.error("Failed to clone", extra={'repo': 'foo', 'error': 'timeout'})
        >>> logger.debug("Processing package", extra={'package': 'requests', 'version': '2.28.0'})
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add context filter if provided
    if context:
        logger.addFilter(ContextFilter(context))

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            # Human-readable format with colors (if terminal supports it)
            formatter = ColoredFormatter(
                '%(asctime)s [%(levelname)-8s] %(name)s:%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Always use JSON format for file logs (easier to parse)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


class ColoredFormatter(logging.Formatter):
    """Add colors to console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format with colors if terminal supports it.

        Args:
            record: Log record to format

        Returns:
            Formatted string with ANSI colors
        """
        # Check if stdout is a terminal
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Add color to level name
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """Get an existing logger by name.

    Args:
        name: Logger name

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Message")
    """
    return logging.getLogger(name)


def set_global_log_level(level: int):
    """Set log level for all loggers.

    Args:
        level: Logging level to set

    Example:
        >>> set_global_log_level(logging.DEBUG)
    """
    logging.root.setLevel(level)
    for handler in logging.root.handlers:
        handler.setLevel(level)


# Convenience functions for common use cases
def setup_basic_logging(verbose: bool = False) -> logging.Logger:
    """Set up basic logging with simple defaults.

    Args:
        verbose: Enable debug level logging (default: False)

    Returns:
        Configured logger

    Example:
        >>> logger = setup_basic_logging(verbose=True)
        >>> logger.debug("This will show if verbose=True")
    """
    level = logging.DEBUG if verbose else logging.INFO
    return setup_logging(__name__, level=level)


def setup_file_logging(log_file: str, verbose: bool = False) -> logging.Logger:
    """Set up logging to file.

    Args:
        log_file: Path to log file
        verbose: Enable debug level logging

    Returns:
        Configured logger
    """
    level = logging.DEBUG if verbose else logging.INFO
    return setup_logging(
        __name__,
        level=level,
        json_format=True,  # Always JSON for files
        log_file=log_file,
        console_output=True
    )


# Example usage patterns
if __name__ == '__main__':
    # Example 1: Basic usage
    logger = setup_logging(__name__)
    logger.info("Basic logging example")

    # Example 2: With context
    logger = setup_logging(__name__, context={'script': 'scan_all_repos', 'run_id': '12345'})
    logger.info("Scanning repository", extra={'repo': 'security-central'})

    # Example 3: JSON format for automation
    json_logger = setup_logging(__name__, json_format=True)
    json_logger.info("JSON log entry", extra={'count': 42, 'status': 'success'})

    # Example 4: File logging
    file_logger = setup_file_logging('logs/security-central.log')
    file_logger.info("This goes to file and console")

    # Example 5: Debug level
    debug_logger = setup_logging(__name__, level=logging.DEBUG)
    debug_logger.debug("Debug information")
    debug_logger.info("Info message")
    debug_logger.warning("Warning message")
    debug_logger.error("Error message")

    # Example 6: With exception
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        debug_logger.error("Caught exception", extra={'error_type': type(e).__name__}, exc_info=True)
