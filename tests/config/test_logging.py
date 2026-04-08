"""LoggingConfig 標準ロギング設定テスト。

log_format フィールド追加、from_toml 廃止後のテスト。
"""

import os
from collections.abc import Generator

import pytest

from mixseek.config.logging import LevelName, LoggingConfig


@pytest.fixture
def clean_env() -> Generator[None]:
    """テスト前に環境変数をクリア"""
    env_vars_to_clean = [
        "MIXSEEK_LOG_LEVEL",
        "MIXSEEK_LOG_CONSOLE",
        "MIXSEEK_LOG_FILE",
        "MIXSEEK_LOG_FORMAT",
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


class TestLoggingConfigDefaults:
    """デフォルト値テスト"""

    def test_default_values(self) -> None:
        config = LoggingConfig()

        assert config.logfire_enabled is False
        assert config.console_enabled is True
        assert config.file_enabled is True
        assert config.log_level == "info"
        assert config.log_format == "text"

    def test_custom_values(self) -> None:
        config = LoggingConfig(
            logfire_enabled=True,
            console_enabled=False,
            file_enabled=False,
            log_level="debug",
            log_format="json",
        )

        assert config.logfire_enabled is True
        assert config.console_enabled is False
        assert config.file_enabled is False
        assert config.log_level == "debug"
        assert config.log_format == "json"


class TestLoggingConfigLogFormat:
    """log_format フィールドのテスト"""

    def test_default_text(self) -> None:
        """デフォルト値は "text" """
        config = LoggingConfig()
        assert config.log_format == "text"

    def test_json_format(self) -> None:
        """log_format="json" を受け付ける"""
        config = LoggingConfig(log_format="json")
        assert config.log_format == "json"

    def test_text_format(self) -> None:
        """log_format="text" を受け付ける"""
        config = LoggingConfig(log_format="text")
        assert config.log_format == "text"


class TestLoggingConfigFromEnv:
    """from_env() メソッドのテスト"""

    def test_from_env_no_env_vars(self, clean_env: None) -> None:
        config = LoggingConfig.from_env()

        assert config.logfire_enabled is False
        assert config.console_enabled is True
        assert config.file_enabled is True
        assert config.log_level == "info"
        assert config.log_format == "text"

    def test_from_env_log_level(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_LEVEL"] = "debug"
        config = LoggingConfig.from_env()
        assert config.log_level == "debug"

    def test_from_env_all_log_levels(self, clean_env: None) -> None:
        valid_levels: list[LevelName] = ["debug", "info", "warning", "error", "critical"]
        for level in valid_levels:
            os.environ["MIXSEEK_LOG_LEVEL"] = level
            config = LoggingConfig.from_env()
            assert config.log_level == level

    def test_from_env_console_disabled(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"
        config = LoggingConfig.from_env()
        assert config.console_enabled is False

    def test_from_env_console_enabled(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "true"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

    def test_from_env_file_disabled(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_FILE"] = "false"
        config = LoggingConfig.from_env()
        assert config.file_enabled is False

    def test_from_env_file_enabled(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_FILE"] = "true"
        config = LoggingConfig.from_env()
        assert config.file_enabled is True

    def test_from_env_log_format_json(self, clean_env: None) -> None:
        """MIXSEEK_LOG_FORMAT=json を読み取る"""
        os.environ["MIXSEEK_LOG_FORMAT"] = "json"
        config = LoggingConfig.from_env()
        assert config.log_format == "json"

    def test_from_env_log_format_text(self, clean_env: None) -> None:
        """MIXSEEK_LOG_FORMAT=text を読み取る"""
        os.environ["MIXSEEK_LOG_FORMAT"] = "text"
        config = LoggingConfig.from_env()
        assert config.log_format == "text"

    def test_from_env_log_format_default(self, clean_env: None) -> None:
        """MIXSEEK_LOG_FORMAT 未設定時はデフォルト "text" """
        config = LoggingConfig.from_env()
        assert config.log_format == "text"

    def test_from_env_all_settings(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_LEVEL"] = "warning"
        os.environ["MIXSEEK_LOG_CONSOLE"] = "false"
        os.environ["MIXSEEK_LOG_FILE"] = "false"
        os.environ["MIXSEEK_LOG_FORMAT"] = "json"

        config = LoggingConfig.from_env()

        assert config.log_level == "warning"
        assert config.console_enabled is False
        assert config.file_enabled is False
        assert config.log_format == "json"

    def test_from_env_invalid_log_level(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_LEVEL"] = "invalid_level"
        with pytest.raises(ValueError, match="invalid_level"):
            LoggingConfig.from_env()

    def test_from_env_invalid_log_format(self, clean_env: None) -> None:
        """不正なログ形式でValueErrorが発生する"""
        os.environ["MIXSEEK_LOG_FORMAT"] = "xml"
        with pytest.raises(ValueError, match="xml"):
            LoggingConfig.from_env()

    def test_from_env_case_insensitive_boolean(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "TRUE"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        os.environ["MIXSEEK_LOG_CONSOLE"] = "True"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        os.environ["MIXSEEK_LOG_FILE"] = "FALSE"
        config = LoggingConfig.from_env()
        assert config.file_enabled is False

    def test_from_env_numeric_boolean(self, clean_env: None) -> None:
        os.environ["MIXSEEK_LOG_CONSOLE"] = "1"
        config = LoggingConfig.from_env()
        assert config.console_enabled is True

        os.environ["MIXSEEK_LOG_FILE"] = "1"
        config = LoggingConfig.from_env()
        assert config.file_enabled is True

        os.environ["MIXSEEK_LOG_CONSOLE"] = "0"
        config = LoggingConfig.from_env()
        assert config.console_enabled is False

        os.environ["MIXSEEK_LOG_FILE"] = "0"
        config = LoggingConfig.from_env()
        assert config.file_enabled is False


class TestLogLevelValidation:
    """ログレベルバリデーション"""

    def test_valid_levels(self) -> None:
        valid_levels: list[LevelName] = ["debug", "info", "warning", "error", "critical"]
        for level in valid_levels:
            config = LoggingConfig(log_level=level)
            assert config.log_level == level

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid"):
            LoggingConfig(log_level="invalid")  # type: ignore[arg-type]
