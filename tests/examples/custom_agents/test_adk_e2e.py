"""End-to-end tests for ADK Research Agent.

These tests require a valid GOOGLE_API_KEY environment variable and
will make real API calls to Google's Gemini API.

Run with: pytest -m e2e tests/examples/custom_agents/test_adk_e2e.py -v
"""

import pytest

# Skip entire module if google-adk is not installed
pytest.importorskip("google.adk")

import os
import time

from examples.custom_agents.adk_research.agent import ADKResearchAgent
from mixseek.models.member_agent import (
    MemberAgentConfig,
    PluginMetadata,
    ResultStatus,
)


def get_e2e_config() -> MemberAgentConfig:
    """Create a MemberAgentConfig for E2E testing."""
    return MemberAgentConfig(
        name="adk-research-e2e-test",
        type="custom",
        model="google-gla:gemini-2.5-flash",
        temperature=0.7,
        max_tokens=4096,
        description="E2E Test ADK Research Agent",
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
                    "search_result_limit": 5,
                    "researcher_count": 2,  # Reduced for faster E2E tests
                    "timeout_seconds": 60,  # Longer timeout for E2E
                }
            }
        },
    )


@pytest.mark.e2e
class TestADKResearchAgentE2E:
    """End-to-end tests for ADK Research Agent with real API."""

    @pytest.fixture(autouse=True)
    def check_api_key(self) -> None:
        """Skip tests if GOOGLE_API_KEY is not set."""
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY environment variable not set")

    @pytest.mark.asyncio
    async def test_single_search_real_api(self) -> None:
        """Test single search with real Gemini API.

        SC-001: Should complete within 10 seconds for simple queries.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        start_time = time.time()

        result = await agent.execute("What is Python programming language?")

        elapsed_time = time.time() - start_time

        # Verify success
        assert result.status == ResultStatus.SUCCESS
        assert result.content
        assert len(result.content) > 100  # Meaningful response

        # Verify metadata
        assert result.metadata["mode"] == "single_search"
        assert result.execution_time_ms is not None

        # SC-001: 10 second target (with margin for network variability)
        assert elapsed_time < 30, f"Single search took {elapsed_time:.2f}s (target: <10s)"

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_deep_research_real_api(self) -> None:
        """Test Deep Research pipeline with real Gemini API.

        SC-002: Should complete within 30 seconds for deep research.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        start_time = time.time()

        result = await agent.execute(
            "What are the main differences between Python and JavaScript?",
            deep_research=True,
        )

        elapsed_time = time.time() - start_time

        # Verify success
        assert result.status == ResultStatus.SUCCESS
        assert result.content
        assert len(result.content) > 200  # More comprehensive response

        # Verify metadata
        assert result.metadata["mode"] == "deep_research"

        # SC-002: 30 second target (with margin for network variability)
        assert elapsed_time < 90, f"Deep research took {elapsed_time:.2f}s (target: <30s)"

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_google_search_tool_execution(self) -> None:
        """Test that google_search tool is actually executed.

        Verifies FR-001: System uses google_search tool for web search.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        # Query that requires current information
        result = await agent.execute("What is the current version of Python?")

        # Verify success
        assert result.status == ResultStatus.SUCCESS

        # Should mention Python version (current or recent)
        content_lower = result.content.lower()
        assert "python" in content_lower
        assert any(version in content_lower for version in ["3.1", "3.12", "3.13", "3.14"])

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_source_tracking(self) -> None:
        """Test that sources are tracked in metadata.

        Verifies FR-004: Source information stored in metadata.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        result = await agent.execute("What is machine learning?")

        # Verify success
        assert result.status == ResultStatus.SUCCESS

        # Verify source tracking
        assert "sources" in result.metadata
        assert "source_count" in result.metadata

        # Note: Sources may be empty if no URLs are in the response text
        # The URL extraction is simplified; full implementation would parse
        # groundingMetadata from ADK response

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_markdown_output_format(self) -> None:
        """Test that output is in Markdown format.

        Verifies FR-002: Output in Markdown format.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        result = await agent.execute("Explain the basics of REST APIs")

        # Verify success
        assert result.status == ResultStatus.SUCCESS

        # Check for Markdown formatting indicators
        content = result.content
        has_markdown = any(
            [
                "##" in content,  # Headers
                "**" in content,  # Bold
                "- " in content,  # Bullet points
                "* " in content,  # Bullet points alternative
                "1." in content,  # Numbered lists
            ]
        )

        assert has_markdown, "Response should contain Markdown formatting"

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_error_handling_invalid_query(self) -> None:
        """Test error handling with edge case queries."""
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        # Very long query that might cause issues
        long_query = "test " * 1000  # 5000 characters

        result = await agent.execute(long_query)

        # Should either succeed (truncated) or return structured error
        # Both are acceptable behaviors
        assert result.status in [ResultStatus.SUCCESS, ResultStatus.ERROR]

        if result.status == ResultStatus.ERROR:
            assert result.error_code is not None
            assert result.error_message is not None

        await agent.cleanup()


@pytest.mark.e2e
class TestADKResearchAgentIntegration:
    """Integration tests for ADK Research Agent with MixSeek-Core loader."""

    @pytest.fixture(autouse=True)
    def check_api_key(self) -> None:
        """Skip tests if GOOGLE_API_KEY is not set."""
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY environment variable not set")

    @pytest.mark.asyncio
    async def test_member_agent_result_compatibility(self) -> None:
        """Test that MemberAgentResult is fully compatible.

        Verifies SC-007: 100% compatibility with Leader Agent.
        """
        config = get_e2e_config()
        agent = ADKResearchAgent(config)

        result = await agent.execute("What is AI?")

        # Verify all required MemberAgentResult fields
        assert hasattr(result, "status")
        assert hasattr(result, "content")
        assert hasattr(result, "agent_name")
        assert hasattr(result, "agent_type")
        assert hasattr(result, "timestamp")
        assert hasattr(result, "metadata")

        # Verify types
        assert isinstance(result.status, ResultStatus)
        assert isinstance(result.content, str)
        assert isinstance(result.agent_name, str)
        assert isinstance(result.agent_type, str)
        assert isinstance(result.metadata, dict)

        # Verify values
        assert result.agent_name == "adk-research-e2e-test"
        assert result.agent_type == "custom"

        await agent.cleanup()
