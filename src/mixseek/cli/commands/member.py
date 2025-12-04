"""Member Agent CLI command.

This module provides the `mixseek member` command for development and testing
of Member Agents. This command is for development purposes only.
"""

import asyncio
import time
from pathlib import Path

import typer

from mixseek.agents.member.factory import MemberAgentFactory
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
from mixseek.cli.formatters import ResultFormatter
from mixseek.cli.utils import (
    mutually_exclusive_group,
    setup_logfire_from_cli,
    setup_logging_from_cli,
    show_development_warning,
)
from mixseek.config.bundled_member_agents import BundledMemberAgentError, BundledMemberAgentLoader
from mixseek.config.manager import ConfigurationManager
from mixseek.config.member_agent_loader import member_settings_to_config
from mixseek.core.auth import close_all_auth_clients
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult
from mixseek.utils.env import get_workspace_path


def display_result(result: MemberAgentResult, execution_time_ms: int, output_format: str, verbose: bool) -> None:
    """Display agent execution result in specified format using the new formatter."""
    try:
        # Special handling for CSV format (expects lists)
        if output_format == "csv":
            ResultFormatter.format_csv([result], [execution_time_ms])
        else:
            formatter = ResultFormatter.get_formatter(output_format)
            formatter(result, execution_time_ms, verbose)
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
        # Fallback to structured format
        ResultFormatter.format_structured(result, execution_time_ms, verbose)


async def execute_agent_from_config(
    config: MemberAgentConfig, prompt: str, verbose: bool, timeout: int
) -> MemberAgentResult:
    """Execute agent from MemberAgentConfig object.

    Args:
        config: Agent configuration
        prompt: User prompt
        verbose: Verbose output flag
        timeout: Execution timeout in seconds

    Returns:
        Execution result

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
    """
    try:
        if verbose:
            typer.echo(f"Loaded configuration: {config.name} ({config.type})", err=True)
            typer.echo(f"Model: {config.model}", err=True)
            typer.echo(f"Timeout: {timeout}s", err=True)

        # Create and execute agent
        agent = MemberAgentFactory.create_agent(config)
        await agent.initialize()

        # Execute with timeout
        result = await asyncio.wait_for(agent.execute(prompt), timeout=timeout)
        return result

    except TimeoutError:
        from mixseek.models.member_agent import ResultStatus

        return MemberAgentResult(
            status=ResultStatus.ERROR,
            content="",
            agent_name=config.name,
            agent_type=config.type,
            error_message=f"Execution timeout after {timeout}s",
        )
    except Exception as e:
        from mixseek.models.member_agent import ResultStatus

        return MemberAgentResult(
            status=ResultStatus.ERROR,
            content="",
            agent_name=config.name,
            agent_type=config.type,
            error_message=f"Execution failed: {e}",
        )
    finally:
        # Cleanup: Close all HTTP clients in the same event loop
        await close_all_auth_clients()


# Create mutual exclusivity callback
_exclusivity = mutually_exclusive_group(group_size=1)


def member(
    prompt: str = typer.Argument(..., help="Prompt to send to agent"),
    config: Path | None = typer.Option(None, "--config", "-c", help="TOML config file path", callback=_exclusivity),
    agent: str | None = typer.Option(
        None, "--agent", help="Bundled agent name (plain, web-search, code-exec)", callback=_exclusivity
    ),
    workspace: Path | None = WORKSPACE_OPTION,
    verbose: bool = VERBOSE_OPTION,
    output_format: str = typer.Option(
        "structured", "--output-format", "-f", help="Output format: structured, json, text, csv"
    ),
    timeout: int | None = typer.Option(None, "--timeout", help="Execution timeout in seconds (overrides config)"),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Override max tokens for model"),
    temperature: float | None = typer.Option(None, "--temperature", help="Override temperature (0.0-1.0)"),
    log_level: str = LOG_LEVEL_OPTION,
    no_log_console: bool = NO_LOG_CONSOLE_OPTION,
    no_log_file: bool = NO_LOG_FILE_OPTION,
    logfire: bool = LOGFIRE_OPTION,
    logfire_metadata: bool = LOGFIRE_METADATA_OPTION,
    logfire_http: bool = LOGFIRE_HTTP_OPTION,
) -> None:
    """Execute Member Agent (development/testing only).

    Examples:
        mixseek member "質問" --config custom.toml

        mixseek member "質問" --agent plain

        mixseek member "質問" --agent plain --max-tokens 4096 --temperature 0.7

        mixseek member "質問" --config custom.toml --workspace /path/to/workspace

        mixseek member "質問" --config relative.toml --workspace /path/to/workspace

        mixseek member "質問" --agent plain --logfire

        mixseek member "質問" --agent plain --logfire-metadata

        mixseek member "質問" --agent plain --log-level debug --verbose
    """
    # Logfireフラグの排他的チェック
    logfire_flags_count = sum([logfire, logfire_metadata, logfire_http])
    if logfire_flags_count > 1:
        typer.secho(
            "ERROR: Only one of --logfire, --logfire-metadata, or --logfire-http can be specified.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Workspace解決（ログ出力先とconfig相対パス解決のため）
    # Article 9準拠: workspace は必須（ログ出力に必要）
    workspace_resolved = get_workspace_path(workspace)

    # 標準logging初期化（Logfireより先に実行）
    logfire_enabled = logfire or logfire_metadata or logfire_http
    setup_logging_from_cli(log_level, no_log_console, no_log_file, logfire_enabled, workspace_resolved, verbose)

    # Logfire初期化
    setup_logfire_from_cli(logfire, logfire_metadata, logfire_http, workspace_resolved, verbose)

    show_development_warning()

    # Validate at least one option is provided
    if not config and not agent:
        typer.echo("Error: Either --config or --agent must be specified", err=True)
        raise typer.Exit(1)

    # Execute agent
    try:
        start_time = time.time()

        # Load configuration based on option
        # Load configuration: unified flow for both --agent and --config (Article 10 DRY)
        try:
            if agent:
                # --agent option: Get bundled member agent path
                loader = BundledMemberAgentLoader()
                config_path = loader.get_agent_path(agent)  # type: ignore[arg-type]
            else:
                # --config option: use provided path
                # Type check: config is Path at this point (validated above)
                assert config is not None
                config_path = config

            # Unified loading path for both --agent and --config (Article 10 DRY)
            # Use ConfigurationManager for consistent path resolution (same as team/exec commands)
            config_manager = ConfigurationManager(workspace=workspace_resolved)
            member_settings = config_manager.load_member_settings(config_path)

            # Convert MemberAgentSettings to MemberAgentConfig
            # Note: agent_data (2nd argument) is optional for overrides - not needed here
            # Pass workspace for bundled agent system_instruction loading
            loaded_config = member_settings_to_config(member_settings, workspace=workspace_resolved)

            # Override config with CLI options if provided
            if max_tokens is not None:
                loaded_config = loaded_config.model_copy(update={"max_tokens": max_tokens})
            if temperature is not None:
                loaded_config = loaded_config.model_copy(update={"temperature": temperature})

            # Determine effective timeout: CLI arg > config.timeout_seconds > default (30s)
            effective_timeout = timeout if timeout is not None else (loaded_config.timeout_seconds or 30)
            result = asyncio.run(execute_agent_from_config(loaded_config, prompt, verbose, effective_timeout))
        except BundledMemberAgentError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

        execution_time_ms = int((time.time() - start_time) * 1000)

        display_result(result, execution_time_ms, output_format, verbose)

        # Exit with appropriate code
        if result.status == "error":
            raise typer.Exit(1)

    except typer.Exit:
        # Re-raise typer.Exit to preserve intended exit code
        raise
    except KeyboardInterrupt:
        typer.echo("\n⚠️  Interrupted by user", err=True)
        raise typer.Exit(130)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)
