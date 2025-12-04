"""Unit tests for Web Fetch Member Agent.

This test suite validates the Web Fetch Member Agent implementation,
including provider validation, tool configuration, error handling, and execution.

According to Article 3 (Test-First Imperative), these tests validate
the Web Fetch Agent implementation for Issue #230.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mixseek.models.member_agent import (
    AgentType,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
    ToolSettings,
    WebFetchToolConfig,
)


@pytest.fixture
def web_fetch_agent_config_anthropic() -> MemberAgentConfig:
    """Create test configuration for Web Fetch Agent with Anthropic model."""
    return MemberAgentConfig(
        name="test-fetch-agent",
        type="web_fetch",
        model="anthropic:claude-sonnet-4-5-20250929",
        system_instruction="Test instructions for web fetch agent behavior.",
        tool_settings=ToolSettings(
            web_fetch=WebFetchToolConfig(
                max_uses=5,
                enable_citations=True,
                max_content_tokens=30000,
            )
        ),
    )


@pytest.fixture
def web_fetch_agent_config_google() -> MemberAgentConfig:
    """Create test configuration for Web Fetch Agent with Google model."""
    return MemberAgentConfig(
        name="test-fetch-agent-google",
        type="web_fetch",
        model="google-gla:gemini-2.5-flash",
        system_instruction="Test instructions for web fetch agent behavior.",
    )


class TestWebFetchToolConfig:
    """Test WebFetchToolConfig validation."""

    def test_valid_configuration(self) -> None:
        """Test valid configuration with all parameters."""
        config = WebFetchToolConfig(
            max_uses=10,
            allowed_domains=["example.com", "docs.example.com"],
            enable_citations=True,
            max_content_tokens=40000,
        )
        assert config.max_uses == 10
        assert config.allowed_domains == ["example.com", "docs.example.com"]
        assert config.enable_citations is True
        assert config.max_content_tokens == 40000

    def test_domain_exclusivity_validation(self) -> None:
        """Test that allowed_domains and blocked_domains are mutually exclusive."""
        with pytest.raises(ValueError) as exc_info:
            WebFetchToolConfig(
                allowed_domains=["example.com"],
                blocked_domains=["malicious.com"],
            )
        assert "mutually exclusive" in str(exc_info.value)

    def test_max_content_tokens_validation(self) -> None:
        """Test max_content_tokens upper bound validation."""
        with pytest.raises(ValueError):
            WebFetchToolConfig(max_content_tokens=60000)  # > 50000

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        config = WebFetchToolConfig()
        assert config.max_uses is None
        assert config.allowed_domains is None
        assert config.blocked_domains is None
        assert config.enable_citations is False
        assert config.max_content_tokens is None


class TestWebFetchMemberAgent:
    """Test Web Fetch Member Agent implementation."""

    def test_agent_initialization_anthropic(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test Web Fetch Agent initialization with Anthropic model."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        assert agent.agent_name == "test-fetch-agent"
        assert agent.agent_type == AgentType.WEB_FETCH
        assert agent._agent is not None

    def test_agent_initialization_google(self, web_fetch_agent_config_google: MemberAgentConfig) -> None:
        """Test Web Fetch Agent initialization with Google model."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_google)

        assert agent.agent_name == "test-fetch-agent-google"
        assert agent.agent_type == AgentType.WEB_FETCH
        assert agent._agent is not None

    def test_unsupported_provider_error_openai(self) -> None:
        """Test that OpenAI model raises ValueError."""
        config = MemberAgentConfig(
            name="test-fetch-openai",
            type="web_fetch",
            model="openai:gpt-4o",
            system_instruction="Test instructions.",
        )

        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        with pytest.raises(ValueError) as exc_info:
            WebFetchMemberAgent(config)

        assert "only supports Anthropic and Google" in str(exc_info.value)

    def test_unsupported_provider_error_grok(self) -> None:
        """Test that Grok model raises ValueError."""
        config = MemberAgentConfig(
            name="test-fetch-grok",
            type="web_fetch",
            model="grok-responses:grok-4-fast",
            system_instruction="Test instructions.",
        )

        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        with pytest.raises(ValueError) as exc_info:
            WebFetchMemberAgent(config)

        assert "only supports Anthropic and Google" in str(exc_info.value)

    def test_agent_properties(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test agent properties from base class."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        assert agent.agent_name == web_fetch_agent_config_anthropic.name
        assert agent.agent_type == web_fetch_agent_config_anthropic.type
        assert agent.config == web_fetch_agent_config_anthropic

    @pytest.mark.asyncio
    async def test_execute_success_with_mock(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test successful execution with mock web fetch."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(
                output="The page content is: Welcome to Example.com",
                usage=MagicMock(total_tokens=250),
            )
        )

        result = await agent.execute("Summarize https://example.com")

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert result.agent_name == "test-fetch-agent"
        assert result.agent_type == "web_fetch"
        assert result.content is not None
        assert "Example.com" in result.content
        assert result.is_success() is True
        assert result.is_error() is False

    @pytest.mark.asyncio
    async def test_execute_empty_task_error(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test error handling for empty task."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        result = await agent.execute("")

        assert result.status == ResultStatus.ERROR
        assert result.error_code == "EMPTY_TASK"
        if result.error_message:
            assert "empty" in result.error_message.lower()
        assert result.is_error() is True
        assert result.is_success() is False

    @pytest.mark.asyncio
    async def test_execute_with_context(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test execution with context parameter."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(
                output="Response with context applied",
                usage=MagicMock(total_tokens=180),
            )
        )

        context = {"topic": "AI", "format": "summary"}
        result = await agent.execute("Fetch https://ai.example.com", context=context)

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "web_fetch"
        assert isinstance(result.metadata, dict)
        assert "context" in result.metadata

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test handling of fetch errors."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock fetch failure
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=Exception("Failed to fetch URL"))

        result = await agent.execute("Fetch https://unreachable.com")

        assert result.status == ResultStatus.ERROR
        assert result.error_code == "EXECUTION_ERROR"
        assert result.is_error() is True
        if result.error_message:
            assert "Failed to fetch URL" in result.error_message

    @pytest.mark.asyncio
    async def test_timeout_handling(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test handling of timeout errors."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock timeout error
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=TimeoutError("Request timed out"))

        result = await agent.execute("Fetch https://slow-server.com")

        assert result.status == ResultStatus.ERROR
        assert result.is_error() is True

    def test_tool_configuration_applied(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test that web fetch tool configuration is properly applied."""
        from mixseek.agents.member.web_fetch import WebFetchAgentDeps, WebFetchMemberAgent

        # Create agent to verify configuration
        WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # WebFetchAgentDeps should include tool config
        assert web_fetch_agent_config_anthropic.tool_settings is not None
        assert web_fetch_agent_config_anthropic.tool_settings.web_fetch is not None
        deps = WebFetchAgentDeps(
            config=web_fetch_agent_config_anthropic,
            web_fetch_config=web_fetch_agent_config_anthropic.tool_settings.web_fetch,
        )

        assert deps.config == web_fetch_agent_config_anthropic
        assert deps.web_fetch_config is not None
        assert deps.web_fetch_config.max_uses == 5
        assert deps.web_fetch_config.enable_citations is True
        assert deps.web_fetch_config.max_content_tokens == 30000

    @pytest.mark.asyncio
    async def test_default_tool_configuration(self) -> None:
        """Test agent with default tool configuration (no web_fetch settings)."""
        config = MemberAgentConfig(
            name="default-fetch-agent",
            type=AgentType.WEB_FETCH,
            model="anthropic:claude-sonnet-4-5-20250929",
            system_instruction="Default web fetch instructions.",
        )

        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(config)

        # Should have no tool settings
        assert agent.config.tool_settings is None
        # Agent should still be functional
        assert agent.agent_name == "default-fetch-agent"

    def test_dependencies_structure(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test that WebFetchAgentDeps structure is correct."""
        import dataclasses

        from mixseek.agents.member.web_fetch import WebFetchAgentDeps

        assert dataclasses.is_dataclass(WebFetchAgentDeps)

        assert web_fetch_agent_config_anthropic.tool_settings is not None
        assert web_fetch_agent_config_anthropic.tool_settings.web_fetch is not None
        deps = WebFetchAgentDeps(
            config=web_fetch_agent_config_anthropic,
            web_fetch_config=web_fetch_agent_config_anthropic.tool_settings.web_fetch,
        )

        assert deps.config == web_fetch_agent_config_anthropic
        assert deps.web_fetch_config == web_fetch_agent_config_anthropic.tool_settings.web_fetch

    @pytest.mark.asyncio
    async def test_result_metadata_population(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test that results include web fetch metadata."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock successful execution with usage info
        agent._agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "Fetched content from URL"
        mock_usage = MagicMock(total_tokens=300, prompt_tokens=100, completion_tokens=200)
        mock_result.usage = MagicMock(return_value=mock_usage)
        agent._agent.run = AsyncMock(return_value=mock_result)

        result = await agent.execute("Fetch https://example.com")

        assert result.status == ResultStatus.SUCCESS
        assert result.usage_info is not None
        assert "total_tokens" in result.usage_info
        assert result.usage_info["total_tokens"] == 300

        # Should include model_id in metadata
        assert "model_id" in result.metadata
        assert result.metadata["model_id"] == web_fetch_agent_config_anthropic.model

    @pytest.mark.asyncio
    async def test_agent_capabilities_annotation(self, web_fetch_agent_config_anthropic: MemberAgentConfig) -> None:
        """Test that agent properly annotates its capabilities."""
        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        agent = WebFetchMemberAgent(web_fetch_agent_config_anthropic)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(
                output="Response with web fetch capability",
                usage=MagicMock(total_tokens=150),
            )
        )

        result = await agent.execute("Fetch URL content")

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "web_fetch"

        # Metadata should indicate fetch capabilities
        assert "capabilities" in result.metadata
        assert "web_fetch" in result.metadata["capabilities"]


class TestWebFetchAgentFactory:
    """Test Web Fetch Agent creation through factory."""

    def test_factory_creates_web_fetch_agent(self) -> None:
        """Test that factory correctly creates WebFetchMemberAgent."""
        from mixseek.agents.member.factory import MemberAgentFactory

        config = MemberAgentConfig(
            name="factory-test-agent",
            type="web_fetch",
            model="anthropic:claude-sonnet-4-5-20250929",
            system_instruction="Factory test instructions.",
        )

        agent = MemberAgentFactory.create_agent(config)

        from mixseek.agents.member.web_fetch import WebFetchMemberAgent

        assert isinstance(agent, WebFetchMemberAgent)
        assert agent.agent_name == "factory-test-agent"
        assert agent.agent_type == "web_fetch"

    def test_factory_supported_types_includes_web_fetch(self) -> None:
        """Test that factory reports web_fetch as supported type."""
        from mixseek.agents.member.factory import MemberAgentFactory

        supported_types = MemberAgentFactory.get_supported_types()

        assert "web_fetch" in supported_types
