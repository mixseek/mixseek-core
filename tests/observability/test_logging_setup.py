"""setup_logging() 統一ロガーのテスト。

"mixseek" named loggerを使用する4モード（logfire有無 x text/json）対応。
TextFormatter, JsonFormatter, SkipTracesFilter のユニットテストを含む。
"""

import json
import logging
from collections.abc import Generator
from pathlib import Path

import pytest

from mixseek.config.logging import LoggingConfig
from mixseek.observability.logging_setup import (
    JsonFormatter,
    SkipTracesFilter,
    TextFormatter,
    setup_logging,
)

LOGGER_NAME = "mixseek"


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """テスト用一時ワークスペースディレクトリを作成"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None]:
    """テスト後にロガーをリセット"""
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)
    # root loggerもクリア（テスト汚染防止）
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


class TestSetupLoggingNamedLogger:
    """ "mixseek" named logger の基本動作テスト"""

    def test_uses_named_logger_not_root(self, temp_workspace: Path) -> None:
        """root logger ではなく "mixseek" named logger を使用"""
        root = logging.getLogger()
        root_handler_count_before = len(root.handlers)

        config = LoggingConfig()
        logger = setup_logging(config, temp_workspace)

        assert logger.name == LOGGER_NAME

        # root logger にハンドラが追加されていないこと（pytestのハンドラは除外）
        assert len(root.handlers) == root_handler_count_before

    def test_propagate_false(self, temp_workspace: Path) -> None:
        """propagate=False が設定される"""
        config = LoggingConfig()
        logger = setup_logging(config, temp_workspace)

        assert logger.propagate is False

    def test_returns_logger(self, temp_workspace: Path) -> None:
        """setup_logging が Logger を返す"""
        config = LoggingConfig()
        result = setup_logging(config, temp_workspace)

        assert isinstance(result, logging.Logger)

    def test_fd_leak_prevention(self, temp_workspace: Path) -> None:
        """再呼び出し時に既存ハンドラが close される（FDリーク防止）"""
        config = LoggingConfig()
        setup_logging(config, temp_workspace)

        logger = logging.getLogger(LOGGER_NAME)
        old_handlers = list(logger.handlers)
        file_handlers = [h for h in old_handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0

        # ストリームを事前に保持（close後にNoneになる場合がある）
        streams = [h.stream for h in file_handlers]
        assert all(s is not None for s in streams)

        # 再度呼び出し
        setup_logging(config, temp_workspace)

        # 旧ハンドラのストリームがクローズされている
        for stream in streams:
            assert stream.closed


class TestSetupLoggingLogLevel:
    """ログレベル設定テスト"""

    def test_default_info_level(self, temp_workspace: Path) -> None:
        config = LoggingConfig()
        logger = setup_logging(config, temp_workspace)
        assert logger.level == logging.INFO

    def test_debug_level(self, temp_workspace: Path) -> None:
        config = LoggingConfig(log_level="debug")
        logger = setup_logging(config, temp_workspace)
        assert logger.level == logging.DEBUG

    def test_warning_level(self, temp_workspace: Path) -> None:
        config = LoggingConfig(log_level="warning")
        logger = setup_logging(config, temp_workspace)
        assert logger.level == logging.WARNING

    def test_error_level(self, temp_workspace: Path) -> None:
        config = LoggingConfig(log_level="error")
        logger = setup_logging(config, temp_workspace)
        assert logger.level == logging.ERROR


class TestMode1LogfireDisabledText:
    """Mode 1: logfire無効 + text"""

    def test_handlers_present(self, temp_workspace: Path) -> None:
        """StreamHandler + FileHandler が存在"""
        config = LoggingConfig(log_format="text")
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types

    def test_text_formatter_used(self, temp_workspace: Path) -> None:
        """TextFormatter が使用されている"""
        config = LoggingConfig(log_format="text")
        logger = setup_logging(config, temp_workspace)

        for h in logger.handlers:
            if isinstance(h, (logging.StreamHandler, logging.FileHandler)):
                assert isinstance(h.formatter, TextFormatter)

    def test_log_dir_created(self, temp_workspace: Path) -> None:
        """logs ディレクトリが作成される"""
        config = LoggingConfig(log_format="text")
        setup_logging(config, temp_workspace)

        log_dir = temp_workspace / "logs"
        assert log_dir.exists()

    def test_log_file_receives_messages(self, temp_workspace: Path) -> None:
        """ログファイルにメッセージが記録される"""
        config = LoggingConfig(log_format="text")
        logger = setup_logging(config, temp_workspace)

        logger.info("Test message for file")

        log_file = temp_workspace / "logs" / "mixseek.log"
        content = log_file.read_text()
        assert "Test message for file" in content


class TestMode2LogfireDisabledJson:
    """Mode 2: logfire無効 + json"""

    def test_handlers_present(self, temp_workspace: Path) -> None:
        """StreamHandler + FileHandler が存在"""
        config = LoggingConfig(log_format="json")
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types

    def test_json_formatter_used(self, temp_workspace: Path) -> None:
        """JsonFormatter が使用されている"""
        config = LoggingConfig(log_format="json")
        logger = setup_logging(config, temp_workspace)

        for h in logger.handlers:
            if isinstance(h, (logging.StreamHandler, logging.FileHandler)):
                assert isinstance(h.formatter, JsonFormatter)

    def test_json_output_has_type_log(self, temp_workspace: Path) -> None:
        """JSON出力に type: "log" フィールドが含まれる"""
        config = LoggingConfig(log_format="json")
        logger = setup_logging(config, temp_workspace)

        logger.info("Test JSON message")

        log_file = temp_workspace / "logs" / "mixseek.log"
        content = log_file.read_text().strip()
        data = json.loads(content)
        assert data["type"] == "log"

    def test_json_output_extra_fields_toplevel(self, temp_workspace: Path) -> None:
        """JSON出力で extra fields がトップレベルキーとして出力"""
        config = LoggingConfig(log_format="json")
        logger = setup_logging(config, temp_workspace)

        logger.info("Test", extra={"agent": "researcher", "score": 0.85})

        log_file = temp_workspace / "logs" / "mixseek.log"
        content = log_file.read_text().strip()
        data = json.loads(content)
        assert data["agent"] == "researcher"
        assert data["score"] == 0.85


class TestMode3LogfireEnabledText:
    """Mode 3: logfire有効 + text

    setup_logging() 直後は StreamHandler + FileHandler + LogfireLoggingHandler が全て存在。
    finalize_mode3_handlers() 呼び出し後に StreamHandler/FileHandler が除去される。
    """

    def test_initial_handlers_all_present(self, temp_workspace: Path) -> None:
        """setup_logging() 直後: StreamHandler + FileHandler + LogfireLoggingHandler が存在"""
        config = LoggingConfig(logfire_enabled=True, log_format="text")
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types
        # LogfireLoggingHandler は logfire パッケージがインストールされている場合のみ
        # CI環境ではインストール済みなので検証する
        try:
            import logfire  # noqa: F401

            assert "LogfireLoggingHandler" in handler_types, (
                "logfire がインストールされているが LogfireLoggingHandler が追加されていない"
            )
        except ImportError:
            pass  # logfire 未インストールの場合はスキップ

    def test_finalize_removes_stream_and_file_handlers(self, temp_workspace: Path) -> None:
        """finalize_mode3_handlers() 後: StreamHandler/FileHandler が除去"""
        from mixseek.observability.logfire import finalize_mode3_handlers

        config = LoggingConfig(logfire_enabled=True, log_format="text")
        setup_logging(config, temp_workspace)

        finalize_mode3_handlers()

        logger = logging.getLogger(LOGGER_NAME)
        remaining_types = [type(h).__name__ for h in logger.handlers]
        # StreamHandler と FileHandler は除去されている
        # （LogfireLoggingHandler が残る場合あり）
        stream_or_file = [t for t in remaining_types if t in ("StreamHandler", "FileHandler")]
        assert len(stream_or_file) == 0


class TestMode4LogfireEnabledJson:
    """Mode 4: logfire有効 + json"""

    def test_handlers_present(self, temp_workspace: Path) -> None:
        """StreamHandler + FileHandler が存在"""
        config = LoggingConfig(logfire_enabled=True, log_format="json")
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types

    def test_json_formatter_used(self, temp_workspace: Path) -> None:
        """JsonFormatter が使用されている"""
        config = LoggingConfig(logfire_enabled=True, log_format="json")
        logger = setup_logging(config, temp_workspace)

        for h in logger.handlers:
            if isinstance(h, (logging.StreamHandler, logging.FileHandler)):
                assert isinstance(h.formatter, JsonFormatter)

    def test_skip_traces_filter_on_logfire_handler(self, temp_workspace: Path) -> None:
        """LogfireLoggingHandler に SkipTracesFilter が設定されている"""
        config = LoggingConfig(logfire_enabled=True, log_format="json")
        logger = setup_logging(config, temp_workspace)

        # logfire インストール済みの場合は必ず検証
        try:
            import logfire  # noqa: F401

            logfire_handlers = [h for h in logger.handlers if type(h).__name__ == "LogfireLoggingHandler"]
            assert len(logfire_handlers) > 0, "LogfireLoggingHandler が追加されていない"
            handler = logfire_handlers[0]
            filter_types = [type(f).__name__ for f in handler.filters]
            assert "SkipTracesFilter" in filter_types
        except ImportError:
            pytest.skip("logfire がインストールされていないためスキップ")


class TestSetupLoggingDisableOutputs:
    """出力無効化テスト"""

    def test_disable_console(self, temp_workspace: Path) -> None:
        config = LoggingConfig(console_enabled=False)
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" not in handler_types
        assert "FileHandler" in handler_types

    def test_disable_file(self, temp_workspace: Path) -> None:
        config = LoggingConfig(file_enabled=False)
        logger = setup_logging(config, temp_workspace)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" not in handler_types

    def test_disable_both_silent_mode(self, temp_workspace: Path) -> None:
        """両方無効でNullHandler（サイレントモード）"""
        config = LoggingConfig(console_enabled=False, file_enabled=False)
        logger = setup_logging(config, temp_workspace)

        non_null = [h for h in logger.handlers if not isinstance(h, logging.NullHandler)]
        assert len(non_null) == 0


class TestSetupLoggingNoWorkspace:
    """ワークスペースなしのテスト"""

    def test_no_workspace_console_only(self) -> None:
        config = LoggingConfig()
        logger = setup_logging(config, workspace=None)

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types
        assert "FileHandler" not in handler_types


class TestTextFormatter:
    """TextFormatter のユニットテスト"""

    def test_no_extra_fields(self) -> None:
        """extra fields なし: メッセージ行のみ"""
        fmt = TextFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Simple message",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        assert "Simple message" in output
        assert "\n" not in output  # 1行のみ

    def test_with_extra_fields(self) -> None:
        """extra fields あり: 別行 key: value 形式"""
        fmt = TextFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Agent started",
            args=(),
            exc_info=None,
        )
        record.agent = "researcher"
        record.score = 0.85

        output = fmt.format(record)
        lines = output.split("\n")
        assert len(lines) >= 2  # メッセージ + extra fields
        assert "  agent: researcher" in output
        assert "  score: 0.85" in output

    def test_multiple_extra_fields(self) -> None:
        """複数 extra fields が個別行で出力"""
        fmt = TextFormatter("%(message)s")
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.field1 = "value1"
        record.field2 = "value2"
        record.field3 = "value3"

        output = fmt.format(record)
        lines = output.split("\n")
        assert len(lines) >= 4  # メッセージ + 3 extra fields


class TestJsonFormatter:
    """JsonFormatter のユニットテスト"""

    def test_basic_fields(self) -> None:
        """基本フィールド（timestamp, type, level, logger, message）が含まれる"""
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="mixseek.agents",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)

        assert "timestamp" in data
        assert data["type"] == "log"
        assert data["level"] == "INFO"
        assert data["logger"] == "mixseek.agents"
        assert data["message"] == "Test message"

    def test_extra_fields_toplevel(self) -> None:
        """extra fields がトップレベルキーとして出力"""
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.agent = "researcher"
        record.score = 0.85

        output = fmt.format(record)
        data = json.loads(output)

        assert data["agent"] == "researcher"
        assert data["score"] == 0.85

    def test_type_is_log(self) -> None:
        """type: "log" が設定される"""
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["type"] == "log"


class TestSkipTracesFilter:
    """SkipTracesFilter のユニットテスト"""

    def test_filters_traces_logger(self) -> None:
        """'mixseek.traces' ロガーのレコードがフィルタされる"""
        f = SkipTracesFilter()
        record = logging.LogRecord(
            name="mixseek.traces",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Span data",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False

    def test_allows_agents_logger(self) -> None:
        """'mixseek.agents' ロガーのレコードはフィルタされない"""
        f = SkipTracesFilter()
        record = logging.LogRecord(
            name="mixseek.agents",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Agent log",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_allows_root_mixseek_logger(self) -> None:
        """'mixseek' ロガーのレコードはフィルタされない"""
        f = SkipTracesFilter()
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Root log",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True
