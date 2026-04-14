"""LogfireConfig テスト。

file_output / from_toml 廃止後のテスト。console_output は維持。
"""

import os
from collections.abc import Generator

import pytest

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode


@pytest.fixture
def clean_env() -> Generator[None]:
    """テスト前に環境変数をクリア"""
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

    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


class TestLogfireConfigConsoleOutput:
    """console_output フィールドのテスト"""

    def test_default_console_output_true(self, clean_env: None) -> None:
        config = LogfireConfig.from_env()
        assert config.console_output is True

    def test_from_env_console_disabled(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"
        config = LogfireConfig.from_env()
        assert config.console_output is False

    def test_from_env_numeric_boolean(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "1"
        config = LogfireConfig.from_env()
        assert config.console_output is True

        os.environ["MIXSEEK_LOG_CONSOLE"] = "0"
        config = LogfireConfig.from_env()
        assert config.console_output is False


class TestLogfireConfigExistingFields:
    """既存フィールドの互換性テスト"""

    def test_from_env_enabled(self, clean_env: None) -> None:
        os.environ["LOGFIRE_ENABLED"] = "1"
        config = LogfireConfig.from_env()
        assert config.enabled is True

    def test_from_env_privacy_mode(self, clean_env: None) -> None:
        os.environ["LOGFIRE_PRIVACY_MODE"] = "full"
        config = LogfireConfig.from_env()
        assert config.privacy_mode == LogfirePrivacyMode.FULL

    def test_from_env_capture_http(self, clean_env: None) -> None:
        os.environ["LOGFIRE_CAPTURE_HTTP"] = "1"
        config = LogfireConfig.from_env()
        assert config.capture_http is True

    def test_from_env_defaults(self, clean_env: None) -> None:
        config = LogfireConfig.from_env()

        assert config.enabled is False
        assert config.privacy_mode == LogfirePrivacyMode.METADATA_ONLY
        assert config.capture_http is False
        assert config.project_name is None
        assert config.send_to_logfire is True
        assert config.console_output is True

    def test_direct_construction(self) -> None:
        """直接構築でフィールドが正しく設定される"""
        config = LogfireConfig(
            enabled=True,
            privacy_mode=LogfirePrivacyMode.FULL,
            capture_http=True,
            project_name="test-project",
            send_to_logfire=False,
            console_output=False,
        )
        assert config.enabled is True
        assert config.privacy_mode == LogfirePrivacyMode.FULL
        assert config.capture_http is True
        assert config.project_name == "test-project"
        assert config.send_to_logfire is False
        assert config.console_output is False
