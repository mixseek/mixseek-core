"""TOML configuration template generation."""

import shutil
from pathlib import Path


def generate_sample_config(workspace_path: Path) -> None:
    """
    Generate sample configuration TOML files with comments.

    Creates the following files in the workspace:
    - configs/search_news.toml: Simple news search orchestrator (default settings)
    - configs/search_news_multi_perspective.toml: Multi-perspective orchestrator (3 teams)
    - configs/agents/team_general_researcher.toml: General research team
    - configs/agents/team_sns_researcher.toml: SNS-focused research team
    - configs/agents/team_academic_researcher.toml: Academic research team
    - configs/evaluators/evaluator_search_news.toml: Evaluator configuration
    - configs/judgment/judgment_search_news.toml: Judgment configuration

    Args:
        workspace_path: Absolute path to workspace root
    """
    # Create subdirectories
    agents_dir = workspace_path / "configs" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    evaluators_dir = workspace_path / "configs" / "evaluators"
    evaluators_dir.mkdir(parents=True, exist_ok=True)

    judgment_dir = workspace_path / "configs" / "judgment"
    judgment_dir.mkdir(parents=True, exist_ok=True)

    # Copy template files from package
    _copy_template_files(workspace_path)


def _copy_template_files(workspace_path: Path) -> None:
    """Copy template configuration files from package to workspace."""
    # Get the templates directory in the package
    templates_dir = Path(__file__).parent / "templates"

    # Template files to copy (name -> destination relative to configs/)
    template_files = {
        "search_news.toml": "search_news.toml",
        "search_news_multi_perspective.toml": "search_news_multi_perspective.toml",
        "team_general_researcher.toml": "agents/team_general_researcher.toml",
        "team_sns_researcher.toml": "agents/team_sns_researcher.toml",
        "team_academic_researcher.toml": "agents/team_academic_researcher.toml",
        "evaluator_search_news.toml": "evaluators/evaluator_search_news.toml",
        "judgment_search_news.toml": "judgment/judgment_search_news.toml",
    }

    configs_dir = workspace_path / "configs"

    for template_name, dest_path in template_files.items():
        src_file = templates_dir / template_name
        dst_file = configs_dir / dest_path

        # Skip if template file doesn't exist (graceful degradation)
        if not src_file.exists():
            continue

        # Copy the template file
        shutil.copy2(src_file, dst_file)
