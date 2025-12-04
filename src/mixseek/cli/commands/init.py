"""Init command implementation for workspace initialization."""

import logging
import sys
from pathlib import Path

import typer

from mixseek.cli.common_options import WORKSPACE_OPTION
from mixseek.config.templates import generate_sample_config
from mixseek.exceptions import (
    ParentDirectoryNotFoundError,
    WorkspacePathNotSpecifiedError,
    WorkspacePermissionError,
)
from mixseek.models.result import InitResult
from mixseek.models.workspace import WorkspacePath, WorkspaceStructure
from mixseek.utils.env import get_workspace_path

logger = logging.getLogger(__name__)


def init(
    workspace: Path | None = WORKSPACE_OPTION,
) -> None:
    """
    Initialize MixSeek workspace.

    Creates workspace directory structure with:
    - logs/      : Log files directory
    - configs/   : Configuration files directory
    - templates/ : Template files directory

    Also generates ready-to-use orchestrator and team configuration files.

    Examples:
        mixseek init --workspace /path/to/workspace
        mixseek init -w ./my-workspace
        export MIXSEEK_WORKSPACE=/path/to/workspace && mixseek init
    """
    # Initialize workspace_path_input to None for safe error handling
    workspace_path_input: Path | None = None

    try:
        # Get workspace path with priority: CLI > ENV
        workspace_path_input = get_workspace_path(workspace)

        # Create WorkspacePath with validation
        workspace_path = (
            WorkspacePath.from_cli(str(workspace_path_input))
            if workspace
            else WorkspacePath.from_env(str(workspace_path_input))
        )

        # Create workspace structure
        workspace_structure = WorkspaceStructure.create(workspace_path.resolved_path)

        # Check if workspace exists and prompt for confirmation
        if workspace_structure.exists:
            if not typer.confirm(
                f"Workspace already exists at {workspace_structure.root}. Overwrite?",
                default=False,
            ):
                typer.echo("Workspace initialization aborted.", err=True)
                sys.exit(1)

        # Create directories
        workspace_structure.create_directories()
        created_dirs = [
            workspace_structure.root,
            workspace_structure.logs_dir,
            workspace_structure.configs_dir,
            workspace_structure.configs_dir / "agents",
            workspace_structure.configs_dir / "evaluators",
            workspace_structure.configs_dir / "judgment",
            workspace_structure.templates_dir,
        ]

        # Generate sample configuration
        generate_sample_config(workspace_structure.root)
        created_files = [
            workspace_structure.configs_dir / "search_news.toml",
            workspace_structure.configs_dir / "search_news_multi_perspective.toml",
            workspace_structure.configs_dir / "agents" / "team_general_researcher.toml",
            workspace_structure.configs_dir / "agents" / "team_sns_researcher.toml",
            workspace_structure.configs_dir / "agents" / "team_academic_researcher.toml",
            workspace_structure.configs_dir / "evaluators" / "evaluator_search_news.toml",
            workspace_structure.configs_dir / "judgment" / "judgment_search_news.toml",
        ]

        # Log success
        logger.info(f"Workspace created at: {workspace_structure.root}")

        # Create and print result
        result = InitResult.success_result(
            workspace_path=workspace_structure.root,
            created_dirs=created_dirs,
            created_files=created_files,
        )
        result.print_result()

    except (
        WorkspacePathNotSpecifiedError,
        ParentDirectoryNotFoundError,
        WorkspacePermissionError,
        OSError,
        ValueError,
        PermissionError,
    ) as e:
        handle_error(e, workspace_path_input or Path("."))
    except KeyboardInterrupt:
        typer.echo("\nInitialization cancelled by user.", err=True)
        sys.exit(130)  # Standard exit code for SIGINT


def handle_error(error: Exception, workspace_path: Path) -> None:
    """
    Handle errors with user-friendly messages.

    Args:
        error: The exception that occurred
        workspace_path: The workspace path that was being processed
    """
    result = InitResult.error_result(workspace_path=workspace_path, error=str(error))

    # Add solution hints based on error type
    if isinstance(error, WorkspacePermissionError):
        typer.echo(
            f"Error: {error}\nSolution: Check directory permissions or choose a different path.",
            err=True,
        )
    elif isinstance(error, ParentDirectoryNotFoundError):
        typer.echo(
            f"Error: {error}\nSolution: Create the parent directory first or choose an existing location.",
            err=True,
        )
    elif isinstance(error, WorkspacePathNotSpecifiedError):
        typer.echo(
            f"Error: {error}",
            err=True,
        )
    else:
        result.print_result()

    logger.error(f"Initialization failed: {error}")
    sys.exit(1)
