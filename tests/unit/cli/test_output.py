"""cli_echo / cli_secho ヘルパーのテスト。

text モードでは typer.echo / typer.secho と完全に同一の出力であること、
json モードでは以下 2 経路の分岐が期待通りに動作することを検証する:

- logger 経路 (setup_logging 呼出後): mixseek logger 経由で ``type:"log"``
  構造化ログが出力され、level フィールドが付く。
- fallback 経路 (setup_logging 未呼出): 早期エラー用に ``type:"cli"``
  1 行 JSON が stderr / stdout に直接出力される。
"""

from __future__ import annotations

import io
import json
import logging
import sys
from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
import typer

from mixseek.cli.output import cli_echo, cli_secho
from mixseek.config.logging import LoggingConfig
from mixseek.observability.logging_setup import setup_logging

LOGGER_NAME = "mixseek"


@pytest.fixture(autouse=True)
def reset_logging_state(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """テスト前後で logging の state (logger handlers と module 変数) をリセット。

    他のテスト (例: ``test_exec_dry_run``) が CLI コマンドを実行して
    ``setup_logging()`` を呼び、``_setup_logging_called=True`` のまま放置するため、
    **test 前** にも module 変数をクリアしないと本 test 群が logger 経路に流れてしまう。
    """
    from mixseek.observability import logging_setup

    # 環境変数の汚染防止
    monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)

    # 既存 test 群からの持ち越し state をクリア (前段)
    logger = logging.getLogger(LOGGER_NAME)
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)
    logging_setup._current_log_format = "text"
    logging_setup._setup_logging_called = False

    yield

    # 本 test の state も次 test に持ち越さないようクリア (後段)
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.setLevel(logging.WARNING)
    logging_setup._current_log_format = "text"
    logging_setup._setup_logging_called = False


def _capture_std(
    monkeypatch: pytest.MonkeyPatch,
    action: Callable[[], None],
) -> tuple[str, str]:
    """sys.stdout / sys.stderr を StringIO に差し替えて action を実行し、(stdout, stderr) を返す。

    ``monkeypatch.undo()`` は fixture 側が同一 monkeypatch に設定した delenv などを
    巻き戻してしまうため使わず、直接 ``sys.stdout`` / ``sys.stderr`` を差し替える。
    (引数の ``monkeypatch`` は現状参照されないが API 互換のため残す。)
    """
    del monkeypatch  # currently unused (see docstring)
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    orig_stdout, orig_stderr = sys.stdout, sys.stderr
    sys.stdout = out_buf
    sys.stderr = err_buf
    try:
        action()
    finally:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
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
        del monkeypatch  # unused — sys.stdout/stderr を直接差し替える (fixture 側の delenv を守る)

        class _FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        def _invoke(fn: Any) -> str:
            out = _FakeTTY()
            err = _FakeTTY()
            orig_stdout, orig_stderr = sys.stdout, sys.stderr
            sys.stdout = out
            sys.stderr = err
            try:
                extra: dict[str, Any] = {"err": kwargs.get("err", False), "fg": kwargs.get("fg")}
                if "bold" in kwargs:
                    extra["bold"] = kwargs["bold"]
                fn("styled", **extra)
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
            return err.getvalue() if kwargs.get("err", False) else out.getvalue()

        expected = _invoke(typer.secho)
        actual = _invoke(cli_secho)
        assert actual == expected
        # 仕様確認: bold 未指定時は `\x1b[22m` が入らない。
        if "bold" not in kwargs and kwargs.get("fg"):
            assert "\x1b[22m" not in actual

    def test_extra_fields_ignored_in_text_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """text モードでは event / level / extra fields は無視され、typer.echo 同等の出力になる。"""
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo(
                "loaded",
                err=True,
                event="evaluate.config_loaded",
                level="error",  # text モードでは無視される
                path="/x.toml",
                nested={"k": 1},
            ),
        )
        assert out == ""
        assert err == "loaded\n"


# ---------------------------------------------------------------------------
# json モード + logger 経路 (setup_logging 呼出後) のテスト
# ---------------------------------------------------------------------------


def _setup_json_logger_with_stderr_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """json モード + console 出力有効で setup_logging を呼び、stderr バッファを返す。

    ``setup_logging`` 内で ``logging.StreamHandler(sys.stderr)`` が作られるため、
    **先に** ``sys.stderr`` を StringIO に差し替えてから setup_logging を呼ぶ。
    """
    err_buf = io.StringIO()
    monkeypatch.setattr("sys.stderr", err_buf)
    config = LoggingConfig(
        log_format="json",
        file_enabled=False,
        console_enabled=True,
        log_level="debug",  # test 内で debug level の動作確認もできるように
    )
    setup_logging(config, tmp_path)
    return err_buf


def _capture_logger_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action: Callable[[], None],
) -> dict[str, Any]:
    """logger 経路で json 出力をキャプチャし、1 行目の JSON を dict で返す。"""
    err_buf = _setup_json_logger_with_stderr_capture(tmp_path, monkeypatch)
    action()
    raw = err_buf.getvalue()
    assert raw.endswith("\n"), "JSON 出力は改行で終わるべき"
    # 1 行目を読む (setup_logging 自体は出力しない想定)
    first_line = raw.split("\n", 1)[0]
    return cast(dict[str, Any], json.loads(first_line))


class TestJsonModeLoggerPath:
    """json モード + setup_logging 後は "mixseek" logger 経由で構造化ログを出す。"""

    def test_basic_payload_has_type_log(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo(
                "Loading custom config: /x.toml",
                err=True,
                event="evaluate.config_loaded",
                path="/x.toml",
            ),
        )
        assert payload["type"] == "log"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "mixseek"
        assert payload["event"] == "evaluate.config_loaded"
        assert payload["message"] == "Loading custom config: /x.toml"
        assert payload["path"] == "/x.toml"
        datetime.fromisoformat(payload["timestamp"])

    def test_event_omitted_when_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo("plain", err=True),
        )
        assert "event" not in payload
        assert payload["message"] == "plain"

    @pytest.mark.parametrize(
        "level,expected_levelname",
        [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ],
    )
    def test_level_parameter_maps_to_logger_method(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, level: str, expected_levelname: str
    ) -> None:
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo("msg", err=True, event="x.y", level=level),
        )
        assert payload["level"] == expected_levelname

    def test_invalid_level_falls_back_to_info(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """未知の level 名 (例: "INVALID") は "info" に正規化される。"""
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo("msg", err=True, event="x.y", level="INVALID"),
        )
        assert payload["level"] == "INFO"

    def test_cli_secho_also_routes_through_logger(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """cli_secho も json モード + 初期化後は logger 経由で出力される。fg は無視される。"""
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_secho(
                "ERROR: boom",
                err=True,
                fg="red",
                bold=True,
                event="team.unexpected_error",
                level="error",
                error="boom",
                error_type="RuntimeError",
            ),
        )
        assert payload["type"] == "log"
        assert payload["level"] == "ERROR"
        assert payload["event"] == "team.unexpected_error"
        assert payload["error"] == "boom"
        assert payload["error_type"] == "RuntimeError"
        # json モードでは ANSI エスケープが入らない
        assert "\x1b[" not in payload["message"]

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("\n⚠️  Interrupted by user", "⚠️  Interrupted by user"),
            ("\nSaving to database...", "Saving to database..."),
            ("hello", "hello"),
            ("   spaced   ", "spaced"),
            ("Available keys:\nfoo, bar, baz", "Available keys:\nfoo, bar, baz"),
            ("\x1b[31mred msg\x1b[0m", "red msg"),
        ],
    )
    def test_json_message_is_cleaned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str, expected: str
    ) -> None:
        """logger 経路でも message は click.unstyle() + strip() で整形される。"""
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo(raw, err=True, event="x.y"),
        )
        assert payload["message"] == expected

    def test_non_serializable_fields_fallback_to_str(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_path = Path("/tmp/example")
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo("with path", event="x.y", workspace_path=custom_path),
        )
        # JsonFormatter 側で default=str により文字列化される
        assert payload["workspace_path"] == str(custom_path)

    def test_reserved_extra_keys_are_dropped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """LogRecord 標準属性 (例: name / msg / levelname) と同名の fields キーは

        logging.makeRecord の KeyError を回避するため extra から除外される。
        """
        payload = _capture_logger_json(
            tmp_path,
            monkeypatch,
            lambda: cli_echo(
                "legit message",
                err=True,
                event="x.y",
                # 以下は LogRecord 標準属性と衝突する予約キー
                name="SHOULD_BE_DROPPED",
                msg="SHOULD_BE_DROPPED",
                levelname="SHOULD_BE_DROPPED",
            ),
        )
        # 正規の値が維持される
        assert payload["message"] == "legit message"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "mixseek"


# ---------------------------------------------------------------------------
# json モード + fallback 経路 (setup_logging 未呼出時の早期エラー) のテスト
# ---------------------------------------------------------------------------


def _capture_fallback_json(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
    *,
    err: bool = False,
    event: str | None = None,
    use_secho: bool = False,
    fg: str | None = None,
    bold: bool = False,
    **fields: Any,
) -> tuple[dict[str, Any], str]:
    """setup_logging を呼ばずに env var で json モードを有効化し、fallback 経路の出力を取得する。

    Returns:
        (payload_dict, stream_name) — stream_name は "stdout" or "stderr"
    """
    monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")

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


class TestJsonModeFallback:
    """setup_logging 未呼出時の早期エラー用 fallback は type:"cli" JSON を出す。"""

    def test_fallback_payload_has_type_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, stream = _capture_fallback_json(
            monkeypatch,
            "Loading custom config: /x.toml",
            err=True,
            event="evaluate.config_loaded",
            path="/x.toml",
        )
        assert stream == "stderr"
        assert payload["type"] == "cli"
        assert payload["event"] == "evaluate.config_loaded"
        assert payload["message"] == "Loading custom config: /x.toml"
        assert payload["path"] == "/x.toml"
        datetime.fromisoformat(payload["timestamp"])

    def test_event_omitted_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, _ = _capture_fallback_json(monkeypatch, "plain")
        assert "event" not in payload
        assert payload["message"] == "plain"

    def test_stdout_when_err_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, stream = _capture_fallback_json(
            monkeypatch,
            "stdout line",
            err=False,
            event="init.result_success",
        )
        assert stream == "stdout"
        assert payload["event"] == "init.result_success"

    def test_cli_secho_emits_json_without_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, _ = _capture_fallback_json(
            monkeypatch,
            "ERROR: boom",
            err=True,
            event="team.unexpected_error",
            use_secho=True,
            fg="red",
            bold=True,
            error="boom",
            error_type="RuntimeError",
        )
        assert payload["type"] == "cli"
        assert payload["event"] == "team.unexpected_error"
        assert payload["error"] == "boom"
        assert payload["error_type"] == "RuntimeError"
        # json モードでは ANSI エスケープが入らない
        assert "\x1b[" not in payload["message"]

    def test_level_parameter_is_ignored_in_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """fallback では type:"cli" のため level フィールドは付与されない (logger 経路専用)。"""
        payload, _ = _capture_fallback_json(
            monkeypatch,
            "early error",
            err=True,
            event="early.err",
            level="error",
        )
        assert "level" not in payload
        assert payload["type"] == "cli"

    def test_non_serializable_fields_fallback_to_str(self, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_path = Path("/tmp/example")
        payload, _ = _capture_fallback_json(
            monkeypatch,
            "with path",
            event="x.y",
            workspace_path=custom_path,
        )
        assert payload["workspace_path"] == str(custom_path)

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("\n⚠️  Interrupted by user", "⚠️  Interrupted by user"),
            ("   spaced   ", "spaced"),
            ("\x1b[31mred msg\x1b[0m", "red msg"),
        ],
    )
    def test_json_message_is_cleaned(self, monkeypatch: pytest.MonkeyPatch, raw: str, expected: str) -> None:
        payload, _ = _capture_fallback_json(
            monkeypatch,
            raw,
            err=True,
            event="x.y",
        )
        assert payload["message"] == expected

    def test_empty_message_stays_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload, _ = _capture_fallback_json(
            monkeypatch,
            "",
            err=True,
            event="team.dev_warning_blank",
        )
        assert payload["message"] == ""

    @pytest.mark.parametrize("reserved_key", ["timestamp", "type"])
    def test_reserved_keys_are_not_overwritten_by_fields(
        self, monkeypatch: pytest.MonkeyPatch, reserved_key: str
    ) -> None:
        """fields に schema 不変キーと同名 entry があっても正規キーは上書きされない。"""
        # mypy: ``**{reserved_key: ...}`` は dict[str, str] として推論されるため、
        # ``use_secho``/``bold`` 等の既存 kwarg と衝突する可能性があるとして警告される。
        # reserved_key は "timestamp"/"type" に限定されており衝突しない。
        payload, _ = _capture_fallback_json(
            monkeypatch,
            "正規 message",
            err=True,
            event="legit.event",
            **{reserved_key: "USER_SUPPLIED_VALUE"},  # type: ignore[arg-type]
        )
        assert payload[reserved_key] != "USER_SUPPLIED_VALUE"
        assert payload["type"] == "cli"
        assert payload["event"] == "legit.event"
        assert payload["message"] == "正規 message"
        datetime.fromisoformat(payload["timestamp"])


# ---------------------------------------------------------------------------
# モード検出の fallback テスト
# ---------------------------------------------------------------------------


class TestLogFormatDetection:
    """setup_logging 未呼出時は環境変数 MIXSEEK_LOG_FORMAT を参照する。"""

    def test_env_var_json_triggers_fallback_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """setup_logging 前 + env var json は fallback 経路 (type:"cli") になる。"""
        monkeypatch.setenv("MIXSEEK_LOG_FORMAT", "json")
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo("hi", err=True, event="pre.setup"),
        )
        assert out == ""
        payload = json.loads(err.rstrip("\n"))
        assert payload["type"] == "cli"
        assert payload["event"] == "pre.setup"

    def test_no_env_var_defaults_to_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MIXSEEK_LOG_FORMAT", raising=False)
        out, err = _capture_std(
            monkeypatch,
            lambda: cli_echo("default", err=True, event="pre.setup"),
        )
        assert err == "default\n"
        assert out == ""

    def test_setup_logging_text_overrides_env_var_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
