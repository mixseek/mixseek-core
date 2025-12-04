"""Tests for setup_logging() standard logging configuration.

This module tests the setup_logging() function that configures
Python's standard logging module with Logfire integration.
"""

import logging
from collections.abc import Generator
from pathlib import Path

import pytest

from mixseek.config.logging import LoggingConfig
from mixseek.observability.logging_setup import setup_logging


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory for testing."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None]:
    """Reset logging configuration after each test."""
    yield
    # Reset root logger to avoid test pollution
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)


class TestSetupLoggingDefault:
    """Test setup_logging with default configuration."""

    def test_default_config_sets_root_logger_level(self, temp_workspace: Path) -> None:
        """Test that default config sets root logger to INFO level."""
        config = LoggingConfig()

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_default_config_creates_log_dir(self, temp_workspace: Path) -> None:
        """Test that setup_logging creates logs directory."""
        config = LoggingConfig()

        setup_logging(config, temp_workspace)

        log_dir = temp_workspace / "logs"
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_default_config_adds_handlers(self, temp_workspace: Path) -> None:
        """Test that default config adds console and file handlers."""
        config = LoggingConfig()

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        # Should have at least 2 handlers (console + file)
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types


class TestSetupLoggingLogLevel:
    """Test setup_logging log level configuration."""

    def test_debug_level(self, temp_workspace: Path) -> None:
        """Test setting DEBUG log level."""
        config = LoggingConfig(log_level="debug")

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_warning_level(self, temp_workspace: Path) -> None:
        """Test setting WARNING log level."""
        config = LoggingConfig(log_level="warning")

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_error_level(self, temp_workspace: Path) -> None:
        """Test setting ERROR log level."""
        config = LoggingConfig(log_level="error")

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR


class TestSetupLoggingDisableOutputs:
    """Test setup_logging with outputs disabled."""

    def test_disable_console(self, temp_workspace: Path) -> None:
        """Test disabling console output."""
        config = LoggingConfig(console_enabled=False)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "StreamHandler" not in handler_types
        assert "FileHandler" in handler_types  # File should still be enabled

    def test_disable_file(self, temp_workspace: Path) -> None:
        """Test disabling file output."""
        config = LoggingConfig(file_enabled=False)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "StreamHandler" in handler_types  # Console should still be enabled
        assert "FileHandler" not in handler_types

    def test_disable_both(self, temp_workspace: Path) -> None:
        """Test disabling both console and file output (silent mode)."""
        config = LoggingConfig(console_enabled=False, file_enabled=False)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        # Should have no handlers when both disabled (or only NullHandler)
        non_null_handlers = [h for h in root_logger.handlers if not isinstance(h, logging.NullHandler)]
        assert len(non_null_handlers) == 0


class TestSetupLoggingNoWorkspace:
    """Test setup_logging without workspace."""

    def test_no_workspace_console_only(self) -> None:
        """Test setup_logging without workspace uses console only."""
        config = LoggingConfig()

        setup_logging(config, workspace=None)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        # Without workspace, only console handler should be added
        assert "StreamHandler" in handler_types


class TestSetupLoggingLogFileCreation:
    """Test setup_logging log file creation."""

    def test_creates_log_file(self, temp_workspace: Path) -> None:
        """Test that setup_logging creates log file."""
        config = LoggingConfig()

        setup_logging(config, temp_workspace)

        log_file = temp_workspace / "logs" / "mixseek.log"
        # After logging something, the file should exist
        test_logger = logging.getLogger("test")
        test_logger.info("Test message")
        assert log_file.exists()

    def test_log_file_contains_messages(self, temp_workspace: Path) -> None:
        """Test that log file contains logged messages."""
        config = LoggingConfig()

        setup_logging(config, temp_workspace)

        test_logger = logging.getLogger("test")
        test_logger.info("Test log message")

        log_file = temp_workspace / "logs" / "mixseek.log"
        content = log_file.read_text()
        assert "Test log message" in content


class TestSetupLoggingWithLogfire:
    """Test setup_logging with Logfire enabled.

    When Logfire is enabled, console output is handled by Logfire's ConsoleOptions
    to prevent duplicate log messages. StreamHandler should NOT be added.
    """

    def test_logfire_enabled_no_stream_handler(self, temp_workspace: Path) -> None:
        """Test that StreamHandler is NOT added when Logfire is enabled."""
        config = LoggingConfig(logfire_enabled=True)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        # StreamHandler should NOT be present when Logfire is enabled
        assert "StreamHandler" not in handler_types
        # FileHandler should still be present
        assert "FileHandler" in handler_types

    def test_logfire_enabled_file_handler_still_works(self, temp_workspace: Path) -> None:
        """Test that FileHandler is still added when Logfire is enabled."""
        config = LoggingConfig(logfire_enabled=True, file_enabled=True)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "FileHandler" in handler_types

    def test_logfire_disabled_stream_handler_present(self, temp_workspace: Path) -> None:
        """Test that StreamHandler IS added when Logfire is disabled (default)."""
        config = LoggingConfig(logfire_enabled=False)

        setup_logging(config, temp_workspace)

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        # StreamHandler should be present when Logfire is disabled
        assert "StreamHandler" in handler_types
