"""CLITextFormatter / CLIJsonFormatter / BareFormatter のユニットテスト。

formatter 単体の振る舞い (ANSI 着色 / level 着色 / schema 不変キー / ANSI 除去 /
bare 出力) を LogRecord を直接組み立てて検証する。
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Generator
from typing import Any

import pytest

from mixseek.cli.output_formatter import BareFormatter, CLIJsonFormatter, CLITextFormatter


class _FakeTTY(io.StringIO):
    """``isatty()`` が ``True`` を返す StringIO 派生。TTY 時のカラー判定に使う。"""

    def isatty(self) -> bool:
        return True


class _FakePipe(io.StringIO):
    """``isatty()`` が ``False`` を返す StringIO 派生 (パイプ想定)。"""

    def isatty(self) -> bool:
        return False


def _make_record(
    level: int,
    message: str,
    *,
    name: str = "mixseek.cli",
    extra: dict[str, Any] | None = None,
) -> logging.LogRecord:
    """テスト用に LogRecord を組み立てる。

    extra は ``LogRecord.__dict__`` に直接挿すので、``level`` / ``message`` など
    LogRecord 標準属性と同名のキーも渡せる (``setattr`` で上書きするため、
    関数仮引数との衝突は起きない)。
    """
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


@pytest.fixture(autouse=True)
def _clear_no_color(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """NO_COLOR が dev 環境に残っていてもテストに影響しないように常に外しておく。"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    yield


# ---------------------------------------------------------------------------
# CLITextFormatter
# ---------------------------------------------------------------------------


class TestCLITextFormatter:
    """text モード: メッセージ本文のみ + level 自動着色 (TTY のみ) を検証。"""

    def test_info_on_tty_has_no_auto_color(self) -> None:
        """INFO は色付けテーブルにないため、メッセージがそのまま出る (TTY でも)。"""
        stream = _FakeTTY()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(logging.INFO, "hello")
        assert formatter.format(record) == "hello"

    @pytest.mark.parametrize(
        "level,expected_fragment",
        [
            (logging.DEBUG, "\x1b[90m"),  # bright_black
            (logging.WARNING, "\x1b[33m"),  # yellow
            (logging.ERROR, "\x1b[31m"),  # red
            (logging.CRITICAL, "\x1b[31m"),  # red + bold
        ],
    )
    def test_auto_color_applied_on_tty(self, level: int, expected_fragment: str) -> None:
        stream = _FakeTTY()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(level, "alert")
        output = formatter.format(record)
        assert expected_fragment in output
        assert "alert" in output
        assert output.endswith("\x1b[0m")

    def test_critical_is_bold(self) -> None:
        stream = _FakeTTY()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(logging.CRITICAL, "doom")
        # click.style で bold=True は \x1b[1m を付ける。
        assert "\x1b[1m" in formatter.format(record)

    def test_non_tty_strips_ansi_from_message(self) -> None:
        """非 TTY に出すときは caller が入れた ANSI も除去される。"""
        stream = _FakePipe()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(logging.INFO, "\x1b[36mcyan section\x1b[0m")
        assert formatter.format(record) == "cyan section"

    def test_no_color_env_strips_ansi(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NO_COLOR 指定時は TTY でも ANSI 除去 (level 着色も付かない)。"""
        monkeypatch.setenv("NO_COLOR", "1")
        stream = _FakeTTY()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(logging.ERROR, "\x1b[31malready red\x1b[0m")
        output = formatter.format(record)
        assert "\x1b[" not in output
        assert output == "already red"

    def test_non_tty_does_not_add_auto_color(self) -> None:
        """非 TTY では level 自動着色は無効 (パイプや redirect 先で ANSI が混ざらない)。"""
        stream = _FakePipe()
        formatter = CLITextFormatter(stream=stream)
        record = _make_record(logging.ERROR, "err")
        assert formatter.format(record) == "err"


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
        # 代表的な正規値のサニティ
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
# BareFormatter
# ---------------------------------------------------------------------------


class TestBareFormatter:
    """データ出力用 bare formatter: ``%(message)s`` のみを返す。"""

    def test_returns_message_as_is(self) -> None:
        record = _make_record(logging.INFO, "hello")
        assert BareFormatter().format(record) == "hello"

    def test_level_prefix_not_added(self) -> None:
        """level や logger 名が付かないこと (パイプ契約維持)。"""
        record = _make_record(logging.ERROR, '{"k":1}', name="mixseek.cli.data")
        assert BareFormatter().format(record) == '{"k":1}'
