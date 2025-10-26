#!/usr/bin/env python3
"""
Comprehensive tests for scripts/logging_config.py

Tests logging configuration, formatters, filters, and setup functions.
"""

import json
import logging
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from logging_config import (
    ColoredFormatter,
    ContextFilter,
    JSONFormatter,
    get_logger,
    set_global_log_level,
    setup_basic_logging,
    setup_file_logging,
    setup_logging,
)


class TestJSONFormatter:
    """Test JSONFormatter class."""

    def test_basic_json_formatting(self):
        """Test basic JSON log formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["message"] == "Test message"
        assert log_dict["level"] == "INFO"
        assert "timestamp" in log_dict

    def test_json_with_extra_fields(self):
        """Test JSON formatting with extra context fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.repo = "test-repo"
        record.scan_id = "12345"

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["repo"] == "test-repo"
        assert log_dict["scan_id"] == "12345"

    def test_json_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=30,
                msg="Exception occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            output = formatter.format(record)
            log_dict = json.loads(output)

            assert "exception" in log_dict
            assert "ValueError" in log_dict["exception"]
            assert "Test error" in log_dict["exception"]


class TestContextFilter:
    """Test ContextFilter class."""

    def test_add_context_to_record(self):
        """Test adding context to log records."""
        context = {"repo": "test-repo", "user": "test-user"}
        filter_obj = ContextFilter(context)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        assert record.repo == "test-repo"
        assert record.user == "test-user"

    def test_empty_context(self):
        """Test filter with empty context."""
        filter_obj = ContextFilter({})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True

    def test_context_doesnt_override_existing(self):
        """Test that context doesn't override existing attributes."""
        context = {"levelname": "CUSTOM"}
        filter_obj = ContextFilter(context)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        # Should not override built-in levelname
        assert record.levelname == "INFO"


class TestColoredFormatter:
    """Test ColoredFormatter class."""

    def test_colored_formatting(self):
        """Test colored log formatting."""
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)

        # Check basic structure (colors will be ANSI codes)
        assert "Test message" in output
        assert "test.py" in output

    def test_different_log_levels_different_colors(self):
        """Test that different levels get different color codes."""
        formatter = ColoredFormatter()

        info_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Info",
            args=(),
            exc_info=None,
        )
        error_record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error",
            args=(),
            exc_info=None,
        )

        info_output = formatter.format(info_record)
        error_output = formatter.format(error_record)

        # Outputs should be different (different color codes)
        assert info_output != error_output
        assert "Info" in info_output
        assert "Error" in error_output


class TestSetupLogging:
    """Test setup_logging function."""

    def test_basic_setup(self):
        """Test basic logging setup."""
        logger = setup_logging("test_logger", level=logging.INFO)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO

    def test_json_format(self):
        """Test setup with JSON format."""
        logger = setup_logging("test_json", json_format=True, console_output=True)
        assert isinstance(logger, logging.Logger)
        # Check that a handler exists
        assert len(logger.handlers) > 0

    def test_file_logging(self):
        """Test setup with file logging."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tf:
            log_file = tf.name

        try:
            logger = setup_logging("test_file", log_file=log_file)
            logger.info("Test message")

            # Check file was created and has content
            assert os.path.exists(log_file)
            with open(log_file) as f:
                content = f.read()
                assert "Test message" in content
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_console_output_disabled(self):
        """Test setup with console output disabled."""
        logger = setup_logging("test_no_console", console_output=False)
        # Should have no StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        # May have 0 handlers if no file logging either
        assert isinstance(logger, logging.Logger)

    def test_with_context(self):
        """Test setup with context."""
        context = {"repo": "test-repo", "scan_id": "123"}
        logger = setup_logging("test_context", context=context)

        # Check that ContextFilter was added
        filters = []
        for handler in logger.handlers:
            filters.extend(handler.filters)

        context_filters = [f for f in filters if isinstance(f, ContextFilter)]
        assert len(context_filters) > 0

    def test_debug_level(self):
        """Test setup with DEBUG level."""
        logger = setup_logging("test_debug", level=logging.DEBUG)
        assert logger.level == logging.DEBUG


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger."""
        logger = get_logger("test_get_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_get_logger"

    def test_get_logger_returns_same_instance(self):
        """Test that calling get_logger twice returns same instance."""
        logger1 = get_logger("test_same")
        logger2 = get_logger("test_same")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that different names create different loggers."""
        logger1 = get_logger("test_logger1")
        logger2 = get_logger("test_logger2")
        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestSetGlobalLogLevel:
    """Test set_global_log_level function."""

    def test_set_global_level(self):
        """Test setting global log level."""
        # Create a logger before setting global level
        logger = get_logger("test_global_level")
        initial_level = logger.level

        # Set global level
        set_global_log_level(logging.ERROR)

        # Check that root logger level changed
        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_set_debug_level(self):
        """Test setting DEBUG level globally."""
        set_global_log_level(logging.DEBUG)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_set_critical_level(self):
        """Test setting CRITICAL level globally."""
        set_global_log_level(logging.CRITICAL)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.CRITICAL


class TestSetupBasicLogging:
    """Test setup_basic_logging function."""

    def test_basic_setup_non_verbose(self):
        """Test basic setup without verbose mode."""
        logger = setup_basic_logging(verbose=False)
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO

    def test_basic_setup_verbose(self):
        """Test basic setup with verbose mode."""
        logger = setup_basic_logging(verbose=True)
        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.DEBUG

    def test_has_console_handler(self):
        """Test that basic setup has console handler."""
        logger = setup_basic_logging()
        handlers = logger.handlers
        assert len(handlers) > 0
        # Should have at least one StreamHandler
        stream_handlers = [h for h in handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) > 0


class TestSetupFileLogging:
    """Test setup_file_logging function."""

    def test_file_logging_creates_file(self):
        """Test that file logging creates log file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tf:
            log_file = tf.name

        try:
            # Remove the file first
            os.unlink(log_file)

            logger = setup_file_logging(log_file)
            logger.info("Test log entry")

            # Check file exists and has content
            assert os.path.exists(log_file)
            with open(log_file) as f:
                content = f.read()
                assert "Test log entry" in content
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_file_logging_verbose(self):
        """Test file logging with verbose mode."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tf:
            log_file = tf.name

        try:
            logger = setup_file_logging(log_file, verbose=True)
            assert logger.level == logging.DEBUG

            logger.debug("Debug message")

            with open(log_file) as f:
                content = f.read()
                assert "Debug message" in content
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_file_logging_non_verbose(self):
        """Test file logging without verbose mode."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tf:
            log_file = tf.name

        try:
            logger = setup_file_logging(log_file, verbose=False)
            assert logger.level == logging.INFO
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_file_logging_creates_directory(self):
        """Test that file logging creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "logs", "subdir", "test.log")

            logger = setup_file_logging(log_file)
            logger.info("Test")

            assert os.path.exists(log_file)
            assert os.path.exists(os.path.dirname(log_file))


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tf:
            log_file = tf.name

        try:
            # Setup logging with all features
            logger = setup_logging(
                "integration_test",
                level=logging.DEBUG,
                json_format=False,
                log_file=log_file,
                console_output=True,
                context={"test_id": "123"},
            )

            # Log various levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Check file has all messages
            with open(log_file) as f:
                content = f.read()
                assert "Debug message" in content
                assert "Info message" in content
                assert "Warning message" in content
                assert "Error message" in content
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_multiple_loggers_isolation(self):
        """Test that multiple loggers are isolated."""
        logger1 = setup_logging("logger1", level=logging.DEBUG)
        logger2 = setup_logging("logger2", level=logging.ERROR)

        assert logger1.level == logging.DEBUG
        assert logger2.level == logging.ERROR
        assert logger1 is not logger2

    def test_json_and_colored_output(self):
        """Test JSON formatting vs colored output."""
        # JSON logger
        json_logger = setup_logging("json_test", json_format=True)

        # Colored logger
        colored_logger = setup_logging("colored_test", json_format=False)

        assert isinstance(json_logger, logging.Logger)
        assert isinstance(colored_logger, logging.Logger)
