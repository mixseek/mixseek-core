"""Pytest fixtures for evaluator tests."""

from pathlib import Path
from typing import Any

import pytest

# Rebuild EvaluationRequest model to resolve forward references
from mixseek.models.evaluation_config import EvaluationConfig  # noqa: F401
from mixseek.models.evaluation_request import EvaluationRequest

EvaluationRequest.model_rebuild()


@pytest.fixture
def sample_user_query() -> str:
    """Sample user query for testing."""
    return "What are the benefits of using Python for data analysis?"


@pytest.fixture
def sample_submission() -> str:
    """Sample AI agent submission for testing."""
    return (
        "Python offers several benefits for data analysis:\n"
        "1. Rich ecosystem of libraries (pandas, numpy, scikit-learn)\n"
        "2. Easy to learn and read syntax\n"
        "3. Strong community support\n"
        "4. Excellent visualization tools (matplotlib, seaborn)\n"
        "5. Integration with big data tools"
    )


@pytest.fixture
def sample_team_id() -> str:
    """Sample team ID for testing."""
    return "team-alpha-001"


@pytest.fixture
def sample_evaluation_request_data(
    sample_user_query: str, sample_submission: str, sample_team_id: str
) -> dict[str, Any]:
    """Sample evaluation request data as dictionary."""
    return {
        "user_query": sample_user_query,
        "submission": sample_submission,
        "team_id": sample_team_id,
    }


@pytest.fixture
def mock_llm_response_clarity() -> dict[str, Any]:
    """Mock LLM response for clarity_coherence metric."""
    return {
        "score": 85,
        "comment": "The response is well-structured and clearly written. "
        "Each point is distinct and easy to understand.",
    }


@pytest.fixture
def mock_llm_response_coverage() -> dict[str, Any]:
    """Mock LLM response for coverage metric."""
    return {
        "score": 80,
        "comment": "The response covers major benefits but could include more details "
        "about performance and scalability aspects.",
    }


@pytest.fixture
def mock_llm_response_relevance() -> dict[str, Any]:
    """Mock LLM response for relevance metric."""
    return {
        "score": 90,
        "comment": "The response directly addresses the user's question about Python "
        "for data analysis. All points are relevant.",
    }


@pytest.fixture
def valid_config_toml_content() -> str:
    """Valid TOML configuration content for testing."""
    return """
# Valid evaluator configuration
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
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
def invalid_weights_config_toml() -> str:
    """TOML configuration with invalid weights (don't sum to 1.0)."""
    return """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5

[[metrics]]
name = "Coverage"
weight = 0.5

[[metrics]]
name = "Relevance"
weight = 0.3
"""


@pytest.fixture
def invalid_model_format_config_toml() -> str:
    """TOML configuration with invalid model format."""
    return """
[llm_default]
model = "invalid-model-format"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.5

[[metrics]]
name = "Relevance"
weight = 0.5
"""


@pytest.fixture
def missing_metrics_config_toml() -> str:
    """TOML configuration with no metrics defined."""
    return """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3
"""


@pytest.fixture
def custom_weights_config_toml() -> str:
    """TOML configuration with custom metric weights."""
    return """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "Relevance"
weight = 0.5

[[metrics]]
name = "ClarityCoherence"
weight = 0.3

[[metrics]]
name = "Coverage"
weight = 0.2
"""


@pytest.fixture
def two_metrics_config_toml() -> str:
    """TOML configuration with only two metrics enabled."""
    return """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.6

[[metrics]]
name = "Relevance"
weight = 0.4
"""


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Temporary directory for configuration files."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    return config_dir


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


@pytest.fixture
def mock_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock ANTHROPIC_API_KEY environment variable."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key-12345")


@pytest.fixture
def mock_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OPENAI_API_KEY environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-67890")


@pytest.fixture
def mock_all_api_keys(mock_anthropic_api_key: None, mock_openai_api_key: None) -> None:
    """Mock all required API keys."""
    pass
