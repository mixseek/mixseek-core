"""mixseek exec コマンド実装"""

import asyncio
import logging
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from mixseek.cli.common_options import (
    LOG_FORMAT_OPTION,
    LOG_LEVEL_OPTION,
    LOGFIRE_HTTP_OPTION,
    LOGFIRE_METADATA_OPTION,
    LOGFIRE_OPTION,
    NO_LOG_CONSOLE_OPTION,
    NO_LOG_FILE_OPTION,
    VERBOSE_OPTION,
    WORKSPACE_OPTION,
)
from mixseek.cli.utils import initialize_observability, validate_logfire_flags
from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.config.preflight import PreflightResult, run_preflight_check
from mixseek.core.auth import close_all_auth_clients
from mixseek.orchestrator import Orchestrator
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
DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    help="設定検証のみ実行し、オーケストレーションは実行しない",
)


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
    dry_run: bool = DRY_RUN_OPTION,
    verbose: bool = VERBOSE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
    log_format: str | None = LOG_FORMAT_OPTION,
) -> None:
    """ユーザプロンプトを複数チームで並列実行

    Note: exec コマンドではリーダーボード機能のため、常に DuckDB に保存されます。

    Args:
        user_prompt: ユーザプロンプト
        config: 設定ファイルパス
        timeout: タイムアウト(秒)
        workspace: ワークスペースパス
        output_format: 出力フォーマット
        dry_run: プリフライトチェックのみ実行
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
            # 1. Logfireフラグの排他的チェック
            validate_logfire_flags(logfire, logfire_metadata, logfire_http)

            # 2. ワークスペースパス解決（ConfigurationManager経由）
            # Note: workspace_pathはLogfire初期化にのみ使用（オプショナル機能）
            workspace_path: Path | None = None
            try:
                config_manager = ConfigurationManager(workspace=workspace)
                orchestrator_settings: OrchestratorSettings = config_manager.load_settings(OrchestratorSettings)
                workspace_path = orchestrator_settings.workspace_path
            except Exception:
                # ConfigurationManager失敗時はCLI引数を使用（Logfire用）
                workspace_path = workspace

            # Issue #273 fix: 環境変数に設定して後続コンポーネントに伝搬
            if workspace_path:
                os.environ[WORKSPACE_ENV_VAR] = str(workspace_path)

            # 3. ロギング・Logfire初期化（CLI共通ヘルパー）
            initialize_observability(
                log_level=log_level,
                no_log_console=no_log_console,
                no_log_file=no_log_file,
                logfire=logfire,
                logfire_metadata=logfire_metadata,
                logfire_http=logfire_http,
                verbose=verbose,
                log_format=log_format,
                workspace=workspace_path,
            )

            # 4. config必須チェック（dry-run/通常の両方で必要）
            if config is None:
                typer.echo("Error: --config オプションは必須です", err=True)
                raise typer.Exit(code=2)

            # 5. プリフライトチェック（dry-run/通常で共通、1回のみ実行）
            preflight_result = run_preflight_check(config, workspace)

            # dry-runの場合は常に結果を出力して終了、通常モードはエラー時のみ出力して終了
            if dry_run or not preflight_result.is_valid:
                _output_preflight_result(preflight_result, output_format)
                raise typer.Exit(code=0 if preflight_result.is_valid else 2)

            # 6. プリフライトで読み込み済みの設定を再利用（二重ロード回避）
            if preflight_result.orchestrator_settings is None:
                typer.echo("Error: プリフライト成功にもかかわらずorchestrator_settingsがNoneです", err=True)
                raise typer.Exit(code=2)
            orchestrator_settings = preflight_result.orchestrator_settings

            # 7. Orchestrator初期化
            # Note: exec コマンドではリーダーボード機能のため常に DB 保存
            orchestrator = Orchestrator(settings=orchestrator_settings, save_db=True)

            # 8. 実行
            summary = await _execute_orchestration(
                orchestrator,
                user_prompt,
                timeout,
                output_format,
                len(orchestrator_settings.teams),
            )

            # 9. 結果出力
            # Note: exec コマンドでは常に DB に保存
            _output_results(summary, output_format)

            # 10. 終了コード判定
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


def _output_preflight_result(result: PreflightResult, output_format: str) -> None:
    """プリフライトチェック結果を出力する。

    Args:
        result: プリフライトチェック結果
        output_format: 出力フォーマット(text/json)
    """
    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        status_icons = {"ok": "✅", "error": "❌", "skipped": "⏭️"}

        typer.echo("🔍 Preflight Check Results")
        typer.echo("━" * 60)

        for cat in result.categories:
            typer.echo(f"\n📋 {cat.category}")
            for check in cat.checks:
                icon = status_icons.get(check.status.value, "?")
                typer.echo(f"  {icon} {check.name}: {check.message}")
                if check.source_file:
                    typer.echo(f"     📄 {check.source_file}")

        typer.echo("\n" + "━" * 60)
        if result.is_valid:
            typer.echo("✅ All checks passed")
        else:
            typer.echo(f"❌ Preflight failed (errors: {result.error_count})")


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

    # 部分成功チームIDの特定
    partial_team_ids = summary.partial_team_ids

    # 成功チーム（部分成功含む）をスコア降順でソート
    sorted_results = sorted(summary.team_results, key=lambda r: r.score, reverse=True)

    # 成功チームを追加
    for rank, result in enumerate(sorted_results, 1):
        # スコアは既に0-100スケール
        status = "⚠️ Partial" if result.team_id in partial_team_ids else "✅ Completed"
        table.add_row(
            str(rank),
            result.team_name,
            f"{result.score:.2f}",
            status,
        )

    # 完全失敗チームのみ追加（部分成功チームはリーダーボードに表示済み）
    for failed in summary.failed_teams_info:
        if failed.team_id not in partial_team_ids:
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
    # 部分成功チームIDの特定
    partial_team_ids = summary.partial_team_ids

    # 成功チーム結果表示
    for result in summary.team_results:
        if result.team_id in partial_team_ids:
            typer.echo(f"⚠️  Team {result.team_id}: {result.team_name} (Round {result.round_number}) [Partial]")
        else:
            typer.echo(f"✅ Team {result.team_id}: {result.team_name} (Round {result.round_number})")
        # スコアは既に0-100スケール
        typer.echo(f"   Score: {result.score:.2f}")
        typer.echo(f"   Exit Reason: {result.exit_reason or 'N/A'}\n")

    # 失敗チーム情報表示
    if summary.failed_teams_info:
        typer.echo("❌ Failed Teams:")
        for failed in summary.failed_teams_info:
            if failed.team_id in partial_team_ids:
                typer.echo(f"   • {failed.team_id}: {failed.team_name} [Partial - see leaderboard]")
            else:
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
    if summary.partial_teams > 0:
        typer.echo(f"Partial Teams:    {summary.partial_teams}")
    typer.echo(f"Execution Time:   {summary.total_execution_time_seconds:.1f}s")
    # exec コマンドでは常に DB に保存
    typer.echo("\n💾 Results saved to DuckDB")
