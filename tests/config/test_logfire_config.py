"""Tests for LogfireConfig Logfire observability configuration.

This module tests the LogfireConfig including the
console_output and file_output fields for local span output control.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode


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
        "LOGFIRE_ENABLED",
        "LOGFIRE_PRIVACY_MODE",
        "LOGFIRE_CAPTURE_HTTP",
        "LOGFIRE_PROJECT",
        "LOGFIRE_SEND_TO_LOGFIRE",
        "MIXSEEK_LOG_CONSOLE",
        "MIXSEEK_LOG_FILE",
    ]
    original_env = {}
    for var in env_vars_to_clean:
        original_env[var] = os.environ.pop(var, None)

    yield

    # Restore original environment
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value


class TestLogfireConfigConsoleFileOutput:
    """Test console_output and file_output fields."""

    def test_default_console_output_true(self, clean_env: None) -> None:
        """Test that console_output defaults to True."""
        config = LogfireConfig.from_env()
        assert config.console_output is True

    def test_default_file_output_true(self, clean_env: None) -> None:
        """Test that file_output defaults to True."""
        config = LogfireConfig.from_env()
        assert config.file_output is True

    def test_from_env_console_disabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_CONSOLE=false."""
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"

        config = LogfireConfig.from_env()

        assert config.console_output is False

    def test_from_env_file_disabled(self, clean_env: None) -> None:
        """Test from_env reads MIXSEEK_LOG_FILE=false."""
        os.environ["MIXSEEK_LOG_FILE"] = "false"

        config = LogfireConfig.from_env()

        assert config.file_output is False

    def test_from_env_both_disabled(self, clean_env: None) -> None:
        """Test from_env reads both MIXSEEK_LOG_CONSOLE and MIXSEEK_LOG_FILE."""
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"
        os.environ["MIXSEEK_LOG_FILE"] = "false"

        config = LogfireConfig.from_env()

        assert config.console_output is False
        assert config.file_output is False

    def test_from_env_numeric_boolean(self, clean_env: None) -> None:
        """Test from_env handles numeric boolean values (1/0) from UI command."""
        # "1" should be treated as True (used by ui.py)
        os.environ["MIXSEEK_LOG_CONSOLE"] = "1"
        config = LogfireConfig.from_env()
        assert config.console_output is True

        os.environ["MIXSEEK_LOG_FILE"] = "1"
        config = LogfireConfig.from_env()
        assert config.file_output is True

        # "0" should be treated as False
        os.environ["MIXSEEK_LOG_CONSOLE"] = "0"
        config = LogfireConfig.from_env()
        assert config.console_output is False

        os.environ["MIXSEEK_LOG_FILE"] = "0"
        config = LogfireConfig.from_env()
        assert config.file_output is False


class TestLogfireConfigFromTomlConsoleFile:
    """Test console_output and file_output from TOML."""

    def test_from_toml_default_console_file(self, temp_workspace: Path) -> None:
        """Test from_toml uses default values for console_output and file_output."""
        config_path = temp_workspace / "logfire.toml"
        config_path.write_text("""
[logfire]
enabled = true
""")

        config = LogfireConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.console_output is True  # default
        assert config.file_output is True  # default

    def test_from_toml_console_file_disabled(self, temp_workspace: Path) -> None:
        """Test from_toml reads console_output and file_output."""
        config_path = temp_workspace / "logfire.toml"
        config_path.write_text("""
[logfire]
enabled = true
console_output = false
file_output = false
""")

        config = LogfireConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.console_output is False
        assert config.file_output is False

    def test_from_toml_console_only(self, temp_workspace: Path) -> None:
        """Test from_toml with only console_output set."""
        config_path = temp_workspace / "logfire.toml"
        config_path.write_text("""
[logfire]
enabled = true
console_output = false
""")

        config = LogfireConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.console_output is False
        assert config.file_output is True  # default


class TestLogfireConfigExistingFields:
    """Test existing LogfireConfig fields still work correctly."""

    def test_from_env_enabled(self, clean_env: None) -> None:
        """Test from_env reads LOGFIRE_ENABLED."""
        os.environ["LOGFIRE_ENABLED"] = "1"

        config = LogfireConfig.from_env()

        assert config.enabled is True

    def test_from_env_privacy_mode(self, clean_env: None) -> None:
        """Test from_env reads LOGFIRE_PRIVACY_MODE."""
        os.environ["LOGFIRE_PRIVACY_MODE"] = "full"

        config = LogfireConfig.from_env()

        assert config.privacy_mode == LogfirePrivacyMode.FULL

    def test_from_env_capture_http(self, clean_env: None) -> None:
        """Test from_env reads LOGFIRE_CAPTURE_HTTP."""
        os.environ["LOGFIRE_CAPTURE_HTTP"] = "1"

        config = LogfireConfig.from_env()

        assert config.capture_http is True

    def test_from_env_defaults(self, clean_env: None) -> None:
        """Test from_env default values."""
        config = LogfireConfig.from_env()

        assert config.enabled is False
        assert config.privacy_mode == LogfirePrivacyMode.METADATA_ONLY
        assert config.capture_http is False
        assert config.project_name is None
        assert config.send_to_logfire is True

    def test_from_toml_no_file(self, temp_workspace: Path) -> None:
        """Test from_toml returns None when file doesn't exist."""
        config = LogfireConfig.from_toml(temp_workspace)

        assert config is None

    def test_from_toml_full_config(self, temp_workspace: Path) -> None:
        """Test from_toml reads all fields."""
        config_path = temp_workspace / "logfire.toml"
        config_path.write_text("""
[logfire]
enabled = true
privacy_mode = "full"
capture_http = true
project_name = "test-project"
send_to_logfire = false
console_output = true
file_output = false
""")

        config = LogfireConfig.from_toml(temp_workspace)

        assert config is not None
        assert config.enabled is True
        assert config.privacy_mode == LogfirePrivacyMode.FULL
        assert config.capture_http is True
        assert config.project_name == "test-project"
        assert config.send_to_logfire is False
        assert config.console_output is True
        assert config.file_output is False
