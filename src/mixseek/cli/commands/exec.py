"""mixseek exec コマンド実装"""

import asyncio
import logging
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from mixseek.cli.common_options import (
    LOG_LEVEL_OPTION,
    LOGFIRE_HTTP_OPTION,
    LOGFIRE_METADATA_OPTION,
    LOGFIRE_OPTION,
    NO_LOG_CONSOLE_OPTION,
    NO_LOG_FILE_OPTION,
    VERBOSE_OPTION,
    WORKSPACE_OPTION,
)
from mixseek.cli.utils import setup_logfire_from_cli, setup_logging_from_cli
from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.core.auth import close_all_auth_clients
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.orchestrator.models import ExecutionSummary

logger = logging.getLogger(__name__)

# Typer options - 関数外で定義してB008警告を回避
CONFIG_OPTION = typer.Option(
    None,
    "--config",
    "-c",
    help="オーケストレータ設定TOMLファイルパス(必須)",
)
TIMEOUT_OPTION = typer.Option(
    None,
    "--timeout",
    help="チーム単位タイムアウト(秒)",
)
OUTPUT_FORMAT_OPTION = typer.Option(
    "text",
    "--output-format",
    "-f",
    help="出力フォーマット(text/json)",
)


def _validate_logfire_flags(logfire: bool, logfire_metadata: bool, logfire_http: bool) -> None:
    """Logfireフラグの排他的検証

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
        raise typer.Exit(code=1)


def _load_and_validate_config(config: Path | None, workspace: Path | None) -> OrchestratorSettings:
    """設定ファイルの読み込みと検証（FR-011: OrchestratorSettings直接返却）

    Args:
        config: 設定ファイルパス
        workspace: ワークスペースパス（Article 9準拠: 明示的指定）

    Returns:
        OrchestratorSettings: オーケストレータ設定

    Raises:
        typer.Exit: 設定ファイル未指定時
        Exception: 設定読み込みエラー時
    """
    if config is None:
        typer.echo("Error: --config オプションは必須です", err=True)
        typer.echo('Usage: mixseek exec "prompt" --config /path/to/orchestrator.toml', err=True)
        raise typer.Exit(code=1)

    logger.debug(f"Config path: {config}")
    logger.debug(f"Config path type: {type(config)}")
    logger.debug(f"Config path is_absolute: {config.is_absolute()}")

    return load_orchestrator_settings(config, workspace=workspace)


async def _execute_orchestration(
    orchestrator: Orchestrator,
    user_prompt: str,
    timeout: int | None,
    output_format: str,
    team_count: int,
) -> ExecutionSummary:
    """オーケストレーション実行

    Args:
        orchestrator: Orchestratorインスタンス
        user_prompt: ユーザプロンプト
        timeout: タイムアウト(秒)
        output_format: 出力フォーマット
        team_count: チーム数

    Returns:
        ExecutionSummary: 実行結果サマリー
    """
    if output_format == "text":
        typer.echo("🚀 MixSeek Orchestrator")
        typer.echo("━" * 60)
        typer.echo(f"\n📝 Task: {user_prompt}\n")
        typer.echo(f"🔄 Running {team_count} teams in parallel...\n")

    return await orchestrator.execute(
        user_prompt=user_prompt,
        timeout_seconds=timeout,
    )


def _output_results(summary: ExecutionSummary, output_format: str) -> None:
    """実行結果の出力

    Note: exec コマンドでは常に DuckDB に保存されます。

    Args:
        summary: 実行結果サマリー
        output_format: 出力フォーマット(text/json)
    """
    if output_format == "json":
        print(summary.model_dump_json(indent=2))
    else:
        _print_text_summary(summary)


def exec_command(
    user_prompt: str = typer.Argument(..., help="ユーザプロンプト"),
    config: Path = CONFIG_OPTION,
    timeout: int | None = TIMEOUT_OPTION,
    workspace: Path | None = WORKSPACE_OPTION,
    output_format: str = OUTPUT_FORMAT_OPTION,
    verbose: bool = VERBOSE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
) -> None:
    """ユーザプロンプトを複数チームで並列実行

    Note: exec コマンドではリーダーボード機能のため、常に DuckDB に保存されます。

    Args:
        user_prompt: ユーザプロンプト
        config: 設定ファイルパス
        timeout: タイムアウト(秒)
        workspace: ワークスペースパス
        output_format: 出力フォーマット
        verbose: 詳細ログ表示
        logfire: Logfire完全モード
        logfire_metadata: Logfireメタデータモード
        logfire_http: Logfire HTTPキャプチャモード
        log_level: グローバルログレベル
        no_log_console: コンソールログ出力無効化
        no_log_file: ファイルログ出力無効化
    """

    async def _execute() -> None:
        try:
            # 1. Logfireフラグ検証
            _validate_logfire_flags(logfire, logfire_metadata, logfire_http)

            # 2. ワークスペースパス解決（Phase 12 T085: ConfigurationManager経由）
            # Note: workspace_pathはLogfire初期化にのみ使用（オプショナル機能）
            # load_orchestrator_settings()は独自にworkspace検証を行う（FR-011）
            workspace_path: Path | None = None
            try:
                config_manager = ConfigurationManager(workspace=workspace)
                orchestrator_settings: OrchestratorSettings = config_manager.load_settings(OrchestratorSettings)
                workspace_path = orchestrator_settings.workspace_path
            except Exception:
                # ConfigurationManager失敗時はCLI引数を使用（Logfire用）
                # Article 9準拠: load_orchestrator_settings()で明示的検証（FR-011）
                workspace_path = workspace

            # Issue #273 fix: 環境変数に設定して後続コンポーネントに伝搬
            if workspace_path:
                os.environ[WORKSPACE_ENV_VAR] = str(workspace_path)

            # 3. 標準logging初期化（Logfireより先に実行）
            logfire_enabled = logfire or logfire_metadata or logfire_http
            setup_logging_from_cli(log_level, no_log_console, no_log_file, logfire_enabled, workspace_path, verbose)

            # 4. Logfire初期化
            setup_logfire_from_cli(logfire, logfire_metadata, logfire_http, workspace_path, verbose)

            # 5. 設定読み込み（Article 9準拠: workspace明示的に渡す, FR-011: OrchestratorSettings直接返却）
            orchestrator_settings = _load_and_validate_config(config, workspace)

            # 6. Orchestrator初期化（FR-011: OrchestratorSettings直接受け取り）
            # Note: exec コマンドではリーダーボード機能のため常に DB 保存
            orchestrator = Orchestrator(settings=orchestrator_settings, save_db=True)

            # 7. 実行
            summary = await _execute_orchestration(
                orchestrator,
                user_prompt,
                timeout,
                output_format,
                len(orchestrator_settings.teams),
            )

            # 8. 結果出力
            # Note: exec コマンドでは常に DB に保存
            _output_results(summary, output_format)

            # 9. 終了コード判定
            if summary.failed_teams_info:
                if summary.team_results:
                    # 部分成功（成功チームあり + 失敗チームあり）
                    raise typer.Exit(code=1)
                else:
                    # 全チーム失敗
                    raise typer.Exit(code=2)
        except typer.Exit:
            raise
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=2) from e
        finally:
            # Cleanup: Close all HTTP clients
            await close_all_auth_clients()

    asyncio.run(_execute())


def _print_leaderboard_table(summary: ExecutionSummary) -> None:
    """リーダーボードテーブルを表示

    Args:
        summary: 実行サマリー(チーム結果を含む)
    """
    console = Console()
    table = Table(title="🏆 Leaderboard", show_header=True, header_style="bold")

    # カラム定義
    table.add_column("Rank", style="cyan", justify="right", width=6)
    table.add_column("Team", style="magenta", width=20)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Status", width=12)

    # 成功チームをスコア降順でソート
    sorted_results = sorted(summary.team_results, key=lambda r: r.score, reverse=True)

    # 成功チームを追加
    for rank, result in enumerate(sorted_results, 1):
        # スコアは既に0-100スケール
        table.add_row(
            str(rank),
            result.team_name,
            f"{result.score:.2f}",
            "✅ Completed",
        )

    # 失敗チームを追加
    for failed in summary.failed_teams_info:
        table.add_row(
            "—",
            failed.team_name,
            "—",
            "❌ Failed",
        )

    # テーブル表示
    console.print()
    console.print(table)
    console.print()


def _print_text_summary(summary: ExecutionSummary) -> None:
    """テキスト形式でサマリーを表示

    Note: exec コマンドでは常に DuckDB に保存されます。

    Args:
        summary: 実行サマリー
    """
    # 成功チーム結果表示
    for result in summary.team_results:
        typer.echo(f"✅ Team {result.team_id}: {result.team_name} (Round {result.round_number})")
        # スコアは既に0-100スケール
        typer.echo(f"   Score: {result.score:.2f}")
        typer.echo(f"   Exit Reason: {result.exit_reason or 'N/A'}\n")

    # 失敗チーム情報表示
    if summary.failed_teams_info:
        typer.echo("❌ Failed Teams:")
        for failed in summary.failed_teams_info:
            typer.echo(f"   • {failed.team_id}: {failed.team_name}")
            typer.echo(f"     Error: {failed.error_message}\n")

    # 最高スコアチーム表示
    if summary.best_team_id:
        typer.echo("━" * 60)
        typer.echo(f"🏆 Best Result (Team {summary.best_team_id}, Score: {summary.best_score:.2f})")
        typer.echo("━" * 60)

        best_result = next(r for r in summary.team_results if r.team_id == summary.best_team_id)
        typer.echo(f"\n{best_result.submission_content}\n")

    # リーダーボード表示
    _print_leaderboard_table(summary)

    # サマリー表示
    typer.echo("━" * 60)
    typer.echo("📊 Summary")
    typer.echo("━" * 60)
    typer.echo(f"\nTotal Teams:      {summary.total_teams}")
    typer.echo(f"Completed Teams:  {summary.completed_teams}")
    typer.echo(f"Failed Teams:     {summary.failed_teams}")
    typer.echo(f"Execution Time:   {summary.total_execution_time_seconds:.1f}s")
    # exec コマンドでは常に DB に保存
    typer.echo("\n💾 Results saved to DuckDB")
