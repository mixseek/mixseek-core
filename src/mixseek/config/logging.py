"""Standard logging configuration.

This module provides configuration management for standard Python logging integration.
- No hardcoded values
- No implicit fallbacks
- Explicit error propagation

Configuration sources (priority order):
1. CLI flags (highest)
2. Environment variables (MIXSEEK_LOG_*)
3. Default values (lowest)
"""

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Valid log level names
LevelName = Literal["debug", "info", "warning", "error", "critical"]

# Valid log levels for validation
VALID_LOG_LEVELS: tuple[LevelName, ...] = ("debug", "info", "warning", "error", "critical")

# Log output format type
LogFormatType = Literal["text", "json"]


class LoggingConfig(BaseModel):
    """Standard logging configuration.

    Attributes:
        logfire_enabled: Enable forwarding to Logfire (requires --logfire flag)
        console_enabled: Enable console output (stderr)
        file_enabled: Enable file output ($MIXSEEK_WORKSPACE/logs/mixseek.log)
        log_level: Global log level for all destinations (debug/info/warning/error/critical)
        log_format: Log output format (text/json)

    Note:
        Default values are safe defaults (console/file enabled, cloud disabled).
        Requires explicit opt-in for cloud features.
    """

    logfire_enabled: bool = Field(default=False)
    console_enabled: bool = Field(default=True)
    file_enabled: bool = Field(default=True)
    log_level: LevelName = Field(default="info")
    log_format: LogFormatType = Field(default="text")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log_level after initialization.

        Raises:
            ValueError: If log_level is not a valid value

        Note:
            This ensures validation occurs even when LoggingConfig is
            instantiated directly, preventing implicit fallbacks.
        """
        if v not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{v}'. Valid values: {list(VALID_LOG_LEVELS)}")
        return v

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Load configuration from environment variables.

        Environment Variables:
            MIXSEEK_LOG_LEVEL: Log level (debug/info/warning/error/critical, default: info)
            MIXSEEK_LOG_CONSOLE: Enable console output (true/false/1/0, default: true)
            MIXSEEK_LOG_FILE: Enable file output (true/false/1/0, default: true)
            MIXSEEK_LOG_FORMAT: Log output format (text/json, default: text)

        Returns:
            LoggingConfig: Configuration instance

        Raises:
            ValueError: If MIXSEEK_LOG_LEVEL or MIXSEEK_LOG_FORMAT contains an invalid value

        Note:
            Default values are safe defaults (console/file enabled).
            Uses explicit environment variable reading.
        """
        # Read log level with validation
        log_level_str = os.getenv("MIXSEEK_LOG_LEVEL", "info").lower()
        if log_level_str not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level: '{log_level_str}'. Valid values: {list(VALID_LOG_LEVELS)}")
        log_level: LevelName = log_level_str  # type: ignore[assignment]

        # Read boolean values with case-insensitive comparison
        console_str = os.getenv("MIXSEEK_LOG_CONSOLE", "true").lower()
        console_enabled = console_str in ("true", "1")

        file_str = os.getenv("MIXSEEK_LOG_FILE", "true").lower()
        file_enabled = file_str in ("true", "1")

        # Read log output format
        log_format_str = os.getenv("MIXSEEK_LOG_FORMAT", "text").lower()
        valid_formats = ("text", "json")
        if log_format_str not in valid_formats:
            raise ValueError(f"Invalid log format: '{log_format_str}'. Valid values: {list(valid_formats)}")
        log_format: LogFormatType = log_format_str  # type: ignore[assignment]

        return cls(
            logfire_enabled=False,  # Set by CLI only
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            log_level=log_level,
            log_format=log_format,
        )
