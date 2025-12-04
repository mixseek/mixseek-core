"""Evaluation integration helper for CLI commands.

This module provides helper functions to integrate the Evaluator
with team commands for Leader Agent evaluation.
"""

from pathlib import Path

import typer

from mixseek.config.manager import ConfigurationManager
from mixseek.core.auth import close_all_auth_clients
from mixseek.evaluator import Evaluator
from mixseek.models.evaluation_config import EvaluationConfig  # noqa: F401
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_result import EvaluationResult
from mixseek.utils.env import get_workspace_for_config

# Rebuild EvaluationRequest model after EvaluationConfig is imported
# This is required because EvaluationRequest uses TYPE_CHECKING for forward reference
EvaluationRequest.model_rebuild()

# Constants for display formatting
COMMENT_TRUNCATE_LENGTH = 500


def _create_evaluator(
    workspace: Path | None = None,
    evaluate_config: Path | None = None,
    verbose: bool = False,
) -> Evaluator:
    """Create and initialize Evaluator with config loading.

    .. note:: FR-046, FR-050準拠
        ConfigurationManager.get_evaluator_settings() を使用し、
        フォールバックロジックを共通化しています。

    Args:
        workspace: Workspace directory path for default evaluator config
        evaluate_config: Optional path to custom evaluator config file (overrides workspace)
        verbose: Verbose output flag

    Returns:
        Initialized Evaluator instance

    Raises:
        FileNotFoundError: If custom config file is not found
        ValidationError: If config file is invalid
    """
    workspace_path = get_workspace_for_config(workspace)
    manager = ConfigurationManager(workspace=workspace_path)

    if verbose:
        if evaluate_config:
            typer.echo(f"Loading custom config: {evaluate_config}", err=True)
        else:
            typer.echo(f"Using default config: {workspace_path}/configs/evaluator.toml", err=True)

    # FR-050準拠: get_evaluator_settings() でフォールバックロジックを共通化
    settings = manager.get_evaluator_settings(evaluate_config)
    prompt_builder_settings = manager.get_prompt_builder_settings()

    # FR-046準拠: EvaluatorSettings と PromptBuilderSettings を渡して初期化
    return Evaluator(settings=settings, prompt_builder_settings=prompt_builder_settings)


async def evaluate_content(
    user_query: str,
    submission: str,
    workspace: Path | None = None,
    evaluate_config: Path | None = None,
    team_id: str | None = None,
    verbose: bool = False,
) -> EvaluationResult | None:
    """Evaluate content using the Evaluator.

    Args:
        user_query: User's original query/prompt
        submission: AI agent's response content to evaluate
        workspace: Workspace directory path for default evaluator config (default: $MIXSEEK_WORKSPACE or cwd)
        evaluate_config: Optional path to custom evaluator config file (overrides workspace)
        team_id: Optional team ID for tracking
        verbose: Verbose output flag

    Returns:
        EvaluationResult object, or None if evaluation failed

    Example:
        >>> result = evaluate_content(
        ...     user_query="Pythonとは？",
        ...     submission="Pythonはプログラミング言語です。",
        ...     verbose=True
        ... )
        >>> if result:
        ...     print(f"Overall score: {result.overall_score}")
    """
    try:
        if verbose:
            typer.echo("\n=== Evaluating Response ===", err=True)
            typer.echo(f"Query: {user_query}", err=True)
            typer.echo(f"Submission: {submission}", err=True)

        # Evaluator の初期化（共通ヘルパー関数を使用）
        evaluator = _create_evaluator(workspace, evaluate_config, verbose)

        # 評価リクエストを作成
        # team_id が None の場合はデフォルト値を使用
        request = EvaluationRequest(
            user_query=user_query,
            submission=submission,
            team_id=team_id if team_id else "standalone-evaluation",
            config=None,  # カスタム設定は Evaluator 側で既に適用済み
        )

        # 評価を実行
        result = await evaluator.evaluate(request)

        if verbose:
            typer.echo(f"✓ Evaluation completed: {result.overall_score}", err=True)

        return result

    except FileNotFoundError as e:
        typer.secho(f"⚠️  Evaluation config file not found: {e}", fg=typer.colors.YELLOW, err=True)
        if verbose:
            typer.echo("Hint: Use --evaluate-config to specify a custom config file", err=True)
        return None
    except Exception as e:
        typer.secho(f"⚠️  Evaluation failed: {e}", fg=typer.colors.YELLOW, err=True)
        if verbose:
            import traceback

            typer.echo(traceback.format_exc(), err=True)
        return None
    finally:
        # Cleanup: Close all HTTP clients in the same event loop
        await close_all_auth_clients()


def display_evaluation_text(result: EvaluationResult, verbose: bool = False) -> None:
    """Display evaluation results in text format.

    Args:
        result: EvaluationResult object to display
        verbose: If True, show full comments; if False, truncate long comments

    Example:
        >>> result = EvaluationResult(overall_score=85.5, metrics=[...])
        >>> display_evaluation_text(result)
        === Evaluation Results ===
        Overall Score: 85.5
        ...
    """
    typer.secho("\n=== Evaluation Results ===", bold=True, fg=typer.colors.CYAN)
    typer.secho(f"Overall Score: {result.overall_score}", bold=True, fg=typer.colors.CYAN)
    typer.secho("Metric Scores:", bold=True, fg=typer.colors.CYAN)
    for metric in result.metrics:
        # Display metric name and score with bold and color for emphasis
        typer.secho(f"{metric.metric_name}: {metric.score}", bold=True, fg=typer.colors.GREEN)
        if metric.evaluator_comment:
            comment = metric.evaluator_comment
            # Truncate long comments unless verbose mode
            if not verbose and len(comment) > COMMENT_TRUNCATE_LENGTH:
                comment = comment[: COMMENT_TRUNCATE_LENGTH - 3] + "..."
            typer.secho("Comment:", fg=typer.colors.GREEN)
            typer.echo(comment)


def display_evaluation_json(result: EvaluationResult) -> dict[str, object]:
    """Convert evaluation results to JSON-serializable dict.

    Args:
        result: EvaluationResult object to convert

    Returns:
        Dictionary representation of evaluation results

    Example:
        >>> result = EvaluationResult(overall_score=85.5, metrics=[...])
        >>> json_data = display_evaluation_json(result)
        >>> print(json_data["overall_score"])
        85.5
    """
    return result.model_dump(mode="json")
