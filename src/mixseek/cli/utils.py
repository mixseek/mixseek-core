"""CLI utility functions and constants.

Provides common CLI functionality including exit codes and warning messages.
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Any, NoReturn, TypeVar

import typer

from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode
from mixseek.config.logging import LoggingConfig
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
    workspace: Path | None,
    verbose: bool,
) -> None:
    """Logfire初期化（CLI共通ロジック）

    T096: CLIフラグから直接LogfireConfigを作成（Article 9準拠）
    優先順位: CLI flags > Environment variables > TOML
    CLIフラグは enabled/privacy_mode/capture_http のみ指定、
    project_name/send_to_logfire は環境変数/TOMLから継承

    Args:
        logfire: --logfireフラグ
        logfire_metadata: --logfire-metadataフラグ
        logfire_http: --logfire-httpフラグ
        workspace: ワークスペースパス
        verbose: 詳細ログ表示フラグ
    """
    logfire_config = None

    if logfire or logfire_metadata or logfire_http:
        # 1. まず環境変数/TOMLから基本設定を読み取る
        base_config = None
        if os.getenv("LOGFIRE_PROJECT") or os.getenv("LOGFIRE_SEND_TO_LOGFIRE"):
            # 環境変数が設定されている場合
            base_config = LogfireConfig.from_env()
        elif workspace:
            # TOMLから読み取り
            base_config = LogfireConfig.from_toml(workspace)

        # 2. CLIフラグでプライバシーモードとHTTPキャプチャを決定
        if logfire:
            # --logfire: Full mode (すべてキャプチャ)
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = False
        elif logfire_metadata:
            # --logfire-metadata: Metadata only (プロンプト/応答除外)
            privacy_mode = LogfirePrivacyMode.METADATA_ONLY
            capture_http_flag = False
        elif logfire_http:
            # --logfire-http: Full mode + HTTP capture
            privacy_mode = LogfirePrivacyMode.FULL
            capture_http_flag = True
        else:
            privacy_mode = LogfirePrivacyMode.DISABLED
            capture_http_flag = False

        # 3. CLIフラグ優先でマージ（project_name/send_to_logfireは継承）
        logfire_config = LogfireConfig(
            enabled=True,  # CLI指定
            privacy_mode=privacy_mode,  # CLI指定
            capture_http=capture_http_flag,  # CLI指定
            project_name=base_config.project_name if base_config else None,  # 環境変数/TOML継承
            send_to_logfire=base_config.send_to_logfire if base_config else True,  # 環境変数/TOML継承
        )
    elif os.getenv("LOGFIRE_ENABLED") == "1":
        # 環境変数からLogfireConfig作成
        logfire_config = LogfireConfig.from_env()
    elif workspace:
        # TOML設定を試みる（最低優先度）
        logfire_config = LogfireConfig.from_toml(workspace)

    # 初期化
    if logfire_config is not None and logfire_config.enabled:
        try:
            setup_logfire(logfire_config, workspace)
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
) -> None:
    """標準logging初期化（CLI共通ロジック）

    Args:
        log_level: ログレベル (debug/info/warning/error)
        no_log_console: コンソール出力無効化フラグ
        no_log_file: ファイル出力無効化フラグ
        logfire_enabled: Logfire有効化フラグ
        workspace: ワークスペースパス
        verbose: 詳細ログ表示フラグ

    Note:
        優先順位: CLI flags > Environment variables > TOML > defaults
        CLIフラグは --no-log-console, --no-log-file で無効化を指定
    """
    # Build LoggingConfig from CLI flags (highest priority)
    # CLI flags override environment variables and TOML
    config = LoggingConfig(
        logfire_enabled=logfire_enabled,
        console_enabled=not no_log_console,
        file_enabled=not no_log_file,
        log_level=log_level,  # type: ignore[arg-type]
    )

    # Setup standard logging
    try:
        setup_logging(config, workspace)
        if verbose:
            typer.secho(
                f"✓ Logging configured (level={log_level}, console={not no_log_console}, file={not no_log_file})",
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
