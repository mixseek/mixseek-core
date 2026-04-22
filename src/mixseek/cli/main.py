"""Main CLI application entry point for MixSeek."""

# 他の import より前に早期 stderr フックを設置する。
# MIXSEEK_LOG_FORMAT=json のとき warnings.showwarning を JSON 版に差し替え、
# setup_logging() 前 (import 段階) に発火する warning もスキーマ化する。
# 他の mixseek.* を import する前に実行する必要があるため、最上段に配置。
from mixseek.cli._early_init import install_early_stderr_hooks

install_early_stderr_hooks()

import typer  # noqa: E402

from mixseek import __version__  # noqa: E402
from mixseek.cli.commands import config as config_module  # noqa: E402
from mixseek.cli.commands import evaluate as evaluate_module  # noqa: E402
from mixseek.cli.commands import exec as exec_module  # noqa: E402
from mixseek.cli.commands import init as init_module  # noqa: E402
from mixseek.cli.commands import member as member_module  # noqa: E402
from mixseek.cli.commands import team as team_module  # noqa: E402
from mixseek.cli.commands import ui as ui_module  # noqa: E402

app = typer.Typer(
    name="mixseek",
    help="MixSeek: Multi-agent framework CLI",
    add_completion=False,
)

# Register commands
app.command(name="init")(init_module.init)
app.command(name="member")(member_module.member)
app.command(name="team")(team_module.team)
app.command(name="evaluate")(evaluate_module.evaluate)
app.command(name="exec")(exec_module.exec_command)
app.command(name="ui")(ui_module.ui)

# Register config subcommands
app.add_typer(config_module.app, name="config")


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        typer.echo(f"mixseek version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """
    MixSeek CLI - Multi-agent framework with workspace initialization.

    Available commands:
      init             Initialize MixSeek workspace
      member           Execute Member Agent (development/testing only)
      team             Execute team of Member Agents (development/testing only)
      evaluate         Evaluate AI agent submission using LLM-as-a-Judge
      exec             Execute user prompt with multiple teams in parallel
      ui               Launch Streamlit web interface
      config           Manage configuration (coming soon)

    Use "mixseek [command] --help" for more information about a command.
    """
    pass


if __name__ == "__main__":
    app()
