"""Team CLI command - Agent Delegation方式

開発・テスト用チーム実行コマンド。
Leader AgentがAgent Delegationパターンで動的にMember Agentを選択・実行。

⚠️ WARNING: This command is for development/testing only.
For production use, use Orchestration Layer instead.

重要な設計変更（Clarifications 2025-10-23）:
- 全Member Agent並列実行 → Agent Delegation（動的選択）
- aggregated_content削除 → 構造化データのみ記録
- Leader Agentが前ラウンドを意識しない独立設計

References:
    - Spec: specs/008-leader/spec.md (FR-021-028)
    - Contracts: specs/008-leader/contracts/leader-agent-api.md (Section 5)
    - Quickstart: specs/008-leader/quickstart.md
"""

import asyncio
import json
import os
import traceback
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import typer
from pydantic_core import to_jsonable_python

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import team_settings_to_team_config
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmissionsRecord
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.cli.commands.evaluate_helper import (
    display_evaluation_json,
    display_evaluation_text,
    evaluate_content,
)
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
from mixseek.config.member_agent_loader import member_settings_to_config
from mixseek.core.auth import close_all_auth_clients
from mixseek.storage.aggregation_store import AggregationStore


def team(
    prompt: str = typer.Argument(..., help="User prompt for the team"),
    config: Path = typer.Option(..., "--config", "-c", help="Team configuration TOML file"),
    output_format: str = typer.Option("text", "--output-format", "-f", help="Output format: json or text"),
    save_db: bool = typer.Option(False, "--save-db", help="Save results to DuckDB (for debugging)"),
    evaluate: bool = typer.Option(False, "--evaluate", help="Evaluate leader agent response"),
    workspace: Path | None = WORKSPACE_OPTION,
    evaluate_config: Path | None = typer.Option(
        None, "--evaluate-config", "-e", help="Custom evaluator config file (overrides workspace)"
    ),
    verbose: bool = VERBOSE_OPTION,
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
) -> None:
    """Execute team of Member Agents (development/testing only)

    ⚠️ WARNING: This command is for development and testing purposes only.
    For production use, use the Orchestration Layer instead.

    Examples:
        mixseek team "Analyze data" --config team.toml

        mixseek team "Question" --config team.toml --output-format json

        mixseek team "Question" --config team.toml --save-db

        mixseek team "Question" --config team.toml --evaluate

        mixseek team "Question" --config team.toml --evaluate --evaluate-config evaluate.toml

        mixseek team "Question" --config team.toml --logfire

        mixseek team "Question" --config team.toml --logfire-metadata

        mixseek team "Question" --config team.toml --logfire-http
    """
    # Logfire初期化（早期実行）
    # 優先順位: CLIフラグ > 環境変数 > TOML設定

    # 排他的チェック（複数のlogfireフラグは指定できない）
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        typer.secho(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # T096: CLIフラグから環境変数への書き込みを削除（Article 9準拠）
    # CLIフラグはLogfireConfig初期化時に直接使用

    # 設定読み込み（CLIフラグ、環境変数、TOML設定のいずれかで有効化可能）
    # Phase 12 (T084): ConfigurationManager経由でワークスペース取得（Article 9準拠）
    workspace_resolved = workspace
    if not workspace_resolved:
        try:
            config_manager = ConfigurationManager(workspace=None)
            orchestrator_settings: OrchestratorSettings = config_manager.load_settings(OrchestratorSettings)
            workspace_resolved = orchestrator_settings.workspace_path
        except Exception as e:
            # Article 9準拠: 明示的エラーメッセージ（暗黙的フォールバック削除）
            typer.secho(
                f"ERROR: Failed to resolve workspace path: {e}",
                fg=typer.colors.RED,
                err=True,
            )
            typer.secho(
                "Please specify workspace via --workspace option or MIXSEEK_WORKSPACE environment variable",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(code=1)

    # Issue #273 fix: 環境変数に設定して後続コンポーネントに伝搬
    if workspace_resolved:
        os.environ[WORKSPACE_ENV_VAR] = str(workspace_resolved)

    # 標準logging初期化（Logfireより先に実行）
    logfire_enabled = logfire or logfire_metadata or logfire_http
    setup_logging_from_cli(log_level, no_log_console, no_log_file, logfire_enabled, workspace_resolved, verbose)

    # Logfire初期化（共通ロジック）
    setup_logfire_from_cli(logfire, logfire_metadata, logfire_http, workspace_resolved, verbose)

    # FR-022: 開発・テスト専用警告表示
    typer.secho(
        "⚠️  Development/Testing only - Not for production use",
        fg=typer.colors.YELLOW,
        err=True,
    )
    typer.echo("", err=True)

    try:
        asyncio.run(
            _execute_team_command(
                prompt=prompt,
                config=config,
                output_format=output_format,
                save_db=save_db,
                evaluate=evaluate,
                workspace=workspace_resolved,  # T084 fix: Use resolved workspace
                evaluate_config=evaluate_config,
                verbose=verbose,
            )
        )
    except typer.Exit:
        # typer.Exitは再raiseして、元のexit codeを保持
        raise
    except Exception as e:
        typer.secho(f"ERROR: {e}", fg=typer.colors.RED, err=True)
        if verbose:
            typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(code=1)


async def _execute_team_command(
    prompt: str,
    config: Path,
    output_format: str,
    save_db: bool,
    evaluate: bool,
    workspace: Path | None,
    evaluate_config: Path | None,
    verbose: bool,
) -> None:
    """チーム実行ロジック（イベントループ内で実行）"""
    # Article 10 (DRY): ファイル存在チェックはTeamTomlSource内で実行されるため、
    # ここでの重複チェックは削除（相対パス解決前のチェックは不正確）
    # T088 fix: Use ConfigurationManager to load TeamSettings (Article 9 compliant)
    config_manager = ConfigurationManager(workspace=workspace)
    team_settings = config_manager.load_team_settings(config)

    if verbose:
        typer.echo(f"Team: {team_settings.team_name} ({team_settings.team_id})", err=True)
        typer.echo(f"Members: {len(team_settings.members)} agents", err=True)

    member_agents: dict[str, BaseMemberAgent] = {}

    # T088 fix: Use member_settings_to_config() for consistent MemberAgentConfig generation
    for member_settings in team_settings.members:
        # member_settings_to_config()を使用（詳細設定を保持）
        member_agent_config = member_settings_to_config(member_settings, agent_data=None, workspace=workspace)

        member_agent_instance = MemberAgentFactory.create_agent(member_agent_config)
        member_agents[member_settings.agent_name] = member_agent_instance

    # Leader Agent作成のためにTeamConfigに変換（後方互換性）
    team_config = team_settings_to_team_config(team_settings)
    leader_agent = create_leader_agent(team_config, member_agents)

    deps = TeamDependencies(
        team_id=team_config.team_id,
        team_name=team_config.team_name,
        round_number=1,
    )

    if verbose:
        typer.echo("\n=== Executing Leader Agent (Agent Delegation) ===", err=True)

    result = await leader_agent.run(prompt, deps=deps)

    # Generate execution_id for this run (Phase 4: execution_id integration)
    execution_id = str(uuid4())

    record = MemberSubmissionsRecord(
        execution_id=execution_id,
        team_id=deps.team_id,
        team_name=deps.team_name,
        round_number=deps.round_number,
        submissions=deps.submissions,
    )

    # 評価の実行（--evaluate オプションが指定されている場合）
    evaluation_result = None
    if evaluate:
        evaluation_result = await evaluate_content(
            user_query=prompt,
            submission=result.output,  # Leader Agentの最終応答
            workspace=workspace,
            evaluate_config=evaluate_config,
            team_id=deps.team_id,  # チーム設定から自動取得
            verbose=verbose,
        )

    if output_format == "json":
        # FR-023: Integrate Leader and Member Agent message histories
        leader_messages_json = result.all_messages_json()

        # FR-023 & Clarifications Session 2025-10-30:
        # "Leader AgentとMember AgentのMessage Historyを統合した完全な対話履歴を
        # 単一のmessage_historyフィールドに含める"
        #
        # Structure preserves causality (which Leader tool call triggered which Member Agent)
        # as required by FR-034
        message_history = {
            "leader_agent": json.loads(leader_messages_json),
            "member_agents": {
                sub.agent_name: to_jsonable_python(sub.all_messages) if sub.all_messages else []
                for sub in record.submissions
            },
        }

        output_data = {
            "team_id": record.team_id,
            "team_name": record.team_name,
            "round_number": record.round_number,
            "status": "success",
            "total_count": record.total_count,
            "success_count": record.success_count,
            "failure_count": record.failure_count,
            "submissions": [s.model_dump(mode="json") for s in record.submissions],
            "total_usage": asdict(record.total_usage),
            "message_history": message_history,  # FR-023: Integrated Leader + Member Agent message history
        }

        # 評価結果を追加（--evaluate オプションが指定されている場合）
        if evaluation_result:
            output_data["evaluation"] = display_evaluation_json(evaluation_result)

        typer.echo(json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        typer.echo("\n=== Leader Agent Execution ===")
        typer.echo(f"Team: {record.team_name} ({record.team_id})")
        typer.echo(f"Round: {record.round_number}")
        typer.echo(f"\nSelected Member Agents: {record.success_count}/{record.total_count}")

        for sub in record.successful_submissions:
            typer.echo(
                f"✓ {sub.agent_name} (SUCCESS) - "
                f"{sub.usage.input_tokens} input, {sub.usage.output_tokens} output tokens"
            )

        if record.failed_submissions:
            typer.echo(f"\nFailed Agents: {record.failure_count}")
            for sub in record.failed_submissions:
                typer.echo(f"✗ {sub.agent_name} (ERROR): {sub.error_message}")

        typer.echo(
            f"\nTotal Usage: {record.total_usage.input_tokens} input, "
            f"{record.total_usage.output_tokens} output tokens, "
            f"{record.total_usage.requests} requests"
        )

        typer.echo("\n=== Leader Agent Final Response ===")
        typer.echo(result.output)

        if record.successful_submissions:
            typer.echo("\n=== Member Agent Responses (Details) ===")
            for sub in record.successful_submissions:
                typer.echo(f"\n## {sub.agent_name}:")
                typer.echo(sub.content[:200] + "..." if len(sub.content) > 200 else sub.content)

        # 評価結果を表示（--evaluate オプションが指定されている場合）
        if evaluation_result:
            display_evaluation_text(evaluation_result, verbose=verbose)

    if save_db:
        if verbose:
            typer.echo("\nSaving to database...", err=True)

        store = AggregationStore(workspace=workspace)
        messages = result.all_messages()
        await store.save_aggregation(execution_id, record, messages)

        if verbose:
            typer.echo(
                f"✓ Saved to database: execution_id={execution_id}, "
                f"team_id={team_config.team_id}, round={record.round_number}",
                err=True,
            )

    # Member Agent 0件の場合は正常終了（FR-033準拠）
    if record.total_count > 0 and record.failure_count == record.total_count:
        typer.secho(
            "ERROR: All member agents failed. No successful submissions.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    # Cleanup: Close all HTTP clients
    await close_all_auth_clients()
