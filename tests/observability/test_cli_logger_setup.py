"""mixseek.cli logger セットアップ (logging_setup 内) のユニットテスト。

- フォーマッタ (CLITextFormatter / CLIJsonFormatter) 単体の挙動
- logger セットアップ (setup_cli_logger / early_setup_cli_logger_from_env / get_cli_logger)
  の副作用 (handler 構成・出力先・propagate)
- 実行時に stderr / stdout に書かれる内容
"""

from __future__ import annotations

import io
import json
import logging
import sys
from collections.abc import Generator
from typing import Any

import pytest

from mixseek.observability.logging_setup import (
    CLIJsonFormatter,
    CLITextFormatter,
    _force_reset_cli_logger,
    early_setup_cli_logger_from_env,
    get_cli_logger,
    setup_cli_logger,
)

_CLI_LOGGER_NAME = "mixseek.cli"


@pytest.fixture(autouse=True)
def _reset_cli_logger(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """各テスト前後で CLI logger の状態を初期化する。"""
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
    _force_reset_cli_logger()
    yield
    _force_reset_cli_logger()


def _make_record(
    level: int,
    message: str,
    *,
    name: str = "mixseek.cli",
    extra: dict[str, Any] | None = None,
) -> logging.LogRecord:
    """テスト用に LogRecord を組み立てる。"""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def _swap_stderr(buf: io.StringIO) -> Any:
    """sys.stderr を buf に差し替え、元の stderr を返す。"""
    original = sys.stderr
    sys.stderr = buf
    return original


# ---------------------------------------------------------------------------
# CLITextFormatter
# ---------------------------------------------------------------------------


class TestCLITextFormatter:
    """text モード: メッセージ本文のみ (ANSI 除去) を検証。"""

    def test_plain_message_is_returned_as_is(self) -> None:
        formatter = CLITextFormatter()
        record = _make_record(logging.INFO, "hello")
        assert formatter.format(record) == "hello"

    def test_ansi_is_stripped_from_message(self) -> None:
        """caller が入れた ANSI は常に除去される (色なし方針)。"""
        formatter = CLITextFormatter()
        record = _make_record(logging.ERROR, "\x1b[31malready red\x1b[0m")
        assert formatter.format(record) == "already red"

    @pytest.mark.parametrize("level", [logging.DEBUG, logging.WARNING, logging.ERROR, logging.CRITICAL])
    def test_no_level_auto_color(self, level: int) -> None:
        """level に応じた自動着色は行わない。ANSI が出力に混入しない。"""
        formatter = CLITextFormatter()
        record = _make_record(level, "alert")
        output = formatter.format(record)
        assert "\x1b[" not in output
        assert output == "alert"


# ---------------------------------------------------------------------------
# CLIJsonFormatter
# ---------------------------------------------------------------------------


class TestCLIJsonFormatter:
    """json モード: 1 行 JSON + schema 不変キー保護 + ANSI 除去を検証。"""

    def _format_json(self, record: logging.LogRecord) -> dict[str, Any]:
        output = CLIJsonFormatter().format(record)
        assert "\n" not in output, "JSON 出力は 1 行であるべき"
        payload: dict[str, Any] = json.loads(output)
        return payload

    def test_basic_payload_shape(self) -> None:
        record = _make_record(logging.INFO, "loaded")
        payload = self._format_json(record)
        assert payload["type"] == "log"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "mixseek.cli"
        assert payload["message"] == "loaded"
        assert "timestamp" in payload

    def test_extra_fields_appear_at_top_level(self) -> None:
        record = _make_record(logging.INFO, "x", extra={"event": "team.info", "team_id": "t-1"})
        payload = self._format_json(record)
        assert payload["event"] == "team.info"
        assert payload["team_id"] == "t-1"

    def test_message_ansi_is_stripped(self) -> None:
        record = _make_record(logging.INFO, "\x1b[36mcyan\x1b[0m section")
        payload = self._format_json(record)
        assert payload["message"] == "cyan section"

    @pytest.mark.parametrize("reserved_key", ["timestamp", "type", "level", "logger", "message"])
    def test_schema_keys_are_not_overwritten_by_extra(self, reserved_key: str) -> None:
        """extra に schema 不変キーと同名エントリがあっても正規値は保持される。"""
        record = _make_record(logging.WARNING, "legit", extra={reserved_key: "HIJACK"})
        payload = self._format_json(record)
        assert payload[reserved_key] != "HIJACK"
        assert payload["type"] == "log"
        assert payload["level"] == "WARNING"
        assert payload["logger"] == "mixseek.cli"
        assert payload["message"] == "legit"

    def test_non_json_serializable_extra_falls_back_to_str(self) -> None:
        from pathlib import Path

        record = _make_record(logging.INFO, "x", extra={"workspace_path": Path("/tmp/ws")})
        payload = self._format_json(record)
        assert payload["workspace_path"] == "/tmp/ws"


# ---------------------------------------------------------------------------
# setup_cli_logger
# ---------------------------------------------------------------------------


class TestSetupCliLogger:
    """``mixseek.cli`` logger のセットアップ挙動を検証。"""

    def test_text_mode_uses_cli_text_formatter(self) -> None:
        logger = setup_cli_logger("text")
        assert logger.name == _CLI_LOGGER_NAME
        assert logger.propagate is False
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, CLITextFormatter)

    def test_json_mode_uses_cli_json_formatter(self) -> None:
        logger = setup_cli_logger("json")
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, CLIJsonFormatter)

    def test_reinit_clears_previous_handlers(self) -> None:
        """2 度目の setup_cli_logger で handler が重複しない。"""
        setup_cli_logger("text")
        setup_cli_logger("json")
        logger = get_cli_logger()
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, CLIJsonFormatter)

    def test_text_mode_output_reaches_stderr_without_color(self) -> None:
        """text モードでは色なし・プレーンテキストで stderr に出力される。"""
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            setup_cli_logger("text")
            get_cli_logger().error("boom")
        finally:
            sys.stderr = original
        output = buf.getvalue()
        assert output == "boom\n"
        assert "\x1b[" not in output

    def test_json_mode_output_reaches_stderr(self) -> None:
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            setup_cli_logger("json")
            get_cli_logger().error("boom", extra={"event": "test.event", "k": "v"})
        finally:
            sys.stderr = original
        payload = json.loads(buf.getvalue().rstrip("\n"))
        assert payload["type"] == "log"
        assert payload["level"] == "ERROR"
        assert payload["logger"] == "mixseek.cli"
        assert payload["message"] == "boom"
        assert payload["event"] == "test.event"
        assert payload["k"] == "v"

    def test_propagate_is_false(self) -> None:
        """mixseek.cli は親 mixseek logger の handler (Logfire/File) に伝播しない。"""
        logger = setup_cli_logger("text")
        assert logger.propagate is False


# ---------------------------------------------------------------------------
# early_setup_cli_logger_from_env
# ---------------------------------------------------------------------------


class TestEarlySetupCliLoggerFromEnv:
    """env var ベースの bootstrap 初期化を検証。"""

    def test_no_env_defaults_to_text(self) -> None:
        early_setup_cli_logger_from_env()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLITextFormatter)

    @pytest.mark.parametrize("env_value", ["json", "JSON", "Json"])
    def test_env_json_is_case_insensitive(self, monkeypatch: pytest.MonkeyPatch, env_value: str) -> None:
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", env_value)
        early_setup_cli_logger_from_env()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLIJsonFormatter)

    @pytest.mark.parametrize("invalid_value", ["Jsno", "yaml", "", " "])
    def test_invalid_env_falls_back_to_text(self, monkeypatch: pytest.MonkeyPatch, invalid_value: str) -> None:
        """不正値や表記揺れ (json 以外) は text に fallback する。"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", invalid_value)
        early_setup_cli_logger_from_env()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLITextFormatter)


# ---------------------------------------------------------------------------
# get_cli_logger (未初期化時の安全な既定値)
# ---------------------------------------------------------------------------


class TestGetCliLoggerSafeDefault:
    """setup_cli_logger 前の get_cli_logger アクセスが安全であることを検証。"""

    def test_unconfigured_logger_has_null_handler(self) -> None:
        logger = get_cli_logger()
        assert logger.propagate is False
        assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)

    def test_unconfigured_logger_does_not_leak_to_stderr(self) -> None:
        """未初期化時に logger.error を呼んでも stderr には何も出ない。"""
        buf = io.StringIO()
        original = _swap_stderr(buf)
        try:
            get_cli_logger().error("should not appear")
        finally:
            sys.stderr = original
        assert buf.getvalue() == ""
