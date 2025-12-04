"""Unit tests for Plain Member Agent.

This test suite validates the Plain Member Agent implementation,
including initialization, execution, error handling, and configuration.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the Plain Agent implementation to ensure proper functionality and error handling.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mixseek.models.member_agent import (
    AgentType,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
)


@pytest.fixture
def plain_agent_config() -> MemberAgentConfig:
    """Create test configuration for Plain Agent."""
    return MemberAgentConfig(
        name="test-plain-agent",
        type="plain",
        model="google-gla:gemini-2.5-flash-lite",
        system_instruction="Test instructions for plain agent behavior.",
    )


class TestPlainMemberAgent:
    """Test Plain Member Agent implementation."""

    def test_agent_initialization(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test Plain Agent initialization."""
        # Import will fail until T010 is implemented
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        assert agent.agent_name == "test-plain-agent"
        assert agent.agent_type == "plain"
        assert agent._agent is not None

    def test_agent_properties(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test agent properties from base class."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        assert agent.agent_name == plain_agent_config.name
        assert agent.agent_type == plain_agent_config.type
        assert agent.config == plain_agent_config

    @pytest.mark.asyncio
    async def test_execute_success_with_test_model(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test successful execution with TestModel (no API cost)."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Use TestModel for fast, deterministic testing
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(data="Test response from plain agent", usage=MagicMock(total_tokens=150))
        )

        result = await agent.execute("Test prompt for plain agent")

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert result.agent_name == "test-plain-agent"
        assert result.agent_type == "plain"
        assert result.content is not None
        assert len(result.content) > 0
        assert result.is_success() is True
        assert result.is_error() is False

    @pytest.mark.asyncio
    async def test_execute_empty_task_error(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test error handling for empty task."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        result = await agent.execute("")

        assert result.status == ResultStatus.ERROR
        if result.content:
            assert "cannot be empty" in result.content.lower() or "empty" in result.content.lower()
        if result.error_message:
            assert "empty" in result.error_message.lower()
        assert result.is_error() is True
        assert result.is_success() is False

    @pytest.mark.asyncio
    async def test_execute_whitespace_only_task_error(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test error handling for whitespace-only task."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        result = await agent.execute("   \n\t  ")

        assert result.status == ResultStatus.ERROR
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_execute_with_context(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test execution with context parameter."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(data="Response with context", usage=MagicMock(total_tokens=100))
        )

        context = {"session_id": "test-123", "user": "developer"}
        result = await agent.execute("Test prompt", context=context)

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "plain"
        # Context should be stored in metadata
        assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_execute_pydantic_ai_error_handling(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test handling of Pydantic AI execution errors."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock Pydantic AI Agent to raise exception
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=Exception("AI model error"))

        result = await agent.execute("Test prompt")

        assert result.status == ResultStatus.ERROR
        assert (result.error_message and "AI model error" in result.error_message) or (
            result.content and "AI model error" in result.content
        )
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_execute_timeout_handling(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test handling of execution timeouts."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock timeout error
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=TimeoutError("Request timed out"))

        result = await agent.execute("Test prompt")

        assert result.status == ResultStatus.ERROR
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_execute_with_kwargs(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test execution with additional keyword arguments."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(data="Response with kwargs", usage=MagicMock(total_tokens=75))
        )

        result = await agent.execute("Test prompt", temperature=0.5, max_tokens=1000)

        assert result.status == ResultStatus.SUCCESS
        assert result.is_success() is True

    def test_agent_configuration_validation(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test agent validates its configuration properly."""
        from mixseek.agents.member.plain import PlainMemberAgent

        # Valid configuration should work
        agent = PlainMemberAgent(plain_agent_config)
        assert agent.config.type == "plain"

        # Invalid agent type should be handled gracefully
        invalid_config = MemberAgentConfig(
            name="invalid-agent",
            type=AgentType.WEB_SEARCH,  # Wrong type for PlainMemberAgent
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Test instructions.",
        )

        # Should still create the agent (validation is at factory level)
        agent_invalid = PlainMemberAgent(invalid_config)
        assert agent_invalid.config.type == AgentType.WEB_SEARCH

    @pytest.mark.asyncio
    async def test_initialize_method(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test agent initialization method."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Initialize should not raise errors
        await agent.initialize()

        # Agent should still be functional after initialization
        assert agent.agent_name == "test-plain-agent"

    @pytest.mark.asyncio
    async def test_cleanup_method(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test agent cleanup method."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Cleanup should not raise errors
        await agent.cleanup()

        # Agent properties should still be accessible
        assert agent.agent_name == "test-plain-agent"

    def test_agent_dependencies_structure(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test that PlainAgentDeps structure is correct."""
        # PlainAgentDeps should be a dataclass with config field
        import dataclasses

        from mixseek.agents.member.plain import PlainAgentDeps

        assert dataclasses.is_dataclass(PlainAgentDeps)

        deps = PlainAgentDeps(config=plain_agent_config)
        assert deps.config == plain_agent_config

    @pytest.mark.asyncio
    async def test_result_metadata_population(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test that results include proper metadata."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock successful execution with usage info
        agent._agent = MagicMock()
        mock_result = MagicMock()
        mock_result.data = "Test response"
        mock_usage = MagicMock(total_tokens=200, prompt_tokens=50, completion_tokens=150)
        mock_result.usage = MagicMock(return_value=mock_usage)
        agent._agent.run = AsyncMock(return_value=mock_result)

        result = await agent.execute("Test prompt")

        assert result.status == ResultStatus.SUCCESS
        assert result.usage_info is not None
        assert "total_tokens" in result.usage_info
        assert result.usage_info["total_tokens"] == 200

    @pytest.mark.asyncio
    async def test_execution_timing_measurement(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test that execution time is measured and recorded."""
        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock execution that takes some time
        async def mock_run(*args: object, **kwargs: object) -> MagicMock:
            import asyncio

            await asyncio.sleep(0.01)  # 10ms delay
            return MagicMock(data="Response", usage=MagicMock(total_tokens=100))

        agent._agent = MagicMock()
        agent._agent.run = mock_run

        result = await agent.execute("Test prompt")

        assert result.status == ResultStatus.SUCCESS
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 10  # At least 10ms
        assert result.execution_time_ms < 1000  # But less than 1 second

    @pytest.mark.asyncio
    async def test_incomplete_tool_call_handling(self, plain_agent_config: MemberAgentConfig) -> None:
        """Test handling of IncompleteToolCall exception from Pydantic AI v1.3.0+.

        IncompleteToolCall is raised when token limit is reached during tool call generation.
        This should be handled explicitly and NOT retried.

        Reference: Pydantic AI v1.3.0 - https://github.com/pydantic/pydantic-ai/releases
        """
        from pydantic_ai import IncompleteToolCall

        from mixseek.agents.member.plain import PlainMemberAgent

        agent = PlainMemberAgent(plain_agent_config)

        # Mock IncompleteToolCall exception
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=IncompleteToolCall("Token limit reached during tool call"))

        result = await agent.execute("Test prompt that triggers incomplete tool call")

        # Should return error result
        assert result.status == ResultStatus.ERROR
        assert result.error_code == "TOKEN_LIMIT_EXCEEDED"
        assert result.error_message is not None
        assert "Tool call generation incomplete due to token limit" in result.error_message
        assert result.is_error() is True
        # Should NOT have been retried (retry_count should be 0)
        assert result.retry_count == 0
