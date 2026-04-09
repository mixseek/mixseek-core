"""CLI utility functions and constants.

Provides common CLI functionality including exit codes and warning messages.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Any, NoReturn, TypeVar, cast

import typer
from pydantic import ValidationError

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
    warning_message = "⚠️  Development/Testing only - Not for production use\n"
    print(warning_message, file=sys.stderr, end="")


def exit_with_error(message: str, code: int = EXIT_ERROR) -> NoReturn:
    """Exit the program with an error message.

    Args:
        message: Error message to display
        code: Exit code (default: EXIT_ERROR)

    Raises:
        SystemExit: Always raises to exit the program
    """
    print(f"Error: {message}", file=sys.stderr)
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
        logfire_config = LogfireConfig.from_env()
        # CLI値で console_output を上書き（CLI > env の優先度）
        logfire_config = logfire_config.model_copy(update={"console_output": console_enabled})

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
                typer.secho("✓ Logfire observability enabled", fg=typer.colors.GREEN, err=True)
        except Exception as e:
            typer.secho(
                f"WARNING: Logfire initialization failed: {e}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            if verbose:
                typer.echo(traceback.format_exc(), err=True)


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
    try:
        config = LoggingConfig(
            logfire_enabled=logfire_enabled,
            console_enabled=not no_log_console,
            file_enabled=not no_log_file,
            log_level=cast(LevelName, log_level),
            log_format=cast(LogFormatType, log_format),
        )
    except ValidationError as e:
        typer.echo(f"Error: ログ設定が不正です: {e}", err=True)
        raise typer.Exit(code=2)

    try:
        setup_logging(config, workspace)
        if verbose:
            typer.secho(
                f"✓ Logging configured (level={log_level}, format={log_format}, "
                f"console={not no_log_console}, file={not no_log_file})",
                fg=typer.colors.GREEN,
                err=True,
            )
    except Exception as e:
        typer.secho(
            f"WARNING: Logging setup failed: {e}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        if verbose:
            typer.echo(traceback.format_exc(), err=True)


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
        typer.secho(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            fg=typer.colors.RED,
            err=True,
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
