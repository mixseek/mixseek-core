"""Evaluate command implementation for AI agent output evaluation."""

import asyncio
import json
import sys
from pathlib import Path

import typer

from mixseek.cli.commands.evaluate_helper import display_evaluation_text, evaluate_content
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
from mixseek.utils.env import get_workspace_path


def evaluate(
    user_query: str = typer.Argument(..., help="User query string"),
    submission: str = typer.Argument(..., help="AI agent submission text"),
    workspace: Path | None = WORKSPACE_OPTION,
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Custom evaluator config file (overrides workspace)"
    ),
    verbose: bool = VERBOSE_OPTION,
    output_format: str = typer.Option("structured", "--output-format", "-f", help="Output format: structured, json"),
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
) -> None:
    """Evaluate AI agent submission using LLM-as-a-Judge.

    This command evaluates AI agent outputs using built-in metrics:
    - Clarity/Coherence: How clear and consistent the response is
    - Coverage: How comprehensive the response is
    - Relevance: How relevant the response is to the query

    Configuration is loaded from $MIXSEEK_WORKSPACE/configs/evaluator.toml
    or specified via --evaluate-config option.

    Examples:
        mixseek evaluate "Pythonとは?" "Pythonは言語です"

        mixseek evaluate "質問" "回答" --workspace /path/to/workspace

        mixseek evaluate "質問" "回答" --config evaluate.toml

        mixseek evaluate "質問" "回答" --output-format json --verbose

        mixseek evaluate "質問" "回答" --logfire

        mixseek evaluate "質問" "回答" --logfire-metadata

        mixseek evaluate "質問" "回答" --log-level debug --verbose
    """
    # Logfireフラグの排他的チェック
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        typer.secho(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    # Workspace解決（ログ出力先のため）
    # Article 9準拠: workspace は必須（ログ出力に必要）
    workspace_resolved = get_workspace_path(workspace)

    # 標準logging初期化（Logfireより先に実行）
    logfire_enabled = logfire or logfire_metadata or logfire_http
    setup_logging_from_cli(log_level, no_log_console, no_log_file, logfire_enabled, workspace_resolved, verbose)

    # Logfire初期化
    setup_logfire_from_cli(logfire, logfire_metadata, logfire_http, workspace_resolved, verbose)

    try:
        # 評価を実行（共通ヘルパー関数を使用）
        # Note: cleanup (close_all_auth_clients) は evaluate_content 内の finally で処理される
        result = asyncio.run(
            evaluate_content(
                user_query=user_query,
                submission=submission,
                workspace=workspace,
                evaluate_config=config,
                team_id="standalone-evaluation",
                verbose=verbose,
            )
        )

        # evaluate_content が None を返した場合はエラー（詳細メッセージは既に出力済み）
        if result is None:
            raise typer.Exit(1)

        # 結果を出力
        if output_format == "json":
            print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
        else:
            # Structured format (default) - 共通ヘルパー関数を使用
            display_evaluation_text(result, verbose=verbose)

    except KeyboardInterrupt:
        typer.echo("\n⚠️  Interrupted by user", err=True)
        sys.exit(130)
