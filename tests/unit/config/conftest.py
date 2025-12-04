"""Pytest fixtures for config tests.

Note: isolate_from_project_dotenv fixture is defined in tests/conftest.py (DRY principle).
"""

from pathlib import Path

import pytest


@pytest.fixture
def valid_config_toml_content() -> str:
    """Valid TOML configuration content for testing."""
    return """
# Valid evaluator configuration
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.0
max_tokens = 2000
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4
model = "anthropic:claude-sonnet-4-5-20250929"

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3
model = "openai:gpt-5"
"""


@pytest.fixture
def temp_workspace(tmp_path: Path, valid_config_toml_content: str) -> Path:
    """Temporary workspace with valid evaluator configuration."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config_dir = workspace / "configs"
    config_dir.mkdir()
    config_file = config_dir / "evaluator.toml"
    config_file.write_text(valid_config_toml_content)
    return workspace
