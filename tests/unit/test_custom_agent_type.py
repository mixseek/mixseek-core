"""Unit tests for custom agent type support.

This test suite validates that users can register and use custom agent types
beyond the built-in AgentType enum values.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the implementation to ensure proper extensibility.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.models.member_agent import (
    MemberAgentConfig,
    MemberAgentResult,
)


class CustomMemberAgent(BaseMemberAgent):
    """Custom Member Agent implementation for testing."""

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute custom agent logic."""
        return MemberAgentResult.success(
            content=f"Custom agent processed: {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )


class TestCustomAgentType:
    """Test custom agent type registration and usage."""

    def test_custom_agent_type_string_in_config(self) -> None:
        """Test MemberAgentConfig accepts custom type as string."""
        config = MemberAgentConfig(
            name="my-custom-agent",
            type="custom",  # Custom string type
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Custom agent instructions.",
        )

        assert config.name == "my-custom-agent"
        assert config.type == "custom"

    def test_register_custom_agent_type(self) -> None:
        """Test registering a custom agent type with factory."""
        # Register custom agent type
        MemberAgentFactory.register_agent("custom", CustomMemberAgent)

        # Verify it's in supported types
        supported_types = MemberAgentFactory.get_supported_types()
        assert "custom" in supported_types

    def test_create_custom_agent_instance(self) -> None:
        """Test creating custom agent instance from factory."""
        # Register custom agent
        MemberAgentFactory.register_agent("custom", CustomMemberAgent)

        # Create config with custom type (disable file logging for tests)
        config = MemberAgentConfig(
            name="my-custom-agent",
            type="custom",
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Custom agent instructions.",
        )

        # Create agent from factory
        agent = MemberAgentFactory.create_agent(config)

        # Verify agent type
        assert isinstance(agent, CustomMemberAgent)
        assert agent.agent_name == "my-custom-agent"
        assert agent.agent_type == "custom"

    @pytest.mark.asyncio
    async def test_custom_agent_execution(self) -> None:
        """Test executing task with custom agent."""
        # Register custom agent
        MemberAgentFactory.register_agent("custom", CustomMemberAgent)

        # Create config (disable file logging for tests)
        config = MemberAgentConfig(
            name="my-custom-agent",
            type="custom",
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Custom agent instructions.",
        )

        # Create and execute agent
        agent = MemberAgentFactory.create_agent(config)
        result = await agent.execute("Test task")

        # Verify result
        assert result.is_success()
        assert result.content == "Custom agent processed: Test task"
        assert result.agent_name == "my-custom-agent"
        assert result.agent_type == "custom"

    def test_documentation_example_code(self) -> None:
        """Test the example code from docs/api/agents/member-agents.md works correctly.

        This test verifies the sample code from lines 550-560 of the documentation.
        """
        # Documentation example code (adapted)
        # Original: custom_type = AgentType("custom")
        # Fixed: use string directly
        custom_type = "custom"

        # Register custom agent
        MemberAgentFactory.register_agent(custom_type, CustomMemberAgent)

        # Create config (disable file logging for tests)
        config = MemberAgentConfig(
            name="my-custom-agent",
            type=custom_type,
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Custom instructions",
        )

        # Create agent
        agent = MemberAgentFactory.create_agent(config)

        # Verify
        assert isinstance(agent, CustomMemberAgent)
        assert agent.agent_type == "custom"

    def test_unregistered_custom_type_raises_error(self) -> None:
        """Test that using unregistered custom type raises ValueError."""
        config = MemberAgentConfig(
            name="my-agent",
            type="unregistered_custom_type",
            model="google-gla:gemini-2.5-flash-lite",
            system_instruction="Test instructions.",
        )

        with pytest.raises(ValueError, match="Unsupported agent type"):
            MemberAgentFactory.create_agent(config)

    def test_custom_agent_accepts_custom_model_prefix(self) -> None:
        """Test that custom agents can use arbitrary model prefixes.

        Issue #72: Custom agents (type="custom") should skip model prefix
        validation and accept any provider:model format.
        """
        config = MemberAgentConfig(
            name="my-agent",
            type="custom",
            model="my-provider:custom-model-v1",
            system_instruction="Test instructions.",
        )
        assert config.model == "my-provider:custom-model-v1"

    def test_builtin_agent_rejects_custom_model_prefix(self) -> None:
        """Test that builtin agents reject non-standard model prefixes.

        Builtin agents (plain, web_search, code_execution) must use standard
        prefixes: google-gla:, google-vertex:, openai:, anthropic:, grok:, grok-responses:
        """
        with pytest.raises(ValidationError) as exc_info:
            MemberAgentConfig(
                name="my-agent",
                type="plain",
                model="custom-prefix:my-model",
                system_instruction="Test instructions.",
            )
        # Use errors() for more robust assertion
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("model",)
        assert "Unsupported model" in errors[0]["msg"]

    def test_custom_agent_rejects_empty_model(self) -> None:
        """Test that custom agents reject empty model string.

        Even custom agents require basic format validation:
        model must be non-empty and contain colon separator.
        """
        with pytest.raises(ValidationError) as exc_info:
            MemberAgentConfig(
                name="my-agent",
                type="custom",
                model="",
                system_instruction="Test instructions.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("model",)
        assert "cannot be empty" in errors[0]["msg"]

    def test_custom_agent_rejects_model_without_colon(self) -> None:
        """Test that custom agents reject model without colon separator.

        Even custom agents require 'prefix:model' format.
        """
        with pytest.raises(ValidationError) as exc_info:
            MemberAgentConfig(
                name="my-agent",
                type="custom",
                model="no-colon-here",
                system_instruction="Test instructions.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("model",)
        assert "prefix:model" in errors[0]["msg"]
