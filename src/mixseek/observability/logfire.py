"""Logfire Observability統合。

text/json で ConsoleOptions の使用/不使用を切り替える。
- text: ConsoleOptions + TeeWriter(stderr + mixseek.log) でスパンツリー表示
- json: ConsoleOptions無効 + JsonSpanProcessor で構造化JSON出力
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path
from typing import IO, Any, TextIO

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.config.logging import LogFormatType
from mixseek.observability.tee_writer import TeeWriter

logger = logging.getLogger(__name__)


class JsonSpanProcessor:
    """OpenTelemetry スパンを構造化 JSON ログレコードに変換し、"mixseek.traces" ロガーに書き込む。

    SpanProcessor プロトコルを直接実装する。
    "mixseek.traces" → 親 "mixseek" に伝搬 → StreamHandler + FileHandler で出力。
    LogfireLoggingHandler には SkipTracesFilter で再送防止済み。
    """

    def __init__(self) -> None:
        self._traces_logger = logging.getLogger("mixseek.traces")

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        """スパン開始時に構造化 JSON レコードを出力"""
        record_data: dict[str, Any] = {
            "type": "span_start",
            "span_name": span.name,
            "span_id": format(span.context.span_id, "016x"),
            "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            "attributes": dict(span.attributes) if span.attributes else {},
        }
        self._traces_logger.info(
            f"{span.name} started",
            extra=record_data,
        )

    def on_end(self, span: Any) -> None:
        """スパン完了時に構造化 JSON レコードを出力"""
        duration_ms = None
        if span.end_time and span.start_time:
            duration_ms = (span.end_time - span.start_time) / 1_000_000

        record_data: dict[str, Any] = {
            "type": "span_end",
            "span_name": span.name,
            "span_id": format(span.context.span_id, "016x"),
            "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            "duration_ms": duration_ms,
            "status": span.status.status_code.name if span.status else None,
            "attributes": dict(span.attributes) if span.attributes else {},
        }
        self._traces_logger.info(
            f"{span.name} completed",
            extra=record_data,
        )

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def setup_logfire(
    config: LogfireConfig,
    log_format: LogFormatType = "text",
    workspace: Path | None = None,
    file_enabled: bool = True,
) -> None:
    """Logfire初期化。log_format に応じて出力方式を切り替える。

    - text: ConsoleOptions + TeeWriter(stderr + mixseek.log) でスパンツリー表示
    - json: ConsoleOptions無効 + JsonSpanProcessor で構造化JSON出力

    Args:
        config: Logfire設定
        log_format: ログ出力形式（text/json）
        workspace: ワークスペースパス（ファイル出力用）
        file_enabled: ファイル出力有効化フラグ
    """
    if not config.enabled:
        logger.debug("Logfire is disabled (config.enabled=False)")
        return

    # 再初期化時のFDリーク防止: 既存ファイルハンドルをクローズ
    _cleanup_file_handles()

    try:
        import logfire
    except ImportError as e:
        raise ImportError("Logfire not installed. Install with: uv sync --extra logfire") from e

    try:
        # T098: LOGFIRE_PROJECT 環境変数の設定
        if config.project_name:
            os.environ["LOGFIRE_PROJECT"] = config.project_name

        additional_processors: list[Any] = []
        console: Any = False
        file_handle: IO[str] | None = None

        if log_format == "text":
            # Mode 3: ConsoleOptions + TeeWriter
            # console_output と file_enabled に基づいて writers を組み立てる
            writers: list[TextIO] = []
            if config.console_output:
                writers.append(sys.stderr)
            if file_enabled and workspace:
                log_dir = workspace / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                file_handle = open(log_dir / "mixseek.log", "a", encoding="utf-8")  # noqa: SIM115
                _logfire_file_handles.append(file_handle)
                writers.append(file_handle)

            if writers:
                from logfire import ConsoleOptions

                if len(writers) == 1:
                    console = ConsoleOptions(output=writers[0])
                else:
                    console = ConsoleOptions(output=TeeWriter(writers))
            # writers が空の場合は console=False のまま
        elif log_format == "json":
            # Mode 4: ConsoleOptions無効 + JsonSpanProcessor
            console = False
            additional_processors.append(JsonSpanProcessor())

        logfire.configure(
            send_to_logfire=config.send_to_logfire,
            console=console,
            additional_span_processors=additional_processors or None,
        )

        # Mode 3 (logfire + text): ConsoleOptions 確立後に StreamHandler/FileHandler を除去
        # ConsoleOptions が有効な場合のみ（writers が空でない場合）
        if log_format == "text" and console is not False:
            finalize_mode3_handlers()

        # PydanticAI instrumentation（プライバシーモード対応）
        if config.privacy_mode == LogfirePrivacyMode.METADATA_ONLY:
            logfire.instrument_pydantic_ai(
                include_content=False,
                include_binary_content=False,
            )
            logger.info("Logfire instrumentation: metadata_only mode (content excluded)")

        elif config.privacy_mode == LogfirePrivacyMode.FULL:
            logfire.instrument_pydantic_ai()
            logger.info("Logfire instrumentation: full mode (all content captured)")

        elif config.privacy_mode == LogfirePrivacyMode.DISABLED:
            logger.info("Logfire instrumentation: disabled mode (no instrumentation)")
            return

        # HTTPX instrumentation（オプション）
        if config.capture_http:
            try:
                logfire.instrument_httpx(capture_all=True)
                logger.info("HTTPX instrumentation enabled (HTTP requests/responses captured)")
            except Exception as e:
                logger.warning(f"HTTPX instrumentation failed: {e}")

        logger.info("Logfire observability enabled successfully")

    except Exception as e:
        raise RuntimeError(f"Logfire initialization failed: {e}") from e


def finalize_mode3_handlers() -> None:
    """Mode 3 (logfire+text) 用: ConsoleOptions 確立後に StreamHandler/FileHandler を除去する。

    setup_logging() は全モードで StreamHandler/FileHandler を追加する（setup_logfire() 完了前の
    ログ欠損防止のため）。Mode 3 では ConsoleOptions + TeeWriter が全出力を担当するので、
    logfire.configure() 完了後にこれらを除去して重複を防止する。
    """
    mixseek_logger = logging.getLogger("mixseek")
    handlers_to_remove = [
        h for h in mixseek_logger.handlers if (type(h) is logging.StreamHandler or isinstance(h, logging.FileHandler))
    ]
    for h in handlers_to_remove:
        # FileHandler のみクローズ（StreamHandler(stderr) はクローズしない）
        if isinstance(h, logging.FileHandler):
            h.close()
        mixseek_logger.removeHandler(h)


# ファイルハンドル管理（text + logfire モード用）
_logfire_file_handles: list[IO[str]] = []


def _cleanup_file_handles() -> None:
    """プロセス終了時にファイルハンドルをクローズ。"""
    for handle in _logfire_file_handles:
        try:
            if not handle.closed:
                handle.close()
        except Exception:
            pass
    _logfire_file_handles.clear()


atexit.register(_cleanup_file_handles)
