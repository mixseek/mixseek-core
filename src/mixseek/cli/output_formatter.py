"""CLI 出力フォーマッタ。

`mixseek.cli` / `mixseek.cli.data` の 2 本立て logger に適用するフォーマッタを提供する。

- `CLITextFormatter`: text モード用。メッセージ本文のみを出力し、level に応じて
    ANSI カラーを自動付与する。非 TTY / ``NO_COLOR`` 指定時は ANSI を除去する。
- `CLIJsonFormatter`: json モード用。1 行 JSON として ``{"timestamp", "type",
    "level", "logger", "message", ...}`` を出力する。message は ``click.unstyle()``
    で ANSI を除去してから格納する。
- `BareFormatter`: データ出力用。``%(message)s`` のみをそのまま出力する
    (``--output-format json`` / ``--version`` のパイプ契約維持)。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

import click

from mixseek.observability.logging_setup import _STANDARD_FIELDS

# スキーマ不変キー (CLIJsonFormatter 出力の骨格)。extra からの上書きを防ぐ。
_JSON_SCHEMA_KEYS: frozenset[str] = frozenset({"timestamp", "type", "level", "logger", "message"})

# level 自動着色テーブル。INFO は既定で色を付けない (現行 typer.echo 同等)。
# CRITICAL は bold 付きで他と差別化する。
_LEVEL_STYLES: dict[int, dict[str, Any]] = {
    logging.DEBUG: {"fg": "bright_black"},
    logging.WARNING: {"fg": "yellow"},
    logging.ERROR: {"fg": "red"},
    logging.CRITICAL: {"fg": "red", "bold": True},
}


def _should_color(stream: TextIO | None) -> bool:
    """与えられた stream に ANSI カラーを流すべきかを判定する。

    ``NO_COLOR`` 環境変数が設定されていれば常に False。
    それ以外は ``stream.isatty()`` (stream が None の場合は sys.stderr) の結果に従う。
    """
    if os.environ.get("NO_COLOR"):
        return False
    target = stream if stream is not None else sys.stderr
    return bool(getattr(target, "isatty", lambda: False)())


class CLITextFormatter(logging.Formatter):
    """text モード用フォーマッタ。

    - メッセージ本文のみを出力 (timestamp/level プレフィックスなし)
    - level に応じて ANSI カラーを自動付与
    - 非 TTY / ``NO_COLOR`` 指定時は ``click.unstyle()`` で ANSI を除去
    - 呼び出し側が ``click.style(...)`` で付加した構造色 (セクション見出し等) は
        TTY 時はそのまま通す (level 着色は自動付与の既定値で、既存 ANSI は保持)

    Attributes:
        _stream: カラー判定に使うストリーム。None の場合は stderr を使う。
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        super().__init__()
        self._stream = stream

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if not _should_color(self._stream):
            return click.unstyle(message)
        style = _LEVEL_STYLES.get(record.levelno)
        if style is None:
            return message
        return click.style(message, **style)


class CLIJsonFormatter(logging.Formatter):
    """json モード用フォーマッタ。

    ``{"timestamp":..., "type":"log", "level":..., "logger":..., "message":...}``
    形式の 1 行 JSON を出力する。``click.style`` 由来の ANSI は message から除去。
    extra fields はトップレベルに追加されるが、スキーマ不変キー
    (``timestamp``/``type``/``level``/``logger``/``message``) と衝突するキーは
    破棄して運用側のクエリが安定するようにする。
    """

    def format(self, record: logging.LogRecord) -> str:
        message = click.unstyle(record.getMessage())
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "type": "log",
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_FIELDS and not k.startswith("_") and k not in _JSON_SCHEMA_KEYS
        }
        log_entry.update(extra)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class BareFormatter(logging.Formatter):
    """データ出力専用フォーマッタ。

    ``%(message)s`` のみを返す。``--output-format json`` / ``--output-format csv`` /
    ``--version`` などのパイプ契約を維持するため、装飾 / JSON 封筒を一切付与しない。
    """

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()
