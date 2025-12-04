"""Configuration management CLI commands.

Provides commands for viewing and managing configuration settings:
- `mixseek config show` - Display current configuration
- `mixseek config list` - List all available configuration items
- `mixseek config init` - Generate TOML templates (Phase 10)

Article 9 Compliance:
- Configuration values are explicitly sourced from ConfigurationManager
- No implicit defaults or assumptions
- Proper error messages and guidance
- Phase 12: Environment management via ConfigurationManager
"""

from pathlib import Path

import typer

from mixseek.cli.common_options import WORKSPACE_OPTION
from mixseek.config import ConfigurationManager
from mixseek.config.views import ConfigViewService

app = typer.Typer(help="Manage configuration settings")

# Typer options - 関数外で定義してB008警告を回避
CONFIG_OPTION = typer.Option(
    None,
    "--config",
    "-c",
    help="オーケストレータ設定TOMLファイルパス",
)


@app.command(name="show")
def config_show(
    key: str | None = typer.Argument(
        None,
        help="Specific configuration key to show (optional)",
    ),
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="オーケストレータ設定TOMLファイルパス(必須)",
    ),
    workspace: Path | None = WORKSPACE_OPTION,
    output_format: str = typer.Option(
        "text",
        "--output-format",
        "-f",
        help="出力フォーマット(text/json)",
    ),
    environment: str | None = typer.Option(
        None,
        "--environment",
        "-e",
        help="Environment: 'dev', 'staging', or 'prod' (defaults to MIXSEEK_ENVIRONMENT env var, or 'dev')",
    ),
) -> None:
    """Display current configuration settings in hierarchical format.

    This command requires --config option and either --workspace option or
    MIXSEEK_WORKSPACE environment variable to display the actual configuration
    values loaded from the specified orchestrator file.

    The output shows configuration in a hierarchical structure:
    orchestrator → team → member, with file paths and indentation.

    Examples:

        # Show all settings (hierarchical text format)
        mixseek config show --config orchestrator.toml --workspace /path/to/workspace

        # Show with MIXSEEK_WORKSPACE env var
        export MIXSEEK_WORKSPACE=/path/to/workspace
        mixseek config show --config orchestrator.toml

        # Show specific setting
        mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace

        # Show in JSON format (for programmatic use)
        mixseek config show --config orchestrator.toml --workspace /path/to/workspace --output-format json

        # Show for specific environment
        mixseek config show --config orchestrator.toml --workspace /path/to/workspace --environment prod
    """
    try:
        # Validate output format
        if output_format not in ["text", "json"]:
            typer.echo(
                f"Error: Invalid format '{output_format}'. Must be 'text' or 'json'.",
                err=True,
            )
            raise typer.Exit(code=1)

        from mixseek.config.recursive_loader import RecursiveConfigLoader
        from mixseek.config.validation import validate_orchestrator_toml
        from mixseek.utils.env import get_workspace_path

        # Resolve workspace: CLI option > MIXSEEK_WORKSPACE env var
        try:
            resolved_workspace = get_workspace_path(workspace)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)

        # Resolve config to absolute path
        # If relative, resolve against workspace
        if not config.is_absolute():
            config_abs = (resolved_workspace / config).resolve()
        else:
            config_abs = config

        # Validate orchestrator TOML
        try:
            validate_orchestrator_toml(config_abs)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)

        # Recursive config loading
        loader = RecursiveConfigLoader(workspace=resolved_workspace)
        try:
            config_data = loader.load_orchestrator_with_references(config_abs)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"Error loading configuration: {e}", err=True)
            raise typer.Exit(code=1)

        # Determine environment
        resolved_env: str = environment or "dev"

        # Initialize ConfigurationManager with config file
        manager = ConfigurationManager(
            workspace=resolved_workspace,
            environment=resolved_env,
            config_file=config_abs,
        )

        # Initialize view service with config_data (for evaluator/judgment/prompt_builder)
        service = ConfigViewService(manager, config_data)

        # Handle specific key lookup
        if key:
            setting = service.get_setting(key)
            if setting is None:
                typer.echo(
                    f"Error: Configuration key '{key}' not found.",
                    err=True,
                )
                available_keys = ", ".join(sorted(service.get_all_settings().keys()))
                typer.echo(f"\nAvailable keys:\n{available_keys}", err=True)
                raise typer.Exit(code=1)

            # Format based on output_format
            if output_format == "json":
                output = service.format_single_json(setting)
            else:
                output = service.format_single(setting)
            typer.echo(output)
            return

        # Format and display based on output format
        if output_format == "text":
            # Hierarchical text format (default)
            output = service.format_hierarchical(config_data)
            typer.echo(output)
        elif output_format == "json":
            # JSON format
            output = service.format_hierarchical_json(config_data)
            typer.echo(output)

    except Exception as e:
        error_msg = str(e)
        typer.echo(f"Error: {error_msg}", err=True)
        raise typer.Exit(code=1)


@app.command(name="list")
def config_list(
    output_format: str = typer.Option(
        "table",
        "--output-format",
        "-f",
        help="Output format: 'table', 'text', or 'json'",
    ),
) -> None:
    """List all available configuration items with defaults and descriptions.

    This command displays schema information (available settings, defaults, types, descriptions)
    and does not require workspace or config file specification.

    Examples:

        # Show all configuration items (table format)
        mixseek config list

        # Show in text format (more verbose)
        mixseek config list --output-format text

        # Show in JSON format (for programmatic use)
        mixseek config list --output-format json
    """
    try:
        # Validate format option
        if output_format not in ["table", "text", "json"]:
            typer.echo(
                f"Error: Invalid format '{output_format}'. Must be 'table', 'text', or 'json'.",
                err=True,
            )
            raise typer.Exit(code=1)

        # Initialize ConfigurationManager (no workspace required for schema info)
        manager = ConfigurationManager()

        # Initialize view service
        service = ConfigViewService(manager)

        # Format and display
        if output_format == "text":
            output = service.format_list()
        elif output_format == "json":
            # JSON format - show schema information only
            settings = service.get_all_settings()
            output = service.format_schema_json(settings)
        else:
            # Table format (default) - show schema information only
            settings = service.get_all_settings()
            output = service.format_schema_table(settings)

        if output:
            typer.echo(output)
        else:
            typer.echo("No configuration settings found.")

    except Exception as e:
        error_msg = str(e)
        typer.echo(f"Error: {error_msg}", err=True)
        raise typer.Exit(code=1)


@app.command(name="init")
def config_init(
    component: str | None = typer.Option(
        None,
        "--component",
        "-c",
        help=(
            "Component: 'orchestrator', 'team', 'evaluator', 'judgment', 'prompt_builder', etc. "
            "(default: all components in config.toml)"
        ),
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        "-o",
        help="Output file path (absolute or relative to workspace). Default: workspace/configs/<component>.toml",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing template file",
    ),
    workspace: Path | None = WORKSPACE_OPTION,
) -> None:
    """Generate TOML configuration template files.

    Creates template TOML files with all configuration options, descriptions,
    and defaults. Useful for initializing new configurations.

    Examples:

        # Generate with default path (workspace/configs/orchestrator.toml)
        mixseek config init --component orchestrator --workspace /path/to/workspace

        # Generate with custom relative path (workspace/my-configs/orchestrator.toml)
        mixseek config init --component orchestrator \\
            --output-path my-configs/orchestrator.toml --workspace /path/to/workspace

        # Generate with absolute path
        mixseek config init --component orchestrator --output-path /tmp/orchestrator.toml

        # Generate with MIXSEEK_WORKSPACE env var
        export MIXSEEK_WORKSPACE=/path/to/workspace
        mixseek config init --component orchestrator

        # Overwrite existing template
        mixseek config init --component orchestrator --force
    """
    try:
        from mixseek.config.template import TemplateGenerator
        from mixseek.utils.env import get_workspace_from_env

        # === Step 1: Determine workspace ===
        if workspace is None:
            workspace = get_workspace_from_env()

            if workspace is None:
                # workspace 未指定時の動作
                if output_path and output_path.is_absolute():
                    # 絶対パスが指定されている場合は workspace 不要
                    workspace = None
                else:
                    # 相対パスまたはデフォルトパスの場合は workspace が必要
                    typer.echo(
                        "Error: Workspace path must be specified via --workspace or MIXSEEK_WORKSPACE env var.",
                        err=True,
                    )
                    typer.echo(
                        "Example: mixseek config init --component orchestrator --workspace /path/to/workspace",
                        err=True,
                    )
                    raise typer.Exit(code=1)

        # === Step 2: Determine component name ===
        if component:
            component_lower = component.lower()
        else:
            component_lower = "config"

        # === Step 3: Determine output path ===
        if output_path:
            # --output-path が指定された場合
            if output_path.is_absolute():
                # 絶対パス: そのまま使用
                final_output_path = output_path
            else:
                # 相対パス: workspace からの相対パスとして解釈
                if workspace is None:
                    typer.echo(
                        "Error: Workspace is required for relative output path.",
                        err=True,
                    )
                    raise typer.Exit(code=1)
                final_output_path = workspace / output_path
        else:
            # --output-path が未指定の場合: デフォルトパス
            # Note: Step 1 で workspace is None の場合はすでにエラー終了しているため、
            #       ここでは workspace は必ず存在する
            assert workspace is not None  # Type assertion for mypy
            # デフォルト: workspace/configs/<component>.toml
            configs_dir = workspace / "configs"
            configs_dir.mkdir(parents=True, exist_ok=True)
            final_output_path = configs_dir / f"{component_lower}.toml"

        # === Step 4: Check if file exists ===
        if final_output_path.exists() and not force:
            typer.echo(
                f"Error: {final_output_path} already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(code=1)

        # === Step 5: Generate template ===
        # Handle prompt_builder specially (use default template file)
        if component_lower == "prompt_builder":
            import importlib.resources

            try:
                # Try Python 3.9+ API
                template_content = (
                    importlib.resources.files("mixseek")
                    .joinpath("config/templates/prompt_builder_default.toml")
                    .read_text(encoding="utf-8")
                )
            except AttributeError:
                # Fallback for older Python versions
                import pkgutil

                template_bytes = pkgutil.get_data("mixseek", "config/templates/prompt_builder_default.toml")
                if template_bytes is None:
                    raise FileNotFoundError("prompt_builder_default.toml template not found in package")
                template_content = template_bytes.decode("utf-8")

            # Ensure parent directory exists
            final_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write template
            final_output_path.write_text(template_content, encoding="utf-8")
        else:
            # Generate template using TemplateGenerator
            generator = TemplateGenerator()
            try:
                template = generator.generate_template(component_lower)
            except ValueError as e:
                typer.echo(f"Error: {str(e)}", err=True)
                raise typer.Exit(code=1)

            # Ensure parent directory exists
            final_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write template to file
            final_output_path.write_text(template)

        # === Step 6: Success message ===
        typer.echo(f"✓ Generated template: {final_output_path.name}")
        typer.echo(f"  Location: {final_output_path.absolute()}")

        if component_lower == "prompt_builder":
            typer.echo("\nEdit prompt_builder.toml to customize Team user prompt template.")
        else:
            typer.echo(f'\nEdit {final_output_path.name} and set required fields (marked with empty = "")')

    except Exception as e:
        error_msg = str(e)
        typer.echo(f"Error: {error_msg}", err=True)
        raise typer.Exit(code=1)
