"""統一ロガー "mixseek" と CLI 補助ロガー "mixseek.cli" の初期化。

本モジュールは 2 種類のロガーをセットアップする:

- ``mixseek``: アプリケーション本体のログ。4 モード (logfire 有無 x text/json) に対応し、
    stderr / ``workspace/logs/mixseek.log`` / Logfire cloud への出力を扱う。
    ``setup_logging(config, workspace)`` で初期化される。
- ``mixseek.cli``: CLI UI / 操作イベント / エラー通知専用。常に stderr へ 1 行 JSON
    (json モード) またはメッセージ本文のみ (text モード) で出力する。
    ``propagate=False`` で ``mixseek`` 親ロガーとは独立動作し、Logfire / FileHandler
    には流入させない。``setup_cli_logger(log_format)`` または
    ``early_setup_cli_logger_from_env()`` で初期化され、未初期化時は
    ``NullHandler`` で root / ``lastResort`` への leak を防ぐ。

CLI 側は ``get_cli_logger()`` でインスタンスを取得し、
``logger.info(msg, extra={"event": ..., ...})`` のように標準 logging API で呼ぶ。
``extra`` は JSON フォーマッタでトップレベルキーに展開され、運用クエリ
(``logger:"mixseek.cli" @event:...``) の対象となる。
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

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
    未設定時は ``"text"``。``team`` コマンドが空行の視認性区切りを JSON モードで
    抑止する判定などに使用する。
    """
    if _setup_logging_called:
        return _current_log_format
    env_value = os.getenv("MIXSEEK_LOG_FORMAT", "").lower()
    return "json" if env_value == "json" else "text"


def is_logger_initialized() -> bool:
    """setup_logging() が呼ばれ、"mixseek" logger が使用可能かを返す。

    現状は後方互換のために残しているが、CLI 出力は ``mixseek.cli`` 専用 logger
    (本モジュールの ``setup_cli_logger()`` / ``early_setup_cli_logger_from_env()``
    で早期初期化される) 経由で出力されるため、通常は参照されない。
    """
    return _setup_logging_called


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
    スキーマ不変キー (``timestamp`` / ``type`` / ``level`` / ``logger`` / ``message``)
    は extra で上書きさせず、衝突する extra キーは破棄する (``_emit_json`` と同じポリシー)。
    これにより ``logger.info(msg, extra={"type": "foo"})`` のような呼び出しでも
    ``type: "log"`` 等のスキーマが常に安定する。
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
        # extra fields をトップレベルに追加。スキーマ不変キーの上書きは防ぐ。
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_FIELDS and not k.startswith("_")}
        log_entry.update({k: v for k, v in extra.items() if k not in log_entry})
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

    # 全ハンドラ設定完了後に初期化フラグを立てる。
    # 途中で例外 (FileHandler 作成失敗など) が発生した場合に
    # is_logger_initialized() が誤って True にならないようにするため、最後に立てる。
    _current_log_format = config.log_format
    _setup_logging_called = True

    return logger


# ---------------------------------------------------------------------------
# mixseek.cli 補助ロガー
#
# CLI UI / 操作イベント / エラー通知を stderr に構造化出力するための専用 logger。
# 以下の設計原則を守る:
#   - logger 名は "mixseek.cli" を維持 (運用基盤の logger: フィルタを保護)
#   - propagate=False で親 "mixseek" logger とは独立動作
#     (Logfire / FileHandler には流入させない)
#   - initialize_observability() 前の早期エラーも JSON 構造化できるよう
#     env var から bootstrap する経路を持つ
# ---------------------------------------------------------------------------

_CLI_LOGGER_NAME = "mixseek.cli"


class CLITextFormatter(logging.Formatter):
    """CLI text モード用フォーマッタ。

    メッセージ本文のみを出力 (timestamp / logger 名 / level プレフィックスなし)。
    呼び出し側や caller が ``click.style(...)`` で付加した ANSI は
    ``click.unstyle()`` で除去し、装飾なしのプレーンテキストに揃える。
    """

    def format(self, record: logging.LogRecord) -> str:
        return click.unstyle(record.getMessage())


class CLIJsonFormatter(logging.Formatter):
    """CLI json モード用フォーマッタ。

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
            if k not in _STANDARD_FIELDS and not k.startswith("_") and k not in log_entry
        }
        log_entry.update(extra)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def _clear_cli_handlers(logger: logging.Logger) -> None:
    """FD リーク防止のため既存 handler を close してからクリアする。"""
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


def setup_cli_logger(log_format: LogFormatType) -> logging.Logger:
    """``mixseek.cli`` logger を初期化する。

    UI / 操作イベント / エラー通知を stderr に出力する logger をセットアップする。
    ``propagate=False`` で親 ``mixseek`` logger への伝播を防ぎ、Logfire / FileHandler
    とは独立動作する。

    - text モード: ``CLITextFormatter`` (メッセージ本文のみ、ANSI 除去)
    - json モード: ``CLIJsonFormatter`` (1 行 JSON、ANSI 除去)

    Args:
        log_format: ``"text"`` または ``"json"``。

    Returns:
        初期化済みの ``mixseek.cli`` logger。
    """
    logger = logging.getLogger(_CLI_LOGGER_NAME)
    _clear_cli_handlers(logger)
    logger.propagate = False
    # level は DEBUG まで通す。verbose 判定は呼び出し側 (`if verbose:`) が行う。
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    if log_format == "json":
        handler.setFormatter(CLIJsonFormatter())
    else:
        handler.setFormatter(CLITextFormatter())
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


def _ensure_cli_safe_default(logger: logging.Logger) -> None:
    """handler 未設定の CLI logger を「propagate=False + NullHandler」の安全な既定値に揃える。

    ``logging.getLogger`` の既定 (``propagate=True`` + handler 無し) のままだと、
    ``setup_cli_logger()`` 前のアクセス直後に root logger / ``lastResort`` handler
    (stderr, WARNING 以上) へ leak してしまう。
    すでに handler が付いている (= setup 済み) 場合は何もしない。
    """
    if not logger.handlers:
        logger.propagate = False
        logger.addHandler(logging.NullHandler())


def get_cli_logger() -> logging.Logger:
    """``mixseek.cli`` logger を取得する。

    ``setup_cli_logger()`` による初期化前であっても安全な既定値として
    ``propagate=False`` + ``NullHandler`` を付与する。これにより未初期化時の
    メッセージは root / ``lastResort`` に leak せず破棄される。
    通常は ``early_setup_cli_logger_from_env()`` が ``ensure_log_format_env()``
    経由で先に呼ばれているので、初期化済みの logger が返る。
    """
    logger = logging.getLogger(_CLI_LOGGER_NAME)
    _ensure_cli_safe_default(logger)
    return logger


def early_setup_cli_logger_from_env() -> None:
    """env var ベースで ``mixseek.cli`` logger を bootstrap する。

    ``ensure_log_format_env()`` から呼ばれ、``setup_logging()`` 呼び出し前
    (``validate_logfire_flags`` 等の早期エラー) でも logger 経由で適切な
    フォーマットで出力できるようにする。

    既に初期化済みの場合でも、env var が更新されていれば再初期化する
    (``ensure_log_format_env()`` で env var が確定した直後に呼ばれるため)。
    """
    value = os.environ.get("MIXSEEK_LOG_FORMAT", "").lower()
    log_format: LogFormatType = "json" if value == "json" else "text"
    setup_cli_logger(log_format)


def _force_reset_cli_logger() -> None:
    """テスト用途: ``mixseek.cli`` logger の handler を明示的にクリアする。

    pytest fixture から呼び、テスト間で handler が持ち越されてアサーションが
    汚染されるのを防ぐ。本番コードからは呼ばれない。

    ``propagate=False`` + ``NullHandler`` の安全な既定値にリセットすることで、
    ``setup_cli_logger()`` を呼び忘れた後続テストからの偶発的な log 呼び出しが
    root / ``lastResort`` (stderr, WARNING 以上) に leak しないようにする。
    """
    logger = logging.getLogger(_CLI_LOGGER_NAME)
    _clear_cli_handlers(logger)
    logger.propagate = False
    logger.setLevel(logging.NOTSET)
    logger.addHandler(logging.NullHandler())
