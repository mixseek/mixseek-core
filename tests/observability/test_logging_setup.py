"""setup_logging() / early_setup_logging_from_env() ロガーのテスト。

- ``mixseek`` named logger (4 モード = logfire 有無 x text/json) のセットアップ
- ``mixseek.cli`` 子 logger の親 ``mixseek`` への伝搬と統合出力
- env var ベースの早期 bootstrap
- TextFormatter / JsonFormatter / SkipTracesFilter のユニットテスト
"""

import io
import json
import logging
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from mixseek.config.logging import LoggingConfig
from mixseek.observability.logging_setup import (
    JsonFormatter,
    SkipTracesFilter,
    TextFormatter,
    early_setup_logging_from_env,
    setup_logging,
)

LOGGER_NAME = "mixseek"
_CLI_LOGGER_NAME = "mixseek.cli"


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """テスト用一時ワークスペースディレクトリを作成"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture(autouse=True)
def reset_logging(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """テスト前後でロガーをリセット。

    モジュール import 時に attach される NullHandler を再 attach することで、
    setup_logging 未呼び出しテストでも root / lastResort への leak を防ぐ。
    """
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
    monkeypatch.delenv("MIXSEEK_LOG_LEVEL", raising=False)
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    # 本番と同じ leak 防止 NullHandler を attach し直す
    logger.addHandler(logging.NullHandler())
    # root loggerもクリア（テスト汚染防止）
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def _swap_stderr(buf: io.StringIO) -> Any:
    """sys.stderr を buf に差し替え、元の stderr を返す。"""
    original = sys.stderr
    sys.stderr = buf
    return original


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

    def test_schema_keys_not_overwritten_by_extra(self) -> None:
        """extra がスキーマ不変キー (type/timestamp/level/logger/message) を上書きしない"""
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="mixseek",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # スキーマ予約キーと同名の extra を付与（logger.info(msg, extra={...}) 相当）
        record.type = "user_event"
        record.timestamp = "overwritten"
        record.level = "FATAL"
        record.logger = "other.logger"

        output = fmt.format(record)
        data = json.loads(output)

        # スキーマは安定
        assert data["type"] == "log"
        assert data["level"] == "INFO"
        assert data["logger"] == "mixseek"
        assert data["message"] == "Test message"
        # timestamp は ISO 形式 (上書きされていない)
        assert data["timestamp"] != "overwritten"
        assert "T" in data["timestamp"]


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


# ---------------------------------------------------------------------------
# mixseek.cli logger 統合
# ---------------------------------------------------------------------------


class TestCliLoggerIntegration:
    """``mixseek.cli`` が親 ``mixseek`` に伝搬し、共通ハンドラから出力されることを検証。

    フル統合方針: CLI イベントは独立 logger ではなく親 ``mixseek`` の handler チェーン
    (stderr / mixseek.log / Logfire cloud) を経由する。
    """

    def test_propagates_to_parent(self) -> None:
        """mixseek.cli は親 mixseek に伝搬する (propagate=True デフォルト)"""
        cli_logger = logging.getLogger(_CLI_LOGGER_NAME)
        assert cli_logger.propagate is True
        assert cli_logger.parent is logging.getLogger(LOGGER_NAME)

    def test_no_own_handlers_after_setup(self) -> None:
        """mixseek.cli は独自 handler を持たない (親 mixseek に依存)"""
        config = LoggingConfig()
        setup_logging(config, workspace=None)
        cli_logger = logging.getLogger(_CLI_LOGGER_NAME)
        assert cli_logger.handlers == []

    def test_text_mode_output_reaches_stderr(self) -> None:
        """text モード: cli ロガー経由のメッセージが親の stderr handler から出る"""
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            config = LoggingConfig(log_format="text", file_enabled=False)
            setup_logging(config, workspace=None)
            logging.getLogger(_CLI_LOGGER_NAME).error("boom")
        finally:
            sys.stderr = original
        output = buf.getvalue()
        assert "boom" in output
        assert " - mixseek.cli - ERROR - " in output
        assert output.endswith("\n")

    def test_json_mode_output_reaches_stderr(self) -> None:
        """json モード: cli ロガー経由のメッセージが JSON で stderr に届く"""
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            config = LoggingConfig(log_format="json", file_enabled=False)
            setup_logging(config, workspace=None)
            logging.getLogger(_CLI_LOGGER_NAME).error("boom", extra={"event": "test.event", "k": "v"})
        finally:
            sys.stderr = original
        payload = json.loads(buf.getvalue().rstrip("\n"))
        assert payload["type"] == "log"
        assert payload["level"] == "ERROR"
        assert payload["logger"] == "mixseek.cli"
        assert payload["message"] == "boom"
        assert payload["event"] == "test.event"
        assert payload["k"] == "v"

    def test_cli_events_flow_to_log_file(self, temp_workspace: Path) -> None:
        """フル統合: CLI イベントは mixseek.log にも記録される (旧来は stderr only)"""
        config = LoggingConfig(log_format="text")
        setup_logging(config, temp_workspace)
        logging.getLogger(_CLI_LOGGER_NAME).info("test cli event")
        log_file = temp_workspace / "logs" / "mixseek.log"
        content = log_file.read_text()
        assert "test cli event" in content
        assert "mixseek.cli" in content


class TestEarlySetupLoggingFromEnv:
    """env var ベースの ``mixseek`` bootstrap 初期化を検証。"""

    def _stream_handlers(self, logger: logging.Logger) -> list[logging.Handler]:
        """FileHandler を除く StreamHandler のみを抽出 (厳密型一致)。"""
        return [h for h in logger.handlers if type(h) is logging.StreamHandler]

    def test_no_env_defaults_to_text(self) -> None:
        logger = early_setup_logging_from_env()
        handlers = self._stream_handlers(logger)
        assert handlers
        assert all(isinstance(h.formatter, TextFormatter) for h in handlers)

    @pytest.mark.parametrize("env_value", ["json", "JSON", "Json"])
    def test_env_json_is_case_insensitive(self, monkeypatch: pytest.MonkeyPatch, env_value: str) -> None:
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", env_value)
        logger = early_setup_logging_from_env()
        handlers = self._stream_handlers(logger)
        assert handlers
        assert all(isinstance(h.formatter, JsonFormatter) for h in handlers)

    def test_invalid_log_level_falls_back_to_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """不正な MIXSEEK_LOG_LEVEL でも fallback して例外が漏れない"""
        monkeypatch.setenv("MIXSEEK_LOG_LEVEL", "invalid_level")
        logger = early_setup_logging_from_env()
        assert logger.name == LOGGER_NAME
        # default fallback: INFO level
        assert logger.level == logging.INFO

    def test_bootstrap_disables_file_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """bootstrap では file/logfire は無効 (workspace 未解決のため)"""
        monkeypatch.setenv("MIXSEEK_LOG_FILE", "true")
        logger = early_setup_logging_from_env()
        assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_bootstrap_cli_logger_emits_via_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """bootstrap 後、cli ロガー呼び出しが親経由で stderr に届く"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            early_setup_logging_from_env()
            logging.getLogger(_CLI_LOGGER_NAME).error("early boom")
        finally:
            sys.stderr = original
        payload = json.loads(buf.getvalue().rstrip("\n"))
        assert payload["logger"] == "mixseek.cli"
        assert payload["message"] == "early boom"


class TestUnconfiguredLoggerSafety:
    """setup_logging 前の logger アクセスが leak しないことを検証。"""

    def test_unconfigured_does_not_leak_to_stderr(self) -> None:
        """setup_logging 未呼び出しでも NullHandler により root / stderr に leak しない"""
        # autouse fixture が teardown 時に NullHandler を attach する設計のため、
        # 本テストでは明示的に NullHandler のみが付いた状態を再現する
        logger = logging.getLogger(LOGGER_NAME)
        for h in logger.handlers:
            h.close()
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())

        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            logging.getLogger(_CLI_LOGGER_NAME).error("should not appear")
        finally:
            sys.stderr = original
        assert buf.getvalue() == ""
