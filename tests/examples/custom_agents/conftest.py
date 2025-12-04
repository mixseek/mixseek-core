"""Shared fixtures for ADK Research Agent tests."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ADK models import - these don't require google-adk
from examples.custom_agents.adk_research.models import ADKAgentConfig, SearchResult
from mixseek.models.member_agent import (
    MemberAgentConfig,
    PluginMetadata,
)


@pytest.fixture(autouse=True)
def mock_workspace_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set MIXSEEK_WORKSPACE environment variable for all tests."""
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace_path))
    return workspace_path


@pytest.fixture
def sample_adk_config() -> ADKAgentConfig:
    """Create a sample ADKAgentConfig for testing."""
    return ADKAgentConfig(
        gemini_model="gemini-2.5-flash",
        temperature=0.7,
        max_output_tokens=4096,
        search_result_limit=10,
        researcher_count=3,
        timeout_seconds=30,
    )


@pytest.fixture
def sample_member_agent_config() -> MemberAgentConfig:
    """Create a sample MemberAgentConfig with ADK research settings."""
    return MemberAgentConfig(
        name="test-adk-agent",
        type="custom",
        model="google-gla:gemini-2.5-flash",
        temperature=0.7,
        max_tokens=4096,
        description="Test ADK Research Agent",
        system_instruction="You are a research assistant.",
        plugin=PluginMetadata(
            path="/app/examples/custom_agents/adk_research/agent.py",
            agent_class="ADKResearchAgent",
        ),
        metadata={
            "tool_settings": {
                "adk_research": {
                    "gemini_model": "gemini-2.5-flash",
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                    "search_result_limit": 10,
                    "researcher_count": 3,
                    "timeout_seconds": 30,
                }
            }
        },
    )


@pytest.fixture
def sample_member_agent_config_missing_settings() -> MemberAgentConfig:
    """Create a MemberAgentConfig without ADK research settings for error testing."""
    return MemberAgentConfig(
        name="test-adk-agent-no-settings",
        type="custom",
        model="google-gla:gemini-2.5-flash",
        system_instruction="You are a research assistant.",
        plugin=PluginMetadata(
            path="/app/examples/custom_agents/adk_research/agent.py",
            agent_class="ADKResearchAgent",
        ),
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Create sample SearchResult objects for testing."""
    return [
        SearchResult(
            url="https://example.com/article1",
            title="AI Trends 2025",
            snippet="Article about AI trends...",
        ),
        SearchResult(
            url="https://example.com/article2",
            title="Machine Learning Guide",
            snippet="Guide to machine learning...",
        ),
    ]


@pytest.fixture
def mock_adk_response() -> dict[str, Any]:
    """Create a mock ADK response for testing with grounding metadata (FR-004)."""
    return {
        "content": """## Research Summary

Based on my search, here are the key findings about AI trends:

1. **Large Language Models** are becoming more multimodal
2. **Agent frameworks** like ADK are gaining popularity
3. **Open source** AI development is accelerating

### Sources

- [AI Trends 2025](https://example.com/article1)
- [ML Guide](https://example.com/article2)
""",
        "events": [],
        "session_id": "test-session-123",
        "grounding_metadata": [
            {
                "sources": [
                    {"url": "https://example.com/article1", "title": "AI Trends 2025"},
                    {"url": "https://example.com/article2", "title": "Machine Learning Guide"},
                ],
                "queries": ["AI trends 2025"],
            }
        ],
    }


@pytest.fixture
def mock_adk_error_response() -> Exception:
    """Create mock error responses for testing."""
    return Exception("Rate limit exceeded: 429 Too Many Requests")


@pytest.fixture
def mock_runner() -> MagicMock:
    """Create a mock ADKRunnerWrapper for testing with grounding metadata."""
    runner = MagicMock()
    runner.run_once = AsyncMock(
        return_value={
            "content": "Test response content with sources",
            "events": [],
            "session_id": "test-session",
            "grounding_metadata": [
                {
                    "sources": [
                        {"url": "https://example.com/source", "title": "Test Source"},
                    ]
                }
            ],
        }
    )
    runner.cleanup = AsyncMock()
    return runner


@pytest.fixture
def mock_llm_agent() -> MagicMock:
    """Create a mock LlmAgent for testing."""
    agent = MagicMock()
    agent.name = "mock_researcher"
    agent.model = "gemini-2.5-flash"
    return agent


@pytest.fixture
def mock_parallel_agent() -> MagicMock:
    """Create a mock ParallelAgent for testing."""
    agent = MagicMock()
    agent.name = "mock_parallel"
    agent.sub_agents = []
    return agent


@pytest.fixture
def mock_sequential_agent() -> MagicMock:
    """Create a mock SequentialAgent for testing."""
    agent = MagicMock()
    agent.name = "mock_sequential"
    agent.sub_agents = []
    return agent
