"""Logfire observability integration (Article 9 compliant).

このモジュールはLogfireの初期化とPydantic AI instrumentationを提供します。
すべての処理はConstitution Article 9（Data Accuracy Mandate）に準拠します。

Path 2 Architecture:
    Logfire spans → ConsoleOptions(output=TeeWriter) → Console (stderr) + File
                → send_to_logfire → Logfire cloud (optional)
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.observability.tee_writer import TeeWriter

logger = logging.getLogger(__name__)


def setup_logfire(config: LogfireConfig, workspace: Path | None = None) -> None:
    """Logfire初期化（Article 9準拠）.

    Args:
        config: Logfire設定
        workspace: MIXSEEKワークスペースパス（ファイル出力用）

    Raises:
        ImportError: logfireパッケージ未インストール時
        RuntimeError: 初期化失敗時

    Note:
        - config.enabled=Falseの場合は何もしない（early return）
        - Pydantic AI instrumentationを自動設定
        - プライバシーモードに応じてセンシティブデータを除外
        - HTTPXインストルメンテーションはオプション
        - ConsoleOptionsでローカル出力を制御（console/file）

    Example:
        >>> from mixseek.config.logfire import LogfireConfig
        >>> config = LogfireConfig.from_env()
        >>> setup_logfire(config, workspace=Path("/path/to/workspace"))
        ✓ Logfire observability enabled
    """
    if not config.enabled:
        logger.debug("Logfire is disabled (config.enabled=False)")
        return

    # Import logfire (graceful degradation)
    try:
        import logfire
    except ImportError as e:
        raise ImportError("Logfire not installed. Install with: uv sync --extra logfire") from e

    try:
        # T098 Revision: Restore LOGFIRE_PROJECT environment variable
        # Article 9 Exception: Logfire library design constraint
        # - logfire.configure() has NO project_name parameter
        # - LOGFIRE_PROJECT environment variable is the ONLY way to set project name
        # - This is an external library requirement, not implicit fallback
        if config.project_name:
            os.environ["LOGFIRE_PROJECT"] = config.project_name

        # Build TeeWriter for local output destinations
        console_options = _build_console_options(config, workspace)

        # Configure Logfire with send_to_logfire and console options
        logfire.configure(
            send_to_logfire=config.send_to_logfire,
            console=console_options,
        )

        # Pydantic AI instrumentation
        if config.privacy_mode == LogfirePrivacyMode.METADATA_ONLY:
            # プロンプト/応答を除外（本番推奨）
            logfire.instrument_pydantic_ai(
                include_content=False,  # プロンプト/応答除外
                include_binary_content=False,  # バイナリ除外
            )
            logger.info("Logfire instrumentation: metadata_only mode (content excluded)")

        elif config.privacy_mode == LogfirePrivacyMode.FULL:
            # すべてキャプチャ（開発環境）
            logfire.instrument_pydantic_ai()
            logger.info("Logfire instrumentation: full mode (all content captured)")

        elif config.privacy_mode == LogfirePrivacyMode.DISABLED:
            # Logfire無効（instrumentationなし）
            logger.info("Logfire instrumentation: disabled mode (no instrumentation)")
            return

        # HTTPX instrumentation（オプション）
        if config.capture_http:
            try:
                logfire.instrument_httpx(capture_all=True)
                logger.info("HTTPX instrumentation enabled (HTTP requests/responses captured)")
            except Exception as e:
                # HTTPXインストルメンテーション失敗は警告のみ
                logger.warning(f"HTTPX instrumentation failed: {e}")

        # 成功ログ（CLI側で表示を制御）
        logger.info("Logfire observability enabled successfully")

    except Exception as e:
        raise RuntimeError(f"Logfire initialization failed: {e}") from e


# Store file handles for cleanup (module-level to prevent garbage collection)
_logfire_file_handles: list[TextIO] = []


def _cleanup_file_handles() -> None:
    """Close all stored file handles on process exit.

    Registered with atexit to ensure proper cleanup of file resources.
    This prevents resource leaks in long-running processes and test environments.
    """
    for handle in _logfire_file_handles:
        try:
            if not handle.closed:
                handle.close()
        except Exception:
            pass  # Ignore errors during cleanup
    _logfire_file_handles.clear()


# Register cleanup function
atexit.register(_cleanup_file_handles)


def _build_console_options(config: LogfireConfig, workspace: Path | None) -> Any:
    """Build ConsoleOptions for Logfire span local output.

    Args:
        config: Logfire configuration with console_output/file_output settings
        workspace: Workspace path for file output

    Returns:
        ConsoleOptions with TeeWriter, or False if no local output enabled

    Note:
        TeeWriter enables simultaneous output to multiple destinations.
        File handles are stored in module-level list to prevent garbage collection.
    """
    from logfire import ConsoleOptions

    writers: list[TextIO] = []

    # Add console output (stderr)
    if config.console_output:
        writers.append(sys.stderr)

    # Add file output if workspace provided
    if config.file_output and workspace is not None:
        log_dir = workspace / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "logfire.log"
        # Open file in append mode, store handle to prevent garbage collection
        file_handle = open(log_path, "a", encoding="utf-8")  # noqa: SIM115
        _logfire_file_handles.append(file_handle)
        writers.append(file_handle)

    # Return ConsoleOptions with TeeWriter, or False if no outputs
    if not writers:
        return False

    if len(writers) == 1:
        # Single output - use directly without TeeWriter
        return ConsoleOptions(output=writers[0])

    # Multiple outputs - use TeeWriter (duck-typed as TextIO)
    tee_writer = TeeWriter(writers)
    return ConsoleOptions(output=tee_writer)  # type: ignore[arg-type]
