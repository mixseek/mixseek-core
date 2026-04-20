"""統一ロガー "mixseek" の初期化。

4モード（logfire有無 x text/json）に対応する setup_logging() を提供。
root logger ではなく "mixseek" named logger を使用し、propagate=False で独立動作する。
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mixseek.config.logging import LogFormatType, LoggingConfig

# ログレベルマッピング
LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# 現在の log_format を保持するモジュール変数。setup_logging() で更新される。
# 未初期化時は環境変数 MIXSEEK_LOG_FORMAT を fallback として参照し、それも無ければ
# "text" を返す。これにより setup_logging() 呼び出し前の早期エラー出力でも
# --log-format json / MIXSEEK_LOG_FORMAT=json を反映できる。
_current_log_format: LogFormatType = "text"
_setup_logging_called: bool = False


def get_log_format() -> LogFormatType:
    """現在の log_format を返す。

    setup_logging() 呼び出し後は config の値を返す。呼び出し前は
    環境変数 ``MIXSEEK_LOG_FORMAT`` (``"json"`` / ``"text"``) を参照し、
    未設定時は ``"text"``。
    CLI の cli_echo/cli_secho ヘルパーが json/text の出力切り替えに使用する。
    """
    if _setup_logging_called:
        return _current_log_format
    env_value = os.getenv("MIXSEEK_LOG_FORMAT", "").lower()
    return "json" if env_value == "json" else "text"


# テキストフォーマット文字列
TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# LogRecord 標準属性セット（extra フィールド抽出時に除外する）
_STANDARD_FIELDS: frozenset[str] = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class TextFormatter(logging.Formatter):
    """extra fields を別行 key: value 形式で表示するフォーマッタ。

    extra fields がない場合はメッセージ行のみ出力。
    extra fields がある場合は各フィールドをインデント付きで別行出力。
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_FIELDS and not k.startswith("_")}
        if not extra:
            return base
        lines = [base]
        for k, v in extra.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)


class JsonFormatter(logging.Formatter):
    """stdlib のみで実装する JSON フォーマッタ。

    extra fields をトップレベルキーとして出力。type: "log" で標準ログを識別。
    """

    def format(self, record: logging.LogRecord) -> str:
        # メッセージをフォーマット（args展開）
        message = record.getMessage()

        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "type": "log",
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        # extra fields をトップレベルに追加
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_FIELDS and not k.startswith("_")}
        log_entry.update(extra)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SkipTracesFilter(logging.Filter):
    """LogfireLoggingHandler でのスパン由来レコード再送を防止するフィルタ。

    "mixseek.traces" ロガー（JsonSpanProcessor の出力先）からのレコードを
    LogfireLoggingHandler に流さないことで、フィードバックループを回避する。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("mixseek.traces")


def setup_logging(config: LoggingConfig, workspace: Path | None = None) -> logging.Logger:
    """統一ロガー "mixseek" を初期化。4モードに対応。

    全モードで初期段階は StreamHandler/FileHandler を追加する。
    Mode 3 (logfire+text) では setup_logfire() 内の finalize_mode3_handlers() で
    StreamHandler/FileHandler を除去し、ConsoleOptions/TeeWriter に移行する。

    Args:
        config: ロギング設定
        workspace: ワークスペースパス（ファイル出力先）

    Returns:
        設定済みの "mixseek" ロガー
    """
    global _current_log_format, _setup_logging_called
    _current_log_format = config.log_format
    _setup_logging_called = True

    logger = logging.getLogger("mixseek")

    # FDリーク防止: 既存ハンドラをクローズしてからクリア
    for h in logger.handlers:
        h.close()
    logger.handlers.clear()
    logger.propagate = False

    level = LOG_LEVEL_MAP.get(config.log_level, logging.INFO)
    logger.setLevel(level)

    # フォーマッタ選択
    formatter: logging.Formatter
    if config.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter(TEXT_FORMAT)

    # --- 全モード共通: StreamHandler/FileHandler を追加 ---
    # Mode 3 (logfire+text) では setup_logfire() 完了後に除去されるが、
    # setup_logfire() 完了前のログ欠損を防ぐため、初期段階では全モードで追加する。

    # コンソール出力
    if config.console_enabled:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # ファイル出力
    if config.file_enabled and workspace:
        log_dir = workspace / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "mixseek.log", mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Logfire handler（標準ログを Logfire cloud に転送）
    if config.logfire_enabled:
        try:
            import logfire

            logfire_handler = logfire.LogfireLoggingHandler()
            logfire_handler.setLevel(level)
            # Mode 4 (logfire + json): SkipTracesFilter でスパン由来レコードのループ防止
            if config.log_format == "json":
                logfire_handler.addFilter(SkipTracesFilter())
            logger.addHandler(logfire_handler)
        except ImportError:
            # 構造化ログ: 欠落パッケージ名を extra で明示し、JsonFormatter でフィールド化する
            logger.warning(
                "Logfire package not installed, skipping Logfire logging handler",
                extra={"missing_package": "logfire"},
            )
        except Exception as e:
            # 構造化ログ: 例外情報を extra で明示し、JsonFormatter でフィールド化する
            logger.warning(
                "Failed to add Logfire logging handler",
                extra={"error": str(e), "error_type": type(e).__name__},
            )

    # ハンドラなしの場合は NullHandler（サイレントモード）
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    return logger
