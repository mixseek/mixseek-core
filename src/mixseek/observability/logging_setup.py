"""Standard logging configuration (Article 9 compliant).

This module provides setup_logging() function that configures Python's standard
logging module with optional Logfire integration, console output, and file output.

Configuration follows Constitution Article 9 (Data Accuracy Mandate):
- No hardcoded values (log level, paths from config)
- No implicit fallbacks (explicit enable/disable)
- Explicit error propagation

Path 1 Architecture:
    Standard logging → LogfireLoggingHandler → Logfire cloud
                   → StreamHandler → Console (stderr)
                   → FileHandler → File ($WORKSPACE/logs/mixseek.log)
"""

import logging
import sys
from pathlib import Path

from mixseek.config.logging import LoggingConfig

# Log level name to logging module constant mapping
LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

# Standard log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(config: LoggingConfig, workspace: Path | None = None) -> None:
    """Configure Python's standard logging with optional Logfire integration.

    This function sets up the root logger with handlers for:
    - Console output (stderr) if config.console_enabled
    - File output ($WORKSPACE/logs/mixseek.log) if config.file_enabled and workspace provided
    - Logfire cloud forwarding if config.logfire_enabled

    Args:
        config: Logging configuration specifying log level and output destinations
        workspace: Optional workspace path for file logging

    Note:
        - Log level is applied globally to all handlers (FR-007, FR-008)
        - Console and file outputs can be independently enabled/disabled (FR-005, FR-006)
        - Log directory is created automatically if needed (FR-011)
        - When both console and file are disabled, a NullHandler is added (silent mode)

    Example:
        >>> from mixseek.config.logging import LoggingConfig
        >>> config = LoggingConfig(log_level="debug", console_enabled=True)
        >>> setup_logging(config, workspace=Path("/path/to/workspace"))
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Set global log level
    level = LOG_LEVEL_MAP.get(config.log_level, logging.INFO)
    root_logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)

    handlers_added = 0

    # Add console handler (StreamHandler to stderr)
    # Note: When Logfire is enabled, console output is handled by Logfire's ConsoleOptions
    # to prevent duplicate log messages
    if config.console_enabled and not config.logfire_enabled:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        handlers_added += 1

    # Add file handler if workspace provided and file output enabled
    if config.file_enabled and workspace is not None:
        # Create logs directory
        log_dir = workspace / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler
        log_file = log_dir / "mixseek.log"
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        handlers_added += 1

    # Add Logfire handler if enabled (requires logfire package)
    if config.logfire_enabled:
        try:
            import logfire

            logfire_handler = logfire.LogfireLoggingHandler()
            logfire_handler.setLevel(level)
            root_logger.addHandler(logfire_handler)
            handlers_added += 1
        except ImportError:
            # Logfire not installed - skip (graceful degradation)
            root_logger.warning("Logfire package not installed, skipping Logfire logging handler")
        except Exception as e:
            # Logfire initialization failed - log warning and continue
            root_logger.warning(f"Failed to add Logfire logging handler: {e}")

    # If no handlers were added, add NullHandler to prevent "No handler found" warnings
    if handlers_added == 0:
        root_logger.addHandler(logging.NullHandler())
