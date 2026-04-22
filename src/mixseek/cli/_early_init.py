"""CLI 起動時の最上段で実行する stderr 制御フック。

このモジュールは ``mixseek.cli.main`` の先頭 (他の import より前) で
``install_early_stderr_hooks()`` を呼び出されることを前提とする。

### 配置場所の制約
``mixseek.cli._early_init`` に配置しているのは、親パッケージの ``__init__.py``
(``mixseek/__init__.py`` と ``mixseek/cli/__init__.py``) がいずれも軽量で
``logfire`` を import しないため。もし ``mixseek.observability`` 配下に置くと、
``mixseek/observability/__init__.py`` が ``logfire`` を間接 import してしまい、
本フックで JSON 化したい ``LogfireNotConfiguredWarning`` 等が早期にトリガされる。

### 実装の制約
- stdlib のみ import する (``os`` / ``sys`` / ``warnings`` / ``json`` / ``datetime``)。
  他 ``mixseek.*`` / ``logfire`` を一切 import しない。
- 冪等: 複数回呼ばれても副作用は一度だけ (``_installed`` フラグ)。

### 提供する挙動
``MIXSEEK_LOG_FORMAT=json`` 時の ``warnings.showwarning`` 差し替え:
Python の警告出力を ``{"type":"warning",...}`` 1 行 JSON に切り替える。
``setup_logging()`` 前 (import 段階) に発火する warning もスキーマ化できる。
text モード (未設定 or ``"text"``) では stdlib 既定動作を維持する。

### 方針上の注意
warning を抑止 (例: ``LOGFIRE_IGNORE_NO_CONFIG=1`` の自動セット) はしない。
warning は開発者に届ける価値のある情報なので、構造化できない場合でも
stdlib 既定のまま stderr に表示させ、利用者が気づけるようにする。
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import UTC, datetime
from typing import Any, TextIO

_installed: bool = False
_original_showwarning: Any = None


def _json_showwarning(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    """warnings.showwarning の JSON 版差し替え実装。

    ``warnings.warn()`` の通常呼び出しでは ``file`` / ``line`` は省略され、
    出力先は stderr が既定。``file`` が明示指定された場合はそちらに書く
    (stdlib の ``_showwarning`` と同じポリシー)。

    JSON シリアライズ / 書き込み失敗時は fallback として元の ``showwarning`` に委譲する。
    """
    target: TextIO = file if file is not None else sys.stderr
    entry: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "type": "warning",
        "level": "WARNING",
        "category": category.__name__ if category else None,
        "filename": filename,
        "lineno": lineno,
        "message": str(message),
    }
    try:
        target.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        # 書き込み失敗時は stdlib 既定動作にフォールバック (観測性維持)
        if _original_showwarning is not None:
            _original_showwarning(message, category, filename, lineno, file, line)


def install_early_stderr_hooks() -> None:
    """早期 stderr 制御フックをインストールする (冪等)。

    ``mixseek.cli.main`` モジュールのトップ (他の import より前) で呼び出すこと。
    import 段階で発火する warning (``LogfireNotConfiguredWarning`` /
    ``DeprecationWarning`` 等) も JSON 化するため、``warnings.showwarning`` の
    差し替えは他 import より前に行う必要がある。
    """
    global _installed, _original_showwarning
    if _installed:
        return

    if os.getenv("MIXSEEK_LOG_FORMAT", "").lower() == "json":
        _original_showwarning = warnings.showwarning
        warnings.showwarning = _json_showwarning

    _installed = True
