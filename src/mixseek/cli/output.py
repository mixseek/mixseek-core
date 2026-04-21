"""CLI 出力ヘルパー。

text / json の両モードに対応した CLI 向けメッセージ出力関数を提供する。

- text モード: ``typer.echo`` / ``typer.secho`` に完全委譲し、現行動作を保つ。
- json モード:
  - ``setup_logging()`` 呼び出し後は ``"mixseek"`` logger 経由で構造化ログを出力する。
    これによりファイル出力 (``workspace/logs/mixseek.log``)、Logfire 転送、
    ``--log-level`` フィルタ、``level`` フィールド付き JSON (``{"type":"log",...}``)
    が自動的に効く。
  - ``setup_logging()`` 呼び出し前 (``validate_logfire_flags`` 等の早期エラー) は
    fallback として 1 行 JSON (``{"type":"cli",...}``) を stderr / stdout に出力する。

モード判定は ``mixseek.observability.get_log_format()`` に委ねる。
``setup_logging()`` 呼び出し前は環境変数 ``MIXSEEK_LOG_FORMAT`` を参照し、
未設定時は ``"text"`` 扱い。
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import click
import typer

from mixseek.observability import get_log_format, is_logger_initialized

_LOGGER_NAME = "mixseek"

# 許容する log level 名 (標準 logging の小文字メソッド名)
_VALID_LEVELS: frozenset[str] = frozenset({"debug", "info", "warning", "error", "critical"})

# ``_emit_via_logger`` で ``extra`` から除外する予約キー (LogRecord 標準属性)。
# logging モジュールは extra に標準属性と同名のキーを渡すと KeyError を投げる。
_RESERVED_EXTRA_KEYS: frozenset[str] = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


def cli_echo(
    message: str,
    *,
    err: bool = False,
    event: str | None = None,
    level: str = "info",
    **fields: Any,
) -> None:
    """CLI メッセージを出力する。

    text モードでは ``typer.echo(message, err=err)`` と完全に同じ出力を行う。
    json モードでは ``setup_logging()`` 初期化後かで経路が分かれる:

    - 初期化後: ``"mixseek"`` logger の ``level`` メソッド経由で構造化ログ出力。
      (``{"type":"log","level":<LEVEL>,"logger":"mixseek",...}``)
    - 初期化前 (早期エラー): ``{"type":"cli","event":...,"message":...}`` を
      1 行 JSON として stderr (err=True) または stdout に出力する fallback。

    Args:
        message: 出力するメッセージ本文。
        err: True の場合 stderr、False の場合 stdout に出力する。
            (logger 経由の場合は ``StreamHandler`` 設定に従うため無視される。)
        event: イベント名 (例: ``"evaluate.config_loaded"``)。JSON の ``event`` キーに入る。
            None の場合は出力に含まれない。
        level: logger 経路で使用する log level。
            ``"debug"`` / ``"info"`` / ``"warning"`` / ``"error"`` / ``"critical"``。
            text モードおよび早期エラー fallback では無視される。
        **fields: JSON モードで出力に含める追加キー。
    """
    if get_log_format() == "json":
        if is_logger_initialized():
            _emit_via_logger(message, level=level, event=event, fields=fields)
        else:
            _emit_json(message, err=err, event=event, fields=fields)
    else:
        typer.echo(message, err=err)


def cli_secho(
    message: str,
    *,
    err: bool = False,
    fg: str | None = None,
    bold: bool | None = None,
    event: str | None = None,
    level: str = "info",
    **fields: Any,
) -> None:
    """色付き CLI メッセージを出力する。

    text モードでは ``typer.secho`` と完全に同じ出力を行う。json モードでは
    色情報を捨て、``cli_echo`` と同じ経路 (logger / 早期エラー fallback) で出力する。

    ``fg`` は text モード表示用、``level`` は json モード (logger 経路) 用で
    責務が独立している。``fg=typer.colors.RED`` の呼び出しは通常 ``level="error"``、
    ``fg=typer.colors.YELLOW`` は ``level="warning"`` を明示的に併記する。

    Args:
        message: 出力するメッセージ本文。
        err: True の場合 stderr、False の場合 stdout に出力する。
            (logger 経由の場合は ``StreamHandler`` 設定に従うため無視される。)
        fg: 文字色 (``typer.colors.RED`` 等)。json モードでは無視される。
        bold: 太字フラグ。``None`` (既定) は ``typer.secho`` 同様にスタイルを付与しない。
            ``False`` を明示すると ANSI の太字無効化コード (``\\x1b[22m``) が入るため、
            呼び出し側が明示的に指定しない限り ``None`` のままにすること。
        event: イベント名。JSON の ``event`` キーに入る。
        level: logger 経路で使用する log level。詳細は ``cli_echo`` を参照。
        **fields: JSON モードで出力に含める追加キー。
    """
    if get_log_format() == "json":
        if is_logger_initialized():
            _emit_via_logger(message, level=level, event=event, fields=fields)
        else:
            _emit_json(message, err=err, event=event, fields=fields)
    else:
        typer.secho(message, err=err, fg=fg, bold=bold)


def _emit_via_logger(
    message: str,
    *,
    level: str,
    event: str | None,
    fields: dict[str, Any],
) -> None:
    """``"mixseek"`` logger の ``level`` メソッド経由で構造化ログを出力する。

    ``JsonFormatter`` により ``{"type":"log","level":...,"logger":...,"message":...,
    <fields>}`` 形式の 1 行 JSON になり、同時に FileHandler / LogfireLoggingHandler
    にも自動的に流れる。

    message は ``click.unstyle()`` で ANSI エスケープ除去、``strip()`` で
    前後の空白・改行を除去してから渡す。text モード向け装飾が JSON ログの
    メッセージ本文に残らないようにするため。

    ``fields`` の中に logger 側で生成される標準属性 (``message`` / ``level`` 等)
    と衝突するキーがあっても、``logging`` 標準の挙動を壊さないよう ``_STANDARD_FIELDS``
    と衝突するものは ``extra`` から除外する。
    """
    normalized_level = level if level in _VALID_LEVELS else "info"
    clean_message = click.unstyle(message).strip()

    extra: dict[str, Any] = {}
    if event is not None:
        extra["event"] = event
    # logging の LogRecord 標準属性と衝突する extra キーは ValueError になるので除外。
    for k, v in fields.items():
        if k not in _RESERVED_EXTRA_KEYS:
            extra[k] = v

    logger = logging.getLogger(_LOGGER_NAME)
    log_method = getattr(logger, normalized_level)
    log_method(clean_message, extra=extra)


def _emit_json(
    message: str,
    *,
    err: bool,
    event: str | None,
    fields: dict[str, Any],
) -> None:
    """JSON モード (setup_logging 前の早期エラー) 専用 fallback 出力。

    ``fields`` の中に ``timestamp`` / ``type`` / ``event`` / ``message``
    と衝突するキーがあっても、スキーマ不変キーは上書きされない
    (衝突した ``fields`` 側のエントリは破棄される)。

    出力は ``typer.echo`` (内部的に ``click.echo``) 経由で書き込む。
    text モードと同じ出力経路に揃えることで、click の encoding 正規化
    (Unicode → stream エンコーディングのマッチング) の恩恵を受けられる。

    message は ``click.unstyle()`` で ANSI エスケープ除去、``strip()`` で
    前後の空白・改行を除去してから JSON へ格納する。text モード向けに付加された
    装飾 (例: 先頭の ``\\n``) が JSON ログ解析時のノイズにならないようにするため。
    """
    clean_message = click.unstyle(message).strip()

    payload: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "type": "cli",
    }
    if event is not None:
        payload["event"] = event
    payload["message"] = clean_message
    # スキーマ不変キー (timestamp/type/event/message) の上書きを防ぐため、
    # 既存キーは保持し fields 側の衝突エントリを捨てる。
    payload.update({k: v for k, v in fields.items() if k not in payload})
    typer.echo(json.dumps(payload, ensure_ascii=False, default=str), err=err)
