"""CLI utility functions and constants.

Provides common CLI functionality including exit codes and warning messages.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Any, NoReturn, TypeVar, cast

import click
import typer
from pydantic import ValidationError

from mixseek.cli.output_logger import _early_setup_cli_loggers, get_cli_logger
from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.config.logging import LevelName, LogFormatType, LoggingConfig
from mixseek.observability import setup_logfire, setup_logging

# Exit code constants
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_INTERRUPT = 130

T = TypeVar("T")


def show_development_warning() -> None:
    """Display development/testing only warning to stderr.

    This warning is displayed for all development/testing commands to remind
    users that these commands are not intended for production use.
    """
    get_cli_logger().warning(
        "⚠️  Development/Testing only - Not for production use",
        extra={"event": "cli.dev_warning"},
    )


def exit_with_error(message: str, code: int = EXIT_ERROR) -> NoReturn:
    """Exit the program with an error message.

    Args:
        message: Error message to display
        code: Exit code (default: EXIT_ERROR)

    Raises:
        SystemExit: Always raises to exit the program
    """
    get_cli_logger().error(
        f"Error: {message}",
        extra={"event": "cli.exit_with_error", "error": message, "exit_code": code},
    )
    sys.exit(code)


def exit_success() -> NoReturn:
    """Exit the program with success code.

    Raises:
        SystemExit: Always raises to exit the program
    """
    sys.exit(EXIT_SUCCESS)


def mutually_exclusive_group(group_size: int = 2) -> Any:
    """Create callback for mutually exclusive typer options.

    This function creates a callback that tracks option usage and ensures
    that only a specified number of options from a group can be used together.

    Uses typer Context to store state, avoiding closure-based state that
    could leak between test runs.

    Args:
        group_size: Maximum number of options that can be used together.
                    Set to 1 for strict mutual exclusivity.

    Returns:
        Callback function for typer.Option

    Example:
        >>> exclusivity = mutually_exclusive_group(group_size=1)
        >>> def command(
        ...     config: Path | None = typer.Option(None, "--config", callback=exclusivity),
        ...     agent: str | None = typer.Option(None, "--agent", callback=exclusivity)
        ... ):
        ...     pass  # --config and --agent cannot be used together
    """

    def callback(ctx: typer.Context, param: typer.CallbackParam, value: T | None) -> T | None:
        """Callback to track and validate mutually exclusive options.

        Args:
            ctx: Typer context (used for state storage)
            param: Parameter being processed
            value: Parameter value

        Returns:
            The parameter value (unchanged)

        Raises:
            typer.BadParameter: If too many options from group are used
        """
        if value is not None and param.name is not None:
            # Store group state in context to avoid closure state leakage
            if not hasattr(ctx, "obj") or ctx.obj is None:
                ctx.obj = {}
            if "_exclusive_group" not in ctx.obj:
                ctx.obj["_exclusive_group"] = set()

            group: set[str] = ctx.obj["_exclusive_group"]

            if len(group) >= group_size:
                existing = ", ".join(f"--{name}" for name in sorted(group))
                raise typer.BadParameter(f"Option --{param.name} is mutually exclusive with {existing}")
            group.add(param.name)

        return value

    return callback


def setup_logfire_from_cli(
    logfire: bool,
    logfire_metadata: bool,
    logfire_http: bool,
    verbose: bool,
    log_format: str = "text",
    workspace: Path | None = None,
    file_enabled: bool = True,
    console_enabled: bool = True,
) -> None:
    """Logfire初期化（CLI共通ロジック）

    Args:
        logfire: --logfireフラグ
        logfire_metadata: --logfire-metadataフラグ
        logfire_http: --logfire-httpフラグ
        verbose: 詳細ログ表示フラグ
        log_format: ログ出力形式（text/json）
        workspace: ワークスペースパス
        file_enabled: ファイル出力有効化フラグ
        console_enabled: コンソール出力有効化フラグ
    """
    logfire_config = None
    cli_logger = get_cli_logger()

    if logfire or logfire_metadata or logfire_http:
        # 環境変数から基本設定を読み取る（project_name/send_to_logfire の継承用）
        base_config = None
        if os.getenv("LOGFIRE_PROJECT") or os.getenv("LOGFIRE_SEND_TO_LOGFIRE"):
            base_config = LogfireConfig.from_env()

        # CLIフラグでプライバシーモードとHTTPキャプチャを決定
        if logfire:
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = False
        elif logfire_metadata:
            privacy_mode = LogfirePrivacyMode.METADATA_ONLY
            capture_http_flag = False
        elif logfire_http:
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = True
        else:
            privacy_mode = LogfirePrivacyMode.DISABLED
            capture_http_flag = False

        # CLIフラグ優先でマージ
        logfire_config = LogfireConfig(
            enabled=True,
            privacy_mode=privacy_mode,
            capture_http=capture_http_flag,
            project_name=base_config.project_name if base_config else None,
            send_to_logfire=base_config.send_to_logfire if base_config else True,
            console_output=console_enabled,
        )
    elif os.getenv("LOGFIRE_ENABLED") == "1":
        # CLI値で console_output を上書き（CLI > env の優先度）
        logfire_config = LogfireConfig.from_env().model_copy(update={"console_output": console_enabled})

    # 初期化
    if logfire_config is not None and logfire_config.enabled:
        try:
            setup_logfire(
                logfire_config,
                log_format=cast(LogFormatType, log_format),
                workspace=workspace,
                file_enabled=file_enabled,
            )
            if verbose:
                # 成功通知の GREEN は text モードのみ視認される構造色 (click.style 直書き)。
                cli_logger.info(
                    click.style("✓ Logfire observability enabled", fg="green"),
                    extra={"event": "logfire.enabled"},
                )
        except Exception as e:
            cli_logger.warning(
                f"WARNING: Logfire initialization failed: {e}",
                extra={
                    "event": "logfire.init_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            if verbose:
                cli_logger.warning(
                    traceback.format_exc(),
                    extra={"event": "logfire.init_failed_traceback"},
                )


def setup_logging_from_cli(
    log_level: str,
    no_log_console: bool,
    no_log_file: bool,
    logfire_enabled: bool,
    workspace: Path | None,
    verbose: bool,
    log_format: str = "text",
) -> None:
    """標準logging初期化（CLI共通ロジック）

    Args:
        log_level: ログレベル (debug/info/warning/error)
        no_log_console: コンソール出力無効化フラグ
        no_log_file: ファイル出力無効化フラグ
        logfire_enabled: Logfire有効化フラグ
        workspace: ワークスペースパス
        verbose: 詳細ログ表示フラグ
        log_format: ログ出力形式（text/json）
    """
    cli_logger = get_cli_logger()

    try:
        config = LoggingConfig(
            logfire_enabled=logfire_enabled,
            console_enabled=not no_log_console,
            file_enabled=not no_log_file,
            log_level=cast(LevelName, log_level),
            log_format=cast(LogFormatType, log_format),
        )
    except ValidationError as e:
        cli_logger.error(
            f"Error: ログ設定が不正です: {e}",
            extra={"event": "logging.config_invalid", "error": str(e)},
        )
        raise typer.Exit(code=2)

    try:
        setup_logging(config, workspace)
        if verbose:
            cli_logger.info(
                click.style(
                    f"✓ Logging configured (level={log_level}, format={log_format}, "
                    f"console={not no_log_console}, file={not no_log_file})",
                    fg="green",
                ),
                extra={
                    "event": "logging.configured",
                    "log_level": log_level,
                    "log_format": log_format,
                    "console_enabled": not no_log_console,
                    "file_enabled": not no_log_file,
                },
            )
    except Exception as e:
        cli_logger.warning(
            f"WARNING: Logging setup failed: {e}",
            extra={
                "event": "logging.setup_failed",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        if verbose:
            cli_logger.warning(
                traceback.format_exc(),
                extra={"event": "logging.setup_failed_traceback"},
            )


def ensure_log_format_env(cli_log_format: str | None) -> str:
    """CLI引数の log_format を解決し、環境変数 MIXSEEK_LOG_FORMAT に反映する。

    ``setup_logging()`` 呼び出し前の CLI 出力 (例: ``validate_logfire_flags``) が
    正しいフォーマット (text / json) で出力されるように、env var を確定した直後に
    ``mixseek.cli`` / ``mixseek.cli.data`` logger を早期初期化する。

    値は小文字に正規化し、``{"json", "text"}`` 以外は ``"text"`` に fallback する。
    これにより "JSON"/"Json" 等の表記揺れや不正値が env と戻り値に伝搬しないようにする。

    Args:
        cli_log_format: CLI ``--log-format`` の値。None の場合は既存の環境変数または
            "text" を fallback に採用する。

    Returns:
        実効的に採用した log_format ("text" または "json")。
    """
    effective = cli_log_format if cli_log_format is not None else os.getenv("MIXSEEK_LOG_FORMAT", "text")
    effective = effective.lower()
    if effective not in {"json", "text"}:
        effective = "text"
    os.environ["MIXSEEK_LOG_FORMAT"] = effective
    # env var 確定後に CLI logger / data logger を (再) 初期化。
    # setup_logging() は initialize_observability() で後から呼ばれるが、
    # それより前の cli_logger 呼び出しも適切なフォーマットで出力するため。
    _early_setup_cli_loggers()
    return effective


def validate_logfire_flags(logfire: bool, logfire_metadata: bool, logfire_http: bool) -> None:
    """Logfireフラグの排他的チェック。

    Args:
        logfire: --logfireフラグ
        logfire_metadata: --logfire-metadataフラグ
        logfire_http: --logfire-httpフラグ

    Raises:
        typer.Exit: 複数のLogfireフラグが指定された場合
    """
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        get_cli_logger().error(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            extra={
                "event": "logfire.flags_exclusive_violation",
                "logfire": logfire,
                "logfire_metadata": logfire_metadata,
                "logfire_http": logfire_http,
            },
        )
        raise typer.Exit(1)


def initialize_observability(
    *,
    log_level: str,
    no_log_console: bool,
    no_log_file: bool,
    logfire: bool,
    logfire_metadata: bool,
    logfire_http: bool,
    verbose: bool,
    log_format: str | None,
    workspace: Path | None,
) -> None:
    """CLI共通のロギング・Logfire初期化。

    標準logging初期化、Logfire初期化を一括で行う。
    evaluate/exec/member/team 全コマンドで共通のロジックを統一。
    Logfireフラグの排他チェックは validate_logfire_flags() で事前に行うこと。

    Args:
        log_level: ログレベル (debug/info/warning/error/critical)
        no_log_console: コンソール出力無効化フラグ
        no_log_file: ファイル出力無効化フラグ
        logfire: --logfireフラグ
        logfire_metadata: --logfire-metadataフラグ
        logfire_http: --logfire-httpフラグ
        verbose: 詳細ログ表示フラグ
        log_format: ログ出力形式（text/json/None）
        workspace: 解決済みワークスペースパス
    """
    # 標準logging初期化（Logfireより先に実行）
    logfire_enabled = logfire or logfire_metadata or logfire_http or os.getenv("LOGFIRE_ENABLED") == "1"
    effective_log_format = log_format if log_format is not None else os.getenv("MIXSEEK_LOG_FORMAT", "text")
    setup_logging_from_cli(
        log_level,
        no_log_console,
        no_log_file,
        logfire_enabled,
        workspace,
        verbose,
        effective_log_format,
    )

    # Logfire初期化
    setup_logfire_from_cli(
        logfire,
        logfire_metadata,
        logfire_http,
        verbose,
        log_format=effective_log_format,
        workspace=workspace,
        file_enabled=not no_log_file,
        console_enabled=not no_log_console,
    )
