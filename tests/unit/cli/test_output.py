"""cli_echo / cli_secho ヘルパーのテスト。

text モードでは typer.echo / typer.secho と完全に同一の出力であること、
json モードでは期待する構造化 JSON が stderr / stdout に出力されることを検証する。
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import typer

from mixseek.cli.output import cli_echo, cli_secho
from mixseek.config.logging import LoggingConfig
from mixseek.observability.logging_setup import setup_logging

LOGGER_NAME = "mixseek"


@pytest.fixture(autouse=True)
def reset_logging_state(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """テスト間で logging の state (logger handlers と module 変数) をリセット。"""
    # 環境変数の汚染防止
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)

    yield

    # logger の handlers を cleanup
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)

    # module 変数を pristine 状態に戻す
    from mixseek.observability import logging_setup

    logging_setup._current_log_format = "text"
    logging_setup._setup_logging_called = False


def _enable_json_mode(tmp_path: Path) -> None:
    """setup_logging 経由で json モードを有効化する。"""
    config = LoggingConfig(log_format="json", file_enabled=False, console_enabled=False)
    setup_logging(config, tmp_path)


def _capture_std(
    monkeypatch: pytest.MonkeyPatch,
    action: Callable[[], None],
) -> tuple[str, str]:
    """sys.stdout / sys.stderr を StringIO に差し替えて action を実行し、(stdout, stderr) を返す。"""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", out_buf)
    monkeypatch.setattr("sys.stderr", err_buf)
    try:
        action()
    finally:
        monkeypatch.undo()
    return out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# text モードの出力同一性テスト (typer.echo / typer.secho と完全一致)
# ---------------------------------------------------------------------------


class TestTextModeIdentity:
    """text モードでは typer.echo / typer.secho と完全に同一の出力になる。"""

    @pytest.mark.parametrize(
        "message,kwargs",
        [
            ("hello", {}),
            ("エラー: 設定不正", {"err": True}),
            ("", {}),
            ("", {"err": True}),
            ("multi\nline\ntext", {"err": True}),
        ],
    )
    def test_cli_echo_matches_typer_echo(
        self, message: str, kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        expected = _capture_std(monkeypatch, lambda: typer.echo(message, err=kwargs.get("err", False)))
        actual = _capture_std(monkeypatch, lambda: cli_echo(message, err=kwargs.get("err", False)))
        assert actual == expected

    @pytest.mark.parametrize(
        "message,kwargs",
        [
            ("green text", {"fg": "green"}),
            ("red error", {"fg": "red", "err": True}),
            ("bold warning", {"fg": "yellow", "bold": True, "err": True}),
            ("plain", {}),
        ],
    )
    def test_cli_secho_matches_typer_secho(
        self, message: str, kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # kwargs に bold が無ければ typer.secho / cli_secho の既定 (None) を踏襲する。
        # False を明示してはいけない — `\x1b[22m` (太字無効化) が付いて差分になる。
        def _call(fn: Any) -> None:
            extra: dict[str, Any] = {"err": kwargs.get("err", False), "fg": kwargs.get("fg")}
            if "bold" in kwargs:
                extra["bold"] = kwargs["bold"]
            fn(message, **extra)

        expected = _capture_std(monkeypatch, lambda: _call(typer.secho))
        actual = _capture_std(monkeypatch, lambda: _call(cli_secho))
        assert actual == expected

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"fg": "red", "err": True},
            {"fg": "green"},
            {"fg": "yellow", "err": True},
            {"fg": "yellow", "err": True, "bold": True},
            {},
        ],
    )
    def test_cli_secho_matches_typer_secho_on_tty(
        self, kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TTY 環境で ANSI コードまで含め `typer.secho` と完全一致することを確認する。

        Click は `stream.isatty()` が True のとき ANSI エスケープを出力する。
        bold 未指定時に余分な `\\x1b[22m` (太字無効化) が付かないことをこのテストが検証する。
        """

        class _FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        def _invoke(fn: Any) -> str:
            out = _FakeTTY()
            err = _FakeTTY()
            monkeypatch.setattr("sys.stdout", out)
            monkeypatch.setattr("sys.stderr", err)
            try:
                extra: dict[str, Any] = {"err": kwargs.get("err", False), "fg": kwargs.get("fg")}
                if "bold" in kwargs:
                    extra["bold"] = kwargs["bold"]
                fn("styled", **extra)
            finally:
                monkeypatch.undo()
            return err.getvalue() if kwargs.get("err", False) else out.getvalue()

        expected = _invoke(typer.secho)
        actual = _invoke(cli_secho)
        assert actual == expected
        # 仕様確認: bold 未指定時は `\x1b[22m` が入らない。
        if "bold" not in kwargs and kwargs.get("fg"):
            assert "\x1b[22m" not in actual

    def test_extra_fields_ignored_in_text_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """text モードでは event / extra fields は無視され、typer.echo 同等の出力になる。"""
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo(
                "loaded",
                err=True,
                event="evaluate.config_loaded",
                path="/x.toml",
                nested={"k": 1},
            ),
        )
        assert out == ""
        assert err == "loaded\n"


# ---------------------------------------------------------------------------
# json モードの出力構造テスト
# ---------------------------------------------------------------------------


def _capture_cli_echo_json(
    tmp_path: Path,
    message: str,
    *,
    err: bool = False,
    event: str | None = None,
    use_secho: bool = False,
    fg: str | None = None,
    bold: bool = False,
    monkeypatch: pytest.MonkeyPatch,
    **fields: Any,
) -> tuple[dict[str, Any], str]:
    """json モードで cli_echo / cli_secho を呼び、出力行を dict で返す。

    Returns:
        (payload_dict, stream_name) — stream_name は "stdout" or "stderr"
    """
    _enable_json_mode(tmp_path)

    def _do() -> None:
        if use_secho:
            cli_secho(message, err=err, fg=fg, bold=bold, event=event, **fields)
        else:
            cli_echo(message, err=err, event=event, **fields)

    out, err_str = _capture_std(monkeypatch, _do)

    if err:
        raw = err_str
        stream = "stderr"
        assert out == ""
    else:
        raw = out
        stream = "stdout"
        assert err_str == ""

    assert raw.endswith("\n"), "JSON 出力は改行で終わるべき"
    return json.loads(raw.rstrip("\n")), stream


class TestJsonModeOutput:
    """json モードでは構造化 JSON を 1 行で stderr/stdout に出力する。"""

    def test_basic_payload_shape(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, stream = _capture_cli_echo_json(
            tmp_path,
            "Loading custom config: /x.toml",
            err=True,
            event="evaluate.config_loaded",
            monkeypatch=monkeypatch,
            path="/x.toml",
        )
        assert stream == "stderr"
        assert payload["type"] == "cli"
        assert payload["event"] == "evaluate.config_loaded"
        assert payload["message"] == "Loading custom config: /x.toml"
        assert payload["path"] == "/x.toml"
        # timestamp は ISO-8601 でパース可能
        datetime.fromisoformat(payload["timestamp"])

    def test_event_omitted_when_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, _ = _capture_cli_echo_json(
            tmp_path,
            "plain",
            monkeypatch=monkeypatch,
        )
        assert "event" not in payload
        assert payload["message"] == "plain"

    def test_stdout_when_err_false(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, stream = _capture_cli_echo_json(
            tmp_path,
            "stdout line",
            err=False,
            event="init.result_success",
            monkeypatch=monkeypatch,
        )
        assert stream == "stdout"
        assert payload["event"] == "init.result_success"

    def test_cli_secho_emits_json_without_color(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, _ = _capture_cli_echo_json(
            tmp_path,
            "ERROR: boom",
            err=True,
            event="team.unexpected_error",
            use_secho=True,
            fg="red",
            bold=True,
            monkeypatch=monkeypatch,
            error="boom",
            error_type="RuntimeError",
        )
        assert payload["type"] == "cli"
        assert payload["event"] == "team.unexpected_error"
        assert payload["error"] == "boom"
        assert payload["error_type"] == "RuntimeError"
        # json モードでは ANSI エスケープが入らない
        assert "\x1b[" not in payload["message"]

    def test_non_serializable_fields_fallback_to_str(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_path = Path("/tmp/example")
        payload, _ = _capture_cli_echo_json(
            tmp_path,
            "with path",
            event="x.y",
            monkeypatch=monkeypatch,
            workspace_path=custom_path,
        )
        # Path は default=str で文字列化される
        assert payload["workspace_path"] == str(custom_path)


# ---------------------------------------------------------------------------
# モード検出の fallback テスト
# ---------------------------------------------------------------------------


class TestLogFormatDetection:
    """setup_logging 未呼出時は環境変数 MIXSEEK_LOG_FORMAT を参照する。"""

    def test_env_var_json_triggers_json_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo("hi", err=True, event="pre.setup"),
        )
        assert out == ""
        payload = json.loads(err.rstrip("\n"))
        assert payload["event"] == "pre.setup"

    def test_no_env_var_defaults_to_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo("default", err=True, event="pre.setup"),
        )
        assert err == "default\n"
        assert out == ""

    def test_setup_logging_overrides_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """setup_logging で text に設定した場合、env var の json は無視される。"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        config = LoggingConfig(log_format="text", file_enabled=False, console_enabled=False)
        setup_logging(config, tmp_path)

        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo("explicit text", err=True, event="post.setup"),
        )
        assert err == "explicit text\n"
        assert out == ""
