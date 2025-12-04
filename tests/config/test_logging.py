"""Tests for LoggingConfig standard logging configuration (Article 9 compliant).

This module tests the LoggingConfig that manages standard logging settings
including log level, console output, and file output configuration.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from mixseek.config.logging import LevelName, LoggingConfig


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory for testing."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def clean_env() -> Generator[None]:
    """Clean environment variables before each test."""
    env_vars_to_clean = [
        "MIXSEEK_LOG_LEVEL",
        "MIXSEEK_LOG_CONSOLE",
        "MIXSEEK_LOG_FILE",
    ]
    original_env = {}
    for var in env_vars_to_clean:
        original_env[var] = os.environ.pop(var, None)

    yield

    # Restore original environment (or remove if originally not set)
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


class TestLoggingConfigDefaults:
    """Test default values for LoggingConfig fields."""

    def test_default_values(self) -> None:
        """Test that default LoggingConfig values are correct."""
        config = LoggingConfig()

        assert config.logfire_enabled is False
        assert config.console_enabled is True
        assert config.file_enabled is True
        assert config.log_level == "info"
        assert config.log_file_path is None

    def test_custom_values(self) -> None:
        """Test custom LoggingConfig values."""
        config = LoggingConfig(
            logfire_enabled=True,
            console_enabled=False,
            file_enabled=False,
            log_level="debug",
            log_file_path="/custom/path/app.log",
        )

        assert config.logfire_enabled is True
        assert config.console_enabled is False
        assert config.file_enabled is False
        assert config.log_level == "debug"
        assert config.log_file_path == "/custom/path/app.log"


class TestLoggingConfigFromEnv:
    """Test LoggingConfig.from_env() method."""

    def test_from_env_no_env_vars(self, clean_env: None) -> None:
        """Test from_env returns defaults when no environment variables are set."""
        config = LoggingConfig.from_env()

        assert config.logfire_enabled is False
        assert config.console_enabled is True
        assert config.file_enabled is True
        assert config.log_level == "info"

    def test_from_env_log_level(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_LEVEL."""
        os.environ["MIXSEEK_LOG_LEVEL"] = "debug"

        config = LoggingConfig.from_env()

        assert config.log_level == "debug"

    def test_from_env_all_log_levels(self, clean_env: None) -> None:
        """Test from_env accepts all valid log levels."""
        valid_levels: list[LevelName] = ["debug", "info", "warning", "error"]

        for level in valid_levels:
            os.environ["MIXSEEK_LOG_LEVEL"] = level
            config = LoggingConfig.from_env()
            assert config.log_level == level

    def test_from_env_console_disabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_CONSOLE=false."""
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"

        config = LoggingConfig.from_env()

        assert config.console_enabled is False

    def test_from_env_console_enabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_CONSOLE=true."""
        os.environ["MIXSEEK_LOG_CONSOLE"] = "true"

        config = LoggingConfig.from_env()

        assert config.console_enabled is True

    def test_from_env_file_disabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_FILE=false."""
        os.environ["MIXSEEK_LOG_FILE"] = "false"

        config = LoggingConfig.from_env()

        assert config.file_enabled is False

    def test_from_env_file_enabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_FILE=true."""
        os.environ["MIXSEEK_LOG_FILE"] = "true"

        config = LoggingConfig.from_env()

        assert config.file_enabled is True

    def test_from_env_all_settings(self, clean_env: None) -> None:
        """Test from_env reads all environment variables together."""
        os.environ["MIXSEEK_LOG_LEVEL"] = "warning"
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"
        os.environ["MIXSEEK_LOG_FILE"] = "false"

        config = LoggingConfig.from_env()

        assert config.log_level == "warning"
        assert config.console_enabled is False
        assert config.file_enabled is False

    def test_from_env_invalid_log_level(self, clean_env: None) -> None:
        """Test from_env raises ValueError for invalid log level."""
        os.environ["MIXSEEK_LOG_LEVEL"] = "invalid_level"

        with pytest.raises(ValueError) as exc_info:
            LoggingConfig.from_env()

        assert "invalid_level" in str(exc_info.value).lower()
        assert "debug" in str(exc_info.value).lower()

    def test_from_env_case_insensitive_boolean(self, clean_env: None) -> None:
        """Test from_env handles case variations for boolean values."""
        # TRUE, True, true should all work
        os.environ["MIXSEEK_LOG_CONSOLE"] = "TRUE"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        os.environ["MIXSEEK_LOG_CONSOLE"] = "True"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        # FALSE, False, false should all work
        os.environ["MIXSEEK_LOG_FILE"] = "FALSE"
        config = LoggingConfig.from_env()
        assert config.file_enabled is False

    def test_from_env_numeric_boolean(self, clean_env: None) -> None:
        """Test from_env handles numeric boolean values (1/0) from UI command."""
        # "1" should be treated as True (used by ui.py)
        os.environ["MIXSEEK_LOG_CONSOLE"] = "1"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        os.environ["MIXSEEK_LOG_FILE"] = "1"
        config = LoggingConfig.from_env()
        assert config.file_enabled is True

        # "0" should be treated as False
        os.environ["MIXSEEK_LOG_CONSOLE"] = "0"
        config = LoggingConfig.from_env()
        assert config.console_enabled is False

        os.environ["MIXSEEK_LOG_FILE"] = "0"
        config = LoggingConfig.from_env()
        assert config.file_enabled is False


class TestLoggingConfigFromToml:
    """Test LoggingConfig.from_toml() method."""

    def test_from_toml_no_file(self, temp_workspace: Path) -> None:
        """Test from_toml returns None when file doesn't exist."""
        config = LoggingConfig.from_toml(temp_workspace)

        assert config is None

    def test_from_toml_empty_logging_section(self, temp_workspace: Path) -> None:
        """Test from_toml with empty [logging] section uses defaults."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("[logging]\n")

        config = LoggingConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.log_level == "info"
        assert config.console_enabled is True
        assert config.file_enabled is True

    def test_from_toml_full_config(self, temp_workspace: Path) -> None:
        """Test from_toml reads all settings from TOML file."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("""
[logging]
log_level = "debug"
console_output = false
file_output = false
""")

        config = LoggingConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.log_level == "debug"
        assert config.console_enabled is False
        assert config.file_enabled is False

    def test_from_toml_partial_config(self, temp_workspace: Path) -> None:
        """Test from_toml uses defaults for missing fields."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("""
[logging]
log_level = "error"
""")

        config = LoggingConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.log_level == "error"
        assert config.console_enabled is True  # default
        assert config.file_enabled is True  # default

    def test_from_toml_invalid_log_level(self, temp_workspace: Path) -> None:
        """Test from_toml raises ValueError for invalid log level."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("""
[logging]
log_level = "invalid"
""")

        with pytest.raises(ValueError) as exc_info:
            LoggingConfig.from_toml(temp_workspace)

        assert "invalid" in str(exc_info.value).lower()

    def test_from_toml_invalid_toml_syntax(self, temp_workspace: Path) -> None:
        """Test from_toml raises ValueError for invalid TOML syntax."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("invalid toml [[ syntax")

        with pytest.raises(ValueError) as exc_info:
            LoggingConfig.from_toml(temp_workspace)

        assert "toml" in str(exc_info.value).lower()

    def test_from_toml_no_logging_section(self, temp_workspace: Path) -> None:
        """Test from_toml with TOML file but no [logging] section returns defaults."""
        config_path = temp_workspace / "logging.toml"
        config_path.write_text("""
[other_section]
some_key = "value"
""")

        config = LoggingConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.log_level == "info"  # default
        assert config.console_enabled is True  # default


class TestLogLevelValidation:
    """Test log level validation."""

    def test_valid_levels_type_hint(self) -> None:
        """Test that LevelName type includes all valid levels."""
        # This is a compile-time check, but we can verify the literal values
        valid_levels: list[LevelName] = ["debug", "info", "warning", "error"]
        for level in valid_levels:
            config = LoggingConfig(log_level=level)
            assert config.log_level == level

    def test_post_init_validates_log_level(self) -> None:
        """Test that __post_init__ validates log_level on direct instantiation.

        Article 9 compliance: No implicit fallbacks allowed.
        """
        with pytest.raises(ValueError) as exc_info:
            LoggingConfig(log_level="invalid")  # type: ignore[arg-type]

        assert "invalid" in str(exc_info.value).lower()
        assert "debug" in str(exc_info.value).lower()
