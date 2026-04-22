"""CLI 向け logger セットアップ。

2 本立ての専用 logger を管理する:

- ``mixseek.cli``: UI / 操作イベント / エラー通知用。
    常に **stderr** に出力する。text モードは ``CLITextFormatter`` で level 自動着色、
    json モードは ``CLIJsonFormatter`` で 1 行 JSON を出力する。
- ``mixseek.cli.data``: データ出力 (``--output-format json/csv`` / ``--version``) 専用。
    text/json 問わず **stdout** にプレフィックスなしでそのまま出力する
    (``BareFormatter``)。構造化ログ基盤へのパイプ契約 (JSONL) を維持する。

CLI コマンド側は ``get_cli_logger()`` / ``get_data_logger()`` でインスタンスを取得し、
``logger.info(msg, extra={"event": ..., ...})`` のように標準 logging API で呼ぶ。

初期化順序:

1. CLI コマンド先頭の ``ensure_log_format_env()`` 内で ``_early_setup_cli_loggers()``
    が env var から log_format を判定し、CLI logger / data logger を bootstrap する。
    これにより ``validate_logfire_flags`` などの ``setup_logging()`` 前の早期エラーも
    logger 経由で出せる。
2. ``initialize_observability()`` 内の ``setup_logging()`` が ``mixseek`` logger
    (アプリ本体) を別系統でセットアップする。CLI logger とは独立動作。
3. CLI コマンドが ``--log-format`` を明示して初期化し直したい場合は
    ``setup_cli_logger()`` / ``setup_data_logger()`` を直接呼ぶ。
"""

from __future__ import annotations

import logging
import os
import sys

from mixseek.cli.output_formatter import BareFormatter, CLIJsonFormatter, CLITextFormatter
from mixseek.config.logging import LogFormatType

_CLI_LOGGER_NAME = "mixseek.cli"
_DATA_LOGGER_NAME = "mixseek.cli.data"


def _resolve_log_format_from_env() -> LogFormatType:
    """環境変数 ``MIXSEEK_LOG_FORMAT`` から log_format を解決する。

    未設定または ``{"json", "text"}`` 以外の値は ``"text"`` に fallback する。
    """
    value = os.environ.get("MIXSEEK_LOG_FORMAT", "").lower()
    if value == "json":
        return "json"
    return "text"


def _clear_handlers(logger: logging.Logger) -> None:
    """FD リーク防止のため既存ハンドラを close してからクリアする。"""
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


def setup_cli_logger(log_format: LogFormatType) -> logging.Logger:
    """``mixseek.cli`` logger を初期化する。

    UI / 操作イベント / エラー通知を stderr に出力する logger をセットアップする。
    ``propagate=False`` でルート logger への伝播を防ぎ、``mixseek`` アプリ logger と
    独立して動作する。

    - text モード: ``CLITextFormatter`` (level 自動着色、非 TTY / NO_COLOR で ANSI 除去)
    - json モード: ``CLIJsonFormatter`` (1 行 JSON)

    Args:
        log_format: ``"text"`` または ``"json"``。

    Returns:
        初期化済みの ``mixseek.cli`` logger。
    """
    logger = logging.getLogger(_CLI_LOGGER_NAME)
    _clear_handlers(logger)
    logger.propagate = False
    # level は DEBUG まで通す。verbose 判定は呼び出し側 (`if verbose:`) が行う。
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    if log_format == "json":
        handler.setFormatter(CLIJsonFormatter())
    else:
        handler.setFormatter(CLITextFormatter(stream=sys.stderr))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


def setup_data_logger() -> logging.Logger:
    """``mixseek.cli.data`` logger を初期化する。

    データ出力 (``--output-format json/csv`` / ``--version`` 等) 専用の logger。
    text/json 問わず常に stdout にプレフィックスなしでそのまま出力する
    (``BareFormatter``)。パイプ契約 (``| jq`` など) を維持するため、level 着色や
    JSON 封筒は付与しない。

    Returns:
        初期化済みの ``mixseek.cli.data`` logger。
    """
    logger = logging.getLogger(_DATA_LOGGER_NAME)
    _clear_handlers(logger)
    # ``mixseek.cli`` 親 logger の handler (stderr) へ伝播させない。
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(BareFormatter())
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


def get_cli_logger() -> logging.Logger:
    """``mixseek.cli`` logger を取得する。

    ``setup_cli_logger()`` による初期化前であっても NullHandler で安全に動作する
    ``logging.getLogger`` の既定挙動に任せる (メッセージは単に破棄される)。
    通常は ``_early_setup_cli_loggers()`` が ``ensure_log_format_env()`` 経由で
    先に呼ばれているので、初期化済みの logger が返る。
    """
    return logging.getLogger(_CLI_LOGGER_NAME)


def get_data_logger() -> logging.Logger:
    """``mixseek.cli.data`` logger を取得する。"""
    return logging.getLogger(_DATA_LOGGER_NAME)


def _early_setup_cli_loggers() -> None:
    """env var ベースで CLI logger / data logger を bootstrap する。

    ``ensure_log_format_env()`` や ``version_callback`` から呼ばれ、
    ``setup_logging()`` 呼び出し前 (``validate_logfire_flags`` 等の早期エラー) でも
    logger 経由で適切なフォーマットで出力できるようにする。

    既に初期化済みの場合でも、env var が更新されていれば再初期化する
    (ensure_log_format_env() で env var が確定した直後に呼ばれるため)。
    """
    log_format = _resolve_log_format_from_env()
    setup_cli_logger(log_format)
    setup_data_logger()


def _force_reset_cli_loggers() -> None:
    """テスト用途: CLI logger / data logger の handler を明示的にクリアする。

    pytest fixture から呼び、テスト間で handler が持ち越されてアサーションが
    汚染されるのを防ぐ。本番コードからは呼ばれない。
    """
    for name in (_CLI_LOGGER_NAME, _DATA_LOGGER_NAME):
        logger = logging.getLogger(name)
        _clear_handlers(logger)
        logger.propagate = False
        logger.setLevel(logging.NOTSET)


__all__ = [
    "_early_setup_cli_loggers",
    "_force_reset_cli_loggers",
    "get_cli_logger",
    "get_data_logger",
    "setup_cli_logger",
    "setup_data_logger",
]
