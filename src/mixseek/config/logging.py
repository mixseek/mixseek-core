"""Standard logging configuration (Article 9 compliant).

This module provides configuration management for standard Python logging integration.
All configuration follows Constitution Article 9 (Data Accuracy Mandate):
- No hardcoded values
- No implicit fallbacks
- Explicit error propagation

Configuration sources (priority order):
1. CLI flags (highest)
2. Environment variables (MIXSEEK_LOG_*)
3. TOML file ($MIXSEEK_WORKSPACE/logging.toml)
4. Default values (lowest)
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Valid log level names
LevelName = Literal["debug", "info", "warning", "error"]

# Valid log levels for validation
VALID_LOG_LEVELS: tuple[LevelName, ...] = ("debug", "info", "warning", "error")


class LoggingConfig(BaseModel):
    """Standard logging configuration (Article 9 compliant).

    Attributes:
        logfire_enabled: Enable forwarding to Logfire (requires --logfire flag)
        console_enabled: Enable console output (stderr)
        file_enabled: Enable file output ($MIXSEEK_WORKSPACE/logs/mixseek.log)
        log_level: Global log level for all destinations (debug/info/warning/error)
        log_file_path: Custom log file path (optional, defaults to workspace/logs/mixseek.log)

    Note:
        Default values are safe defaults (console/file enabled, cloud disabled).
        This follows Article 9 by requiring explicit opt-in for cloud features.
    """

    logfire_enabled: bool = Field(default=False)
    console_enabled: bool = Field(default=True)
    file_enabled: bool = Field(default=True)
    log_level: LevelName = Field(default="info")
    log_file_path: str | None = Field(default=None)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log_level after initialization (Article 9 compliant).

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
        """Load configuration from environment variables (Article 9 compliant).

        Environment Variables:
            MIXSEEK_LOG_LEVEL: Log level (debug/info/warning/error, default: info)
            MIXSEEK_LOG_CONSOLE: Enable console output (true/false, default: true)
            MIXSEEK_LOG_FILE: Enable file output (true/false, default: true)

        Returns:
            LoggingConfig: Configuration instance

        Raises:
            ValueError: If MIXSEEK_LOG_LEVEL contains an invalid value

        Note:
            Default values are safe defaults (console/file enabled).
            This follows Article 9 by using explicit environment variable reading.
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

        return cls(
            logfire_enabled=False,  # Set by CLI only
            console_enabled=console_enabled,
            file_enabled=file_enabled,
            log_level=log_level,
            log_file_path=None,  # Set by workspace logic
        )

    @classmethod
    def from_toml(cls, workspace: Path) -> "LoggingConfig | None":
        """Load configuration from TOML file.

        Args:
            workspace: MIXSEEK workspace path

        Returns:
            LoggingConfig | None: Configuration instance (None if file doesn't exist)

        Raises:
            ValueError: If TOML syntax is invalid or contains invalid values

        Note:
            Configuration file: $MIXSEEK_WORKSPACE/logging.toml

            Example TOML format:
            [logging]
            log_level = "info"
            console_output = true
            file_output = true
        """
        import tomllib

        config_path = workspace / "logging.toml"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file: {config_path}") from e

        logging_data = data.get("logging", {})

        # Validate log level
        log_level_str = logging_data.get("log_level", "info")
        if log_level_str not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level in {config_path}: '{log_level_str}'. Valid values: {list(VALID_LOG_LEVELS)}"
            )
        log_level: LevelName = log_level_str

        return cls(
            logfire_enabled=False,  # Set by CLI only
            console_enabled=logging_data.get("console_output", True),
            file_enabled=logging_data.get("file_output", True),
            log_level=log_level,
            log_file_path=None,  # Set by workspace logic
        )
