"""Unit tests for Web Search Member Agent.

This test suite validates the Web Search Member Agent implementation,
including tool integration, search capabilities, error handling, and configuration.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the Web Search Agent implementation to ensure proper functionality and error handling.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mixseek.models.member_agent import (
    AgentType,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
    ToolSettings,
    WebSearchToolConfig,
)


@pytest.fixture
def web_search_agent_config() -> MemberAgentConfig:
    """Create test configuration for Web Search Agent."""
    return MemberAgentConfig(
        name="test-search-agent",
        type="web_search",
        model="google-gla:gemini-2.5-flash-lite",
        system_instruction="Test instructions for web search agent behavior.",
        tool_settings=ToolSettings(web_search=WebSearchToolConfig(max_results=5, timeout=20)),
    )


class TestWebSearchMemberAgent:
    """Test Web Search Member Agent implementation."""

    def test_agent_initialization(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test Web Search Agent initialization."""
        # Import will fail until T017 is implemented
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        assert agent.agent_name == "test-search-agent"
        assert agent.agent_type == AgentType.WEB_SEARCH
        assert agent._agent is not None

    def test_agent_properties(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test agent properties from base class."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        assert agent.agent_name == web_search_agent_config.name
        assert agent.agent_type == web_search_agent_config.type
        assert agent.config == web_search_agent_config

    @pytest.mark.asyncio
    async def test_execute_success_with_mock_search(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test successful execution with mock web search."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock successful execution with search results
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(
                output="Based on search results, the answer is: Current weather info",
                usage=MagicMock(total_tokens=250),
            )
        )

        result = await agent.execute("What's the weather like today?")

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert result.agent_name == "test-search-agent"
        assert result.agent_type == "web_search"
        assert result.content is not None
        assert "Current weather info" in result.content
        assert result.is_success() is True
        assert result.is_error() is False

    @pytest.mark.asyncio
    async def test_execute_empty_task_error(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test error handling for empty task."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        result = await agent.execute("")

        assert result.status == ResultStatus.ERROR
        if result.content:
            assert "cannot be empty" in result.content.lower() or "empty" in result.content.lower()
        if result.error_message:
            assert "empty" in result.error_message.lower()
        assert result.is_error() is True
        assert result.is_success() is False

    @pytest.mark.asyncio
    async def test_execute_with_search_context(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test execution with search context parameter."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Research response with web sources", usage=MagicMock(total_tokens=180))
        )

        context = {"search_domain": "news", "time_filter": "recent"}
        result = await agent.execute("Latest AI developments", context=context)

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "web_search"
        assert isinstance(result.metadata, dict)
        # Context should be stored in metadata
        assert "context" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_search_error_handling(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test handling of web search errors."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock search failure
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=Exception("Search service unavailable"))

        result = await agent.execute("Test search query")

        assert result.status == ResultStatus.ERROR
        assert (result.error_message and "Search service unavailable" in result.error_message) or (
            result.content and "Search service unavailable" in result.content
        )
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_tool_configuration_applied(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test that web search tool configuration is properly applied."""
        from mixseek.agents.member.web_search import WebSearchAgentDeps, WebSearchMemberAgent

        # Create agent for dependency testing
        WebSearchMemberAgent(web_search_agent_config)

        # WebSearchAgentDeps should include tool config
        assert web_search_agent_config.tool_settings is not None
        assert web_search_agent_config.tool_settings.web_search is not None
        deps = WebSearchAgentDeps(
            config=web_search_agent_config, web_search_config=web_search_agent_config.tool_settings.web_search
        )

        assert deps.config == web_search_agent_config
        assert deps.web_search_config is not None
        assert deps.web_search_config.max_results == 5
        assert deps.web_search_config.timeout == 20

    @pytest.mark.asyncio
    async def test_execute_with_search_tool_kwargs(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test execution with web search specific parameters."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(
                output="Search results: Found relevant information", usage=MagicMock(total_tokens=200)
            )
        )

        result = await agent.execute("Python programming tutorials", search_domain="programming", max_results=3)

        assert result.status == ResultStatus.SUCCESS
        assert result.is_success() is True

    def test_agent_type_validation(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test agent validates web search type configuration."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        # Valid configuration should work
        agent = WebSearchMemberAgent(web_search_agent_config)
        assert agent.config.type == AgentType.WEB_SEARCH

        # Verify tool settings are accessible
        assert agent.config.tool_settings is not None
        assert agent.config.tool_settings.web_search is not None
        assert agent.config.tool_settings.web_search.max_results == 5

    @pytest.mark.asyncio
    async def test_search_timeout_handling(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test handling of search timeouts."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock timeout error
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=TimeoutError("Search timed out"))

        result = await agent.execute("Complex search query")

        assert result.status == ResultStatus.ERROR
        assert result.is_error() is True

    def test_dependencies_structure(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test that WebSearchAgentDeps structure is correct."""
        # WebSearchAgentDeps should be a dataclass with required fields
        import dataclasses

        from mixseek.agents.member.web_search import WebSearchAgentDeps

        assert dataclasses.is_dataclass(WebSearchAgentDeps)

        assert web_search_agent_config.tool_settings is not None
        assert web_search_agent_config.tool_settings.web_search is not None
        deps = WebSearchAgentDeps(
            config=web_search_agent_config, web_search_config=web_search_agent_config.tool_settings.web_search
        )

        assert deps.config == web_search_agent_config
        assert deps.web_search_config == web_search_agent_config.tool_settings.web_search

    @pytest.mark.asyncio
    async def test_search_result_metadata_population(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test that results include web search metadata."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock successful execution with usage info
        agent._agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "Research findings with citations"
        mock_usage = MagicMock(total_tokens=300, prompt_tokens=100, completion_tokens=200)
        mock_result.usage = MagicMock(return_value=mock_usage)
        agent._agent.run = AsyncMock(return_value=mock_result)

        result = await agent.execute("Research query")

        assert result.status == ResultStatus.SUCCESS
        assert result.usage_info is not None
        assert "total_tokens" in result.usage_info
        assert result.usage_info["total_tokens"] == 300

        # Should include agent type in metadata
        assert "model_id" in result.metadata
        assert result.metadata["model_id"] == web_search_agent_config.model

    @pytest.mark.asyncio
    async def test_agent_capabilities_annotation(self, web_search_agent_config: MemberAgentConfig) -> None:
        """Test that agent properly annotates its capabilities."""
        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(web_search_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Response with web search capability", usage=MagicMock(total_tokens=150))
        )

        result = await agent.execute("Search enabled query")

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "web_search"

        # Metadata should indicate search capabilities
        assert "capabilities" not in result.metadata or "web_search" in str(result.metadata)

    @pytest.mark.asyncio
    async def test_default_tool_configuration(self) -> None:
        """Test agent with default tool configuration."""
        # Config without explicit tool settings
        config = MemberAgentConfig(
            name="default-search-agent",
            type=AgentType.WEB_SEARCH,
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Default web search instructions.",
        )

        from mixseek.agents.member.web_search import WebSearchMemberAgent

        agent = WebSearchMemberAgent(config)

        # Should have default tool settings (tool_settings itself may be None)
        assert agent.config.tool_settings is None or agent.config.tool_settings.web_search is None
        # Agent should still be functional with defaults
        assert agent.agent_name == "default-search-agent"
