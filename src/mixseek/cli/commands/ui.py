"""UI command for launching Streamlit app."""

import os
from pathlib import Path

import typer
from streamlit.web import cli as stcli

from mixseek.cli.common_options import (
    LOG_FORMAT_OPTION,
    LOG_LEVEL_OPTION,
    LOGFIRE_HTTP_OPTION,
    LOGFIRE_METADATA_OPTION,
    LOGFIRE_OPTION,
    NO_LOG_CONSOLE_OPTION,
    NO_LOG_FILE_OPTION,
    WORKSPACE_OPTION,
)
from mixseek.cli.output import cli_echo
from mixseek.cli.utils import ensure_log_format_env
from mixseek.config import ConfigurationManager, UISettings
from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.config.logfire import LogfireConfig, LogfirePrivacyMode


def ui(
    port: int | None = typer.Option(None, help="Port to run Streamlit on (overrides config)"),
    workspace: Path | None = WORKSPACE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
    log_format: str | None = LOG_FORMAT_OPTION,
) -> None:
    """Launch Mixseek UI (Streamlit application).

    Workspace and port are configured via ConfigurationManager with priority:
    CLI args > Environment variables > .env file > TOML config > Defaults

    Args:
        port: Port to run Streamlit on (overrides config)
        workspace: Workspace path
        logfire: Enable Logfire (full mode)
        logfire_metadata: Enable Logfire (metadata only)
        logfire_http: Enable Logfire (full + HTTP capture)
        log_level: Global log level (debug/info/warning/error)
        no_log_console: Disable console log output
        no_log_file: Disable file log output

    Examples:
        mixseek ui

        mixseek ui --port 8080

        mixseek ui --logfire

        mixseek ui --logfire-metadata

        mixseek ui --logfire-http

        mixseek ui --log-level debug

        mixseek ui --no-log-console
    """
    # log_format を最初に解決し、環境変数へ設定する。
    # これにより、以降の cli_echo が JSON モードを正しく判定できる
    # (ui コマンドは setup_logging を自プロセスで呼ばず Streamlit サブプロセスに委ねるため)。
    ensure_log_format_env(log_format)

    # 排他的チェック（複数のlogfireフラグは指定できない）
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        cli_echo(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            err=True,
            event="ui.logfire_flags_exclusive_violation",
            logfire=logfire,
            logfire_metadata=logfire_metadata,
            logfire_http=logfire_http,
        )
        raise typer.Exit(1)

    # Resolve workspace and port using ConfigurationManager
    try:
        config_manager = ConfigurationManager(workspace=workspace)
        ui_settings: UISettings = config_manager.load_settings(UISettings)

        # Use CLI-provided port if given, otherwise use settings
        final_port = port if port is not None else ui_settings.port

    except Exception as e:
        cli_echo(
            f"Error: Failed to load configuration: {e}",
            err=True,
            event="ui.config_load_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise typer.Exit(1)

    # Logfire設定（CLIフラグが指定された場合のみ）
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

        # 3. 環境変数に書き込み（Streamlitプロセスに渡すため）
        os.environ["LOGFIRE_ENABLED"] = "1"
        os.environ["LOGFIRE_PRIVACY_MODE"] = privacy_mode.value
        if capture_http_flag:
            os.environ["LOGFIRE_CAPTURE_HTTP"] = "1"

        # project_name/send_to_logfireは既存の環境変数/TOMLから継承
        if base_config and base_config.project_name:
            os.environ["LOGFIRE_PROJECT"] = base_config.project_name
        if base_config is not None:
            os.environ["LOGFIRE_SEND_TO_LOGFIRE"] = "1" if base_config.send_to_logfire else "0"

    # ワークスペースパスを環境変数として設定（Streamlitプロセスに渡すため）
    os.environ[WORKSPACE_ENV_VAR] = str(ui_settings.workspace_path)

    # ロギング設定（環境変数経由でStreamlitに渡す）
    # MIXSEEK_LOG_FORMAT は関数先頭で既に設定済み
    os.environ["MIXSEEK_LOG_LEVEL"] = log_level
    os.environ["MIXSEEK_LOG_CONSOLE"] = "0" if no_log_console else "1"
    os.environ["MIXSEEK_LOG_FILE"] = "0" if no_log_file else "1"

    app_path = Path(__file__).parent.parent.parent / "ui" / "app.py"

    if not app_path.exists():
        cli_echo(
            f"Error: Streamlit app not found at {app_path}",
            err=True,
            event="ui.app_not_found",
            app_path=str(app_path),
        )
        raise typer.Exit(1)

    try:
        stcli.main_run([str(app_path), "--server.port", str(final_port)], standalone_mode=False)
    except KeyboardInterrupt:
        cli_echo("\nStreamlit server stopped.", event="ui.server_stopped")
    except SystemExit as e:
        # Streamlit may raise SystemExit(0) or SystemExit(None) on normal termination
        if e.code:
            cli_echo(
                f"Error: Streamlit exited with code {e.code}",
                err=True,
                event="ui.streamlit_exit_error",
                exit_code=e.code,
            )
            raise typer.Exit(1)
    except Exception as e:
        cli_echo(
            f"Error: Streamlit failed to start: {e}",
            err=True,
            event="ui.streamlit_start_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise typer.Exit(1)
