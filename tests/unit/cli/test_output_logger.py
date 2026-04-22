"""setup_cli_logger / setup_data_logger / _early_setup_cli_loggers のユニットテスト。

logger セットアップの副作用 (handler 構成・フォーマッタ・出力先) と、
実行時に stderr / stdout に書かれる内容を検証する。
"""

from __future__ import annotations

import io
import json
import logging
import sys
from collections.abc import Generator
from typing import Any

import pytest

from mixseek.cli.output_formatter import BareFormatter, CLIJsonFormatter, CLITextFormatter
from mixseek.cli.output_logger import (
    _early_setup_cli_loggers,
    _force_reset_cli_loggers,
    get_cli_logger,
    get_data_logger,
    setup_cli_logger,
    setup_data_logger,
)

_CLI_LOGGER_NAME = "mixseek.cli"
_DATA_LOGGER_NAME = "mixseek.cli.data"


@pytest.fixture(autouse=True)
def _reset_cli_loggers(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """各テスト前後で CLI logger / data logger の状態を初期化する。

    - env var ``MIXSEEK_LOG_FORMAT`` を削除して dev 環境の汚染防止
    - handler を明示的にクリア (テスト間で持ち越さない)
    """
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    _force_reset_cli_loggers()
    yield
    _force_reset_cli_loggers()


class _FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def _swap_stderr(buf: io.StringIO) -> Any:
    """sys.stderr を buf に差し替え、元の stderr を返す。"""
    original = sys.stderr
    sys.stderr = buf
    return original


def _swap_stdout(buf: io.StringIO) -> Any:
    original = sys.stdout
    sys.stdout = buf
    return original


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

    def test_text_mode_output_reaches_stderr(self) -> None:
        buf = _FakeTTY()
        original = _swap_stderr(buf)
        try:
            setup_cli_logger("text")
            get_cli_logger().error("boom")
        finally:
            sys.stderr = original
        output = buf.getvalue()
        # ERROR は red で着色される (TTY なので)
        assert "boom" in output
        assert "\x1b[31m" in output

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


# ---------------------------------------------------------------------------
# setup_data_logger
# ---------------------------------------------------------------------------


class TestSetupDataLogger:
    """``mixseek.cli.data`` logger のセットアップ挙動を検証。"""

    def test_uses_bare_formatter_to_stdout(self) -> None:
        logger = setup_data_logger()
        assert logger.name == _DATA_LOGGER_NAME
        assert logger.propagate is False
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, BareFormatter)

    def test_output_is_bare_on_stdout(self) -> None:
        buf = io.StringIO()
        original = _swap_stdout(buf)
        try:
            setup_data_logger()
            get_data_logger().info('{"k":1}')
        finally:
            sys.stdout = original
        # プレフィックスなし、1 行 JSON がそのまま出る
        assert buf.getvalue() == '{"k":1}\n'

    def test_data_logger_does_not_propagate_to_cli_logger_stderr(self) -> None:
        """data_logger のメッセージは親の ``mixseek.cli`` の stderr handler に伝播しない。"""
        cli_buf = io.StringIO()
        data_buf = io.StringIO()
        orig_err = _swap_stderr(cli_buf)
        orig_out = _swap_stdout(data_buf)
        try:
            setup_cli_logger("text")
            setup_data_logger()
            get_data_logger().info("only on stdout")
        finally:
            sys.stderr = orig_err
            sys.stdout = orig_out
        assert cli_buf.getvalue() == ""
        assert data_buf.getvalue() == "only on stdout\n"


# ---------------------------------------------------------------------------
# _early_setup_cli_loggers
# ---------------------------------------------------------------------------


class TestEarlySetupCliLoggers:
    """env var ベースの bootstrap 初期化を検証。"""

    def test_no_env_defaults_to_text(self) -> None:
        _early_setup_cli_loggers()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLITextFormatter)

    @pytest.mark.parametrize("env_value", ["json", "JSON", "Json"])
    def test_env_json_is_case_insensitive(self, monkeypatch: pytest.MonkeyPatch, env_value: str) -> None:
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", env_value)
        _early_setup_cli_loggers()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLIJsonFormatter)

    @pytest.mark.parametrize("invalid_value", ["Jsno", "yaml", "", " "])
    def test_invalid_env_falls_back_to_text(self, monkeypatch: pytest.MonkeyPatch, invalid_value: str) -> None:
        """不正値や表記揺れ (json 以外) は text に fallback する。"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", invalid_value)
        _early_setup_cli_loggers()
        handler = get_cli_logger().handlers[0]
        assert isinstance(handler.formatter, CLITextFormatter)

    def test_also_initializes_data_logger(self) -> None:
        _early_setup_cli_loggers()
        data_logger = get_data_logger()
        assert len(data_logger.handlers) == 1
        assert isinstance(data_logger.handlers[0].formatter, BareFormatter)
