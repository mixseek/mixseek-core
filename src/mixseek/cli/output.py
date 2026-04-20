"""CLI 出力ヘルパー。

text / json の両モードに対応した CLI 向けメッセージ出力関数を提供する。

- text モード: ``typer.echo`` / ``typer.secho`` に完全委譲し、現行動作を保つ。
- json モード: 構造化 JSON を 1 行で stderr / stdout に出力する。

モード判定は ``mixseek.observability.get_log_format()`` に委ねる。
``setup_logging()`` 呼び出し前は環境変数 ``MIXSEEK_LOG_FORMAT`` を参照し、
未設定時は ``"text"`` 扱い。
"""

import json
import sys
from datetime import UTC, datetime
from typing import Any

import typer

from mixseek.observability import get_log_format


def cli_echo(
    message: str,
    *,
    err: bool = False,
    event: str | None = None,
    **fields: Any,
) -> None:
    """CLI メッセージを出力する。

    text モードでは ``typer.echo(message, err=err)`` と完全に同じ出力を行う。
    json モードでは ``{"type":"cli","event":...,"message":...,...fields}`` を
    1 行 JSON として stderr (err=True) または stdout に出力する。

    Args:
        message: 出力するメッセージ本文。
        err: True の場合 stderr、False の場合 stdout に出力する。
        event: JSON モードで出力される event 名 (例: ``"evaluate.config_loaded"``)。
            None の場合 JSON には含まれない。
        **fields: JSON モードで出力に含める追加キー。
    """
    if get_log_format() == "json":
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
    **fields: Any,
) -> None:
    """色付き CLI メッセージを出力する。

    text モードでは ``typer.secho`` と完全に同じ出力を行う。json モードでは
    色情報を捨て、``cli_echo`` と同じ構造の JSON を出力する。

    Args:
        message: 出力するメッセージ本文。
        err: True の場合 stderr、False の場合 stdout に出力する。
        fg: 文字色 (``typer.colors.RED`` 等)。json モードでは無視される。
        bold: 太字フラグ。``None`` (既定) は ``typer.secho`` 同様にスタイルを付与しない。
            ``False`` を明示すると ANSI の太字無効化コード (``\\x1b[22m``) が入るため、
            呼び出し側が明示的に指定しない限り ``None`` のままにすること。
        event: JSON モードで出力される event 名。
        **fields: JSON モードで出力に含める追加キー。
    """
    if get_log_format() == "json":
        _emit_json(message, err=err, event=event, fields=fields)
    else:
        typer.secho(message, err=err, fg=fg, bold=bold)


def _emit_json(
    message: str,
    *,
    err: bool,
    event: str | None,
    fields: dict[str, Any],
) -> None:
    """JSON モード用の出力処理。

    ``fields`` の中に ``timestamp`` / ``type`` / ``event`` / ``message``
    と衝突するキーがあっても、スキーマ不変キーは上書きされない
    (衝突した ``fields`` 側のエントリは破棄される)。
    """
    payload: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "type": "cli",
    }
    if event is not None:
        payload["event"] = event
    payload["message"] = message
    # スキーマ不変キー (timestamp/type/event/message) の上書きを防ぐため、
    # 既存キーは保持し fields 側の衝突エントリを捨てる。
    payload.update({k: v for k, v in fields.items() if k not in payload})
    stream = sys.stderr if err else sys.stdout
    stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
