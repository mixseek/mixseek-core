"""Common CLI options shared across commands.

This module defines reusable Typer options to ensure consistency across all CLI commands
and comply with Constitution Article 10 (DRY Principle).

Usage:
    from mixseek.cli.common_options import WORKSPACE_OPTION, VERBOSE_OPTION

    def my_command(
        workspace: Path | None = WORKSPACE_OPTION,
        verbose: bool = VERBOSE_OPTION,
    ):
        ...
"""

import typer

# Workspace option - used by: init, team, evaluate, exec, config, ui
WORKSPACE_OPTION = typer.Option(
    None,
    "--workspace",
    "-w",
    help="Workspace path (uses MIXSEEK_WORKSPACE env var if not specified)",
)

# Verbose option - used by: team, evaluate, exec, member
VERBOSE_OPTION = typer.Option(
    False,
    "--verbose",
    "-v",
    help="Verbose output",
)

# Logfire options - used by: team, exec, ui
LOGFIRE_OPTION = typer.Option(
    False,
    "--logfire",
    help="Enable Logfire observability (full mode)",
)

LOGFIRE_METADATA_OPTION = typer.Option(
    False,
    "--logfire-metadata",
    help="Enable Logfire (metadata only)",
)

LOGFIRE_HTTP_OPTION = typer.Option(
    False,
    "--logfire-http",
    help="Enable Logfire (full + HTTP capture)",
)

# Logging options - used by: team, exec, ui
LOG_LEVEL_OPTION = typer.Option(
    "info",
    "--log-level",
    help="Global log level (debug/info/warning/error/critical)",
)

NO_LOG_CONSOLE_OPTION = typer.Option(
    False,
    "--no-log-console",
    help="Disable console log output",
)

NO_LOG_FILE_OPTION = typer.Option(
    False,
    "--no-log-file",
    help="Disable file log output",
)
