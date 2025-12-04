"""Unit tests for Code Execution Member Agent.

This test suite validates the Code Execution Member Agent implementation,
including tool integration, code execution capabilities, error handling, and configuration.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the Code Execution Agent implementation to ensure proper functionality and error handling.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.models.member_agent import (
    AgentType,
    CodeExecutionToolConfig,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
    ToolSettings,
)


@pytest.fixture
def code_execution_agent_config() -> MemberAgentConfig:
    """Create test configuration for Code Execution Agent."""
    return MemberAgentConfig(
        name="test-code-agent",
        type="code_execution",
        model="anthropic:claude-sonnet-4-5-20250929",  # Code execution requires Anthropic
        system_instruction="Test instructions for code execution agent behavior.",
        tool_settings=ToolSettings(code_execution=CodeExecutionToolConfig()),
    )


class TestCodeExecutionMemberAgent:
    """Test Code Execution Member Agent implementation."""

    @pytest.fixture(autouse=True)
    def mock_agent_and_auth(self) -> Any:
        """Automatically mock Agent class and authentication for all tests in this class."""
        with (
            patch("mixseek.agents.member.code_execution.Agent") as mock_agent,
            patch("mixseek.agents.member.code_execution.create_authenticated_model") as mock_auth,
        ):
            mock_auth.return_value = MagicMock()
            mock_agent.return_value = MagicMock()
            yield {"agent": mock_agent, "auth": mock_auth}

    def test_agent_initialization(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test Code Execution Agent initialization."""
        # Import will fail until T022 is implemented
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        assert agent.agent_name == "test-code-agent"
        assert agent.agent_type == AgentType.CODE_EXECUTION
        assert agent._agent is not None

    def test_agent_properties(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test agent properties from base class."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        assert agent.agent_name == code_execution_agent_config.name
        assert agent.agent_type == code_execution_agent_config.type
        assert agent.config == code_execution_agent_config

    @pytest.mark.asyncio
    async def test_execute_success_with_mock_code(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test successful execution with mock code execution."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock successful execution with code results
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Code executed successfully. Result: 42", usage=MagicMock(total_tokens=300))
        )

        result = await agent.execute("Calculate 6 * 7")

        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert result.agent_name == "test-code-agent"
        assert result.agent_type == "code_execution"
        assert "42" in result.content or "executed" in result.content.lower()
        assert result.is_success() is True
        assert result.is_error() is False

    @pytest.mark.asyncio
    async def test_execute_empty_task_error(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test error handling for empty task."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        result = await agent.execute("")

        assert result.status == ResultStatus.ERROR
        error_message = result.error_message if result.error_message is not None else ""
        assert "cannot be empty" in result.content.lower() or "empty" in error_message.lower()
        assert result.is_error() is True
        assert result.is_success() is False

    @pytest.mark.asyncio
    async def test_execute_with_computation_context(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test execution with computational context parameter."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Data analysis completed: Mean = 5.5", usage=MagicMock(total_tokens=220))
        )

        context = {"data_format": "pandas", "libraries": ["numpy", "matplotlib"]}
        result = await agent.execute("Analyze dataset statistics", context=context)

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "code_execution"
        assert isinstance(result.metadata, dict)
        # Context should be stored in metadata
        assert "context" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_code_error_handling(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test handling of code execution errors."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock code execution failure
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=Exception("Code execution failed: SyntaxError"))

        result = await agent.execute("invalid syntax here")

        assert result.status == ResultStatus.ERROR
        error_message = result.error_message if result.error_message is not None else ""
        assert "Code execution failed" in error_message or "failed" in result.content.lower()
        assert result.is_error() is True

    @pytest.mark.asyncio
    async def test_tool_configuration_applied(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test that code execution tool configuration is properly applied."""
        from mixseek.agents.member.code_execution import CodeExecutionAgentDeps, CodeExecutionMemberAgent

        # Create agent for dependency testing
        CodeExecutionMemberAgent(code_execution_agent_config)

        # CodeExecutionAgentDeps should include tool config
        assert code_execution_agent_config.tool_settings is not None
        assert code_execution_agent_config.tool_settings.code_execution is not None
        deps = CodeExecutionAgentDeps(
            config=code_execution_agent_config,
            code_execution_config=code_execution_agent_config.tool_settings.code_execution,
        )

        assert deps.config == code_execution_agent_config
        assert deps.code_execution_config == code_execution_agent_config.tool_settings.code_execution

    @pytest.mark.asyncio
    async def test_execute_with_code_specific_kwargs(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test execution with code execution specific parameters."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Calculation result: 3.14159", usage=MagicMock(total_tokens=180))
        )

        result = await agent.execute(
            "Calculate pi to 5 decimal places", max_output_length=5000, allowed_modules=["math"]
        )

        assert result.status == ResultStatus.SUCCESS
        assert result.is_success() is True

    def test_agent_type_validation(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test agent validates code execution type configuration."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        # Valid configuration should work
        agent = CodeExecutionMemberAgent(code_execution_agent_config)
        assert agent.config.type == AgentType.CODE_EXECUTION

        # Verify tool settings are accessible
        assert agent.config.tool_settings is not None
        assert agent.config.tool_settings.code_execution is not None

    @pytest.mark.asyncio
    async def test_code_execution_timeout_handling(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test handling of code execution timeouts."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock timeout error
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=TimeoutError("Code execution timed out"))

        result = await agent.execute("while True: pass  # Infinite loop")

        assert result.status == ResultStatus.ERROR
        assert result.is_error() is True

    def test_dependencies_structure(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test that CodeExecutionAgentDeps structure is correct."""
        # CodeExecutionAgentDeps should be a dataclass with required fields
        import dataclasses

        from mixseek.agents.member.code_execution import CodeExecutionAgentDeps

        assert dataclasses.is_dataclass(CodeExecutionAgentDeps)

        assert code_execution_agent_config.tool_settings is not None
        assert code_execution_agent_config.tool_settings.code_execution is not None
        deps = CodeExecutionAgentDeps(
            config=code_execution_agent_config,
            code_execution_config=code_execution_agent_config.tool_settings.code_execution,
        )

        assert deps.config == code_execution_agent_config
        assert deps.code_execution_config == code_execution_agent_config.tool_settings.code_execution

    @pytest.mark.asyncio
    async def test_code_result_metadata_population(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test that results include code execution metadata."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock successful execution with usage info
        agent._agent = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "Computed fibonacci(10) = 55"
        mock_usage = MagicMock(total_tokens=400, prompt_tokens=150, completion_tokens=250)
        mock_result.usage = MagicMock(return_value=mock_usage)
        agent._agent.run = AsyncMock(return_value=mock_result)

        result = await agent.execute("def fibonacci(n): ...")

        assert result.status == ResultStatus.SUCCESS
        assert result.usage_info is not None
        assert "total_tokens" in result.usage_info
        assert result.usage_info["total_tokens"] == 400

        # Should include agent type in metadata
        assert "model_id" in result.metadata
        assert result.metadata["model_id"] == code_execution_agent_config.model

    @pytest.mark.asyncio
    async def test_agent_capabilities_annotation(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test that agent properly annotates its capabilities."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Mock successful execution
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(
            return_value=MagicMock(output="Code analysis complete: No errors found", usage=MagicMock(total_tokens=120))
        )

        result = await agent.execute("print('Hello, World!')")

        assert result.status == ResultStatus.SUCCESS
        assert result.agent_type == "code_execution"

        # Metadata should indicate code execution capabilities
        assert "capabilities" in result.metadata
        assert "code_execution" in result.metadata["capabilities"]

    @pytest.mark.asyncio
    async def test_default_tool_configuration(self) -> None:
        """Test agent with default tool configuration."""
        # Config without explicit tool settings
        config = MemberAgentConfig(
            name="default-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="anthropic:claude-sonnet-4-5-20250929",  # Code execution requires Anthropic
            system_instruction="Default code execution instructions.",
        )

        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(config)

        # Should have default tool settings (tool_settings itself may be None)
        assert agent.config.tool_settings is None or agent.config.tool_settings.code_execution is None
        # Agent should still be functional with defaults
        assert agent.agent_name == "default-code-agent"

    @pytest.mark.asyncio
    async def test_security_constraints_documentation(self, code_execution_agent_config: MemberAgentConfig) -> None:
        """Test that security constraints are properly documented."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent

        agent = CodeExecutionMemberAgent(code_execution_agent_config)

        # Security constraints should be documented in tool config
        assert agent.config.tool_settings is not None
        tool_config = agent.config.tool_settings.code_execution
        assert tool_config is not None
        assert tool_config.provider_controlled is True
        assert tool_config.expected_network_access is False
        assert tool_config.expected_min_timeout_seconds == 300

        # Expected modules should be documented
        expected_modules = tool_config.expected_available_modules
        assert "pandas" in expected_modules
        assert "numpy" in expected_modules
        assert "matplotlib" in expected_modules


class TestCodeExecutionProviderValidation:
    """Test provider validation for code execution (Anthropic Claude only)."""

    def test_rejects_google_ai_models(self) -> None:
        """Test that Google AI models are rejected with clear error message."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
        from mixseek.models.member_agent import AgentType, MemberAgentConfig

        config = MemberAgentConfig(
            name="test-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="google-gla:gemini-2.5-flash-lite",  # ❌ Not supported
            system_instruction="Test agent for code execution",
        )

        with pytest.raises(ValueError) as exc_info:
            CodeExecutionMemberAgent(config)

        error_message = str(exc_info.value).lower()
        assert "only supports anthropic claude" in error_message
        assert "google ai" in error_message or "not supported" in error_message
        assert "anthropic:" in error_message

    def test_rejects_vertex_ai_models(self) -> None:
        """Test that Vertex AI models are rejected with clear error message."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
        from mixseek.models.member_agent import AgentType, MemberAgentConfig

        config = MemberAgentConfig(
            name="test-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="google-gla:gemini-2.5-flash-lite",  # ❌ Not supported (Vertex AI uses same prefix)
            system_instruction="Test agent for code execution",
        )

        with pytest.raises(ValueError) as exc_info:
            CodeExecutionMemberAgent(config)

        error_message = str(exc_info.value)
        assert "only supports Anthropic Claude" in error_message
        assert "400 INVALID_ARGUMENT" in error_message or "Not supported" in error_message

    def test_rejects_openai_models(self) -> None:
        """Test that OpenAI models are rejected with clear error message."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
        from mixseek.models.member_agent import AgentType, MemberAgentConfig

        config = MemberAgentConfig(
            name="test-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="openai:gpt-4o",  # ❌ Not supported
            system_instruction="Test agent for code execution",
        )

        with pytest.raises(ValueError) as exc_info:
            CodeExecutionMemberAgent(config)

        error_message = str(exc_info.value)
        assert "only supports Anthropic Claude" in error_message
        assert "OpenAI" in error_message
        assert "CodeExecutionTool not available" in error_message or "Not supported" in error_message

    @patch("mixseek.agents.member.code_execution.Agent")
    @patch("mixseek.agents.member.code_execution.create_authenticated_model")
    def test_accepts_anthropic_models(self, mock_create_model: Any, mock_agent_class: Any) -> None:
        """Test that Anthropic Claude models are accepted."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
        from mixseek.models.member_agent import AgentType, MemberAgentConfig

        # Mock the model creation
        mock_model = MagicMock()
        mock_create_model.return_value = mock_model

        # Mock the Agent class
        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        config = MemberAgentConfig(
            name="test-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="anthropic:claude-sonnet-4-5-20250929",  # ✅ Supported
            system_instruction="Test agent for code execution",
        )

        # Should not raise ValueError
        agent = CodeExecutionMemberAgent(config)

        # Verify agent was created successfully
        assert agent.agent_name == "test-code-agent"
        assert agent.config.model == "anthropic:claude-sonnet-4-5-20250929"

        # Verify authentication was called
        mock_create_model.assert_called_once_with("anthropic:claude-sonnet-4-5-20250929")

        # Verify Agent class was instantiated
        assert mock_agent_class.called

    def test_error_message_includes_documentation_references(self) -> None:
        """Test that error message includes helpful documentation references."""
        from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
        from mixseek.models.member_agent import AgentType, MemberAgentConfig

        config = MemberAgentConfig(
            name="test-code-agent",
            type=AgentType.CODE_EXECUTION,
            model="google-gla:gemini-2.5-flash-lite",  # ❌ Not supported
            system_instruction="Test agent for code execution",
        )

        with pytest.raises(ValueError) as exc_info:
            CodeExecutionMemberAgent(config)

        error_message = str(exc_info.value)
        # Should reference specification and findings
        assert "spec.md" in error_message or "specification" in error_message.lower()
        assert "ANTHROPIC_API_KEY" in error_message
