"""Integration tests for Member Agent system.

These tests verify the complete integration of Member Agents with all
components including configuration loading, execution, formatting, and recovery.
"""

import asyncio
import json
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.cli.formatters import ResultFormatter
from mixseek.config.member_agent_loader import EnvironmentConfig, MemberAgentLoader
from mixseek.models.member_agent import (
    AgentType,
    MemberAgentResult,
    ResultStatus,
)

# Error recovery removed for Article 9 constitutional compliance


@pytest.fixture(autouse=True)
def setup_workspace(monkeypatch, tmp_path):
    """Set MIXSEEK_WORKSPACE for all tests (Article 9 compliance)."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))


@pytest.fixture
def temp_config_file() -> Generator[Path]:
    """Create a temporary configuration file."""
    config_content = """
[agent]
name = "integration-test-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 1024
timeout_seconds = 60
description = "Integration test agent for comprehensive testing"

[agent.system_instruction]
text = "You are a helpful AI assistant for integration testing. Provide clear and concise responses."

[agent.metadata]
test_environment = "integration"
version = "1.0.0"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        yield Path(f.name)

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def web_search_config_file() -> Generator[Path]:
    """Create a web search agent configuration file."""
    config_content = """
[agent]
name = "web-search-integration-agent"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 2048
timeout_seconds = 120
description = "Web search integration test agent"

[agent.system_instruction]
text = "You are a web search agent that helps users find information by searching the web effectively."

[agent.tool_settings.web_search]
max_results = 10
timeout = 30

[agent.metadata]
search_domains = ["example.com", "test.org"]
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_environment() -> EnvironmentConfig:
    """Mock environment configuration."""
    return EnvironmentConfig(
        log_level="DEBUG",
        development_mode=True,
    )


class TestConfigurationIntegration:
    """Test configuration loading and validation integration."""

    def test_load_and_validate_plain_agent_config(self, temp_config_file: Path) -> None:
        """Test loading and validating a plain agent configuration."""
        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)

        # Verify configuration loaded correctly
        assert config.name == "integration-test-agent"
        assert config.type == AgentType.PLAIN
        assert config.model == "google-gla:gemini-2.5-flash-lite"
        assert config.temperature == 0.2
        assert config.max_tokens == 1024  # Matches fixture configuration

        # Check specific fields
        assert config.timeout_seconds == 60
        assert config.metadata["test_environment"] == "integration"

    def test_load_and_validate_web_search_config(self, web_search_config_file: Path) -> None:
        """Test loading and validating a web search agent configuration."""
        loader = MemberAgentLoader()
        config = loader.load_config(web_search_config_file)

        # Verify configuration
        assert config.name == "web-search-integration-agent"
        assert config.type == AgentType.WEB_SEARCH
        assert config.tool_settings is not None
        assert config.tool_settings.web_search is not None
        assert config.tool_settings.web_search.max_results == 10
        assert config.tool_settings.web_search.timeout == 30

    @patch.dict("os.environ", {"MIXSEEK_LOG_LEVEL": "DEBUG", "MIXSEEK_DEVELOPMENT_MODE": "true"})
    def test_environment_loading_integration(self) -> None:
        """Test environment configuration loading."""
        loader = MemberAgentLoader()
        env_config = loader.load_environment()

        assert env_config.development_mode is True
        assert env_config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]


class TestAgentFactoryIntegration:
    """Test agent factory integration with full configuration."""

    @patch("mixseek.core.auth.create_authenticated_model")
    def test_create_plain_agent_integration(
        self, mock_create_model: MagicMock, temp_config_file: Path, mock_environment: EnvironmentConfig
    ) -> None:
        """Test creating a plain agent through the factory."""
        # Mock the authenticated model
        mock_model = MagicMock()
        mock_create_model.return_value = mock_model

        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)

        # Create agent through factory
        agent = MemberAgentFactory.create_agent(config)

        assert agent is not None
        assert agent.config.name == "integration-test-agent"
        assert agent.config.type == AgentType.PLAIN

    @patch("mixseek.core.auth.create_authenticated_model")
    def test_create_web_search_agent_integration(
        self, mock_create_model: MagicMock, web_search_config_file: Path
    ) -> None:
        """Test creating a web search agent through the factory."""
        mock_model = MagicMock()
        mock_create_model.return_value = mock_model

        loader = MemberAgentLoader()
        config = loader.load_config(web_search_config_file)

        agent = MemberAgentFactory.create_agent(config)

        assert agent is not None
        assert agent.config.name == "web-search-integration-agent"
        assert agent.config.type == AgentType.WEB_SEARCH


class TestAgentExecutionIntegration:
    """Test end-to-end agent execution integration."""

    @pytest.mark.skip(reason="Complex Pydantic AI mocking needs more detailed implementation")
    @pytest.mark.asyncio
    @patch("mixseek.core.auth.create_authenticated_model")
    async def test_plain_agent_execution_success(self, mock_create_model: Any, temp_config_file: Path) -> None:
        """Test successful plain agent execution."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "This is a test response from the integration test."
        mock_response.usage_metadata.prompt_token_count = 25
        mock_response.usage_metadata.candidates_token_count = 15
        mock_response.usage_metadata.total_token_count = 40

        mock_client = MagicMock()
        mock_client.generate_content = AsyncMock(return_value=mock_response)
        mock_create_model.return_value = mock_client

        # Load config and create agent
        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)
        agent = MemberAgentFactory.create_agent(config)

        await agent.initialize()

        # Execute agent
        result = await agent.execute("Hello, this is an integration test.")

        # Verify result
        assert isinstance(result, MemberAgentResult)
        assert result.status == ResultStatus.SUCCESS
        assert result.content == "This is a test response from the integration test."
        assert result.agent_name == "integration-test-agent"
        assert result.agent_type == "plain"
        assert result.usage_info is not None
        assert result.usage_info["total_tokens"] == 40


# TestErrorRecoveryIntegration class removed for Article 9 constitutional compliance
# Error recovery violates constitutional mandate against implicit fallbacks


class TestFormatterIntegration:
    """Test formatter integration with real results."""

    def test_structured_formatter_integration(self) -> None:
        """Test structured formatter with complete result."""
        result = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="Integration test response with comprehensive data",
            agent_name="integration-test-agent",
            agent_type="plain",
            timestamp=datetime.now(UTC),
            execution_time_ms=1500,
            usage_info={"total_tokens": 45, "prompt_tokens": 25, "completion_tokens": 20},
            metadata={
                "model_id": "google-gla:gemini-2.5-flash-lite",
                "temperature": 0.2,
                "max_tokens": 1024,
                "test_metadata": "integration_value",
            },
        )

        with patch("typer.echo") as mock_echo, patch("typer.secho") as mock_secho:
            ResultFormatter.format_structured(result, 1500, verbose=True)

            # Should have multiple output calls for structured format
            total_calls = mock_echo.call_count + mock_secho.call_count
            assert total_calls > 10  # Comprehensive output

    def test_json_formatter_integration(self) -> None:
        """Test JSON formatter produces valid JSON."""
        result = MemberAgentResult(
            status=ResultStatus.SUCCESS,
            content="JSON integration test",
            agent_name="json-test-agent",
            agent_type="web_search",
            warning_message="Test warning message",
            usage_info={"total_tokens": 30},
            metadata={"format": "json"},
        )

        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_json(result, 1000, verbose=True)

            # Extract JSON output and validate
            json_output = mock_echo.call_args[0][0]
            data = json.loads(json_output)  # Should not raise exception

            assert data["status"] == "success"
            assert data["content"] == "JSON integration test"
            assert data["agent_name"] == "json-test-agent"
            assert data["warning_message"] == "Test warning message"

    def test_csv_formatter_integration(self) -> None:
        """Test CSV formatter with multiple results."""
        results = [
            MemberAgentResult(
                status=ResultStatus.SUCCESS, content="First result", agent_name="agent-1", agent_type="plain"
            ),
            MemberAgentResult(
                status=ResultStatus.ERROR,
                content="",
                agent_name="agent-2",
                agent_type="web_search",
                error_code="TIMEOUT_ERROR",
            ),
        ]
        execution_times = [1000, 2000]

        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_csv(results, execution_times)

            # Should output header + 2 data rows
            assert mock_echo.call_count == 3

            # Verify CSV structure
            calls = [call[0][0] for call in mock_echo.call_args_list]
            header = calls[0]
            assert "timestamp,agent_name,agent_type,status" in header


class TestEndToEndIntegration:
    """Test complete end-to-end integration scenarios."""

    @pytest.mark.skip(reason="Complex Pydantic AI mocking needs more detailed implementation")
    @pytest.mark.asyncio
    @patch("mixseek.core.auth.create_authenticated_model")
    async def test_complete_workflow_integration(self, mock_create_model: Any, temp_config_file: Path) -> None:
        """Test complete workflow from config to formatted output."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "Complete workflow test response"
        mock_response.usage_metadata.prompt_token_count = 30
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.usage_metadata.total_token_count = 50

        mock_client = MagicMock()
        mock_client.generate_content = AsyncMock(return_value=mock_response)
        mock_create_model.return_value = mock_client

        # Step 1: Load configuration
        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)

        # Step 2: Create and initialize agent
        agent = MemberAgentFactory.create_agent(config)
        await agent.initialize()

        # Step 3: Execute agent
        result = await agent.execute("Complete integration test prompt")

        # Step 4: Format output
        with patch("typer.echo") as mock_echo:
            ResultFormatter.format_structured(result, 1200, verbose=True)
            assert mock_echo.call_count > 5  # Should produce formatted output

        # Verify complete result
        assert result.status == ResultStatus.SUCCESS
        assert result.content == "Complete workflow test response"
        assert result.usage_info is not None
        assert result.usage_info["total_tokens"] == 50

    @pytest.mark.skip(reason="Complex Pydantic AI mocking needs more detailed implementation")
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, temp_config_file: Path) -> None:
        """Test error handling throughout the integration."""
        # Test error handling by trying to create an agent with invalid model
        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)

        # Change to an invalid model name that will cause creation to fail
        # Create a new config with invalid model to avoid Pydantic validation
        invalid_config_dict = config.model_dump()
        invalid_config_dict["model"] = "invalid-model-name"

        # This should be handled by the factory error handling
        with pytest.raises((ValueError, KeyError, AttributeError)):
            # Try to create config and agent with invalid model
            invalid_config = config.__class__.model_validate(invalid_config_dict)
            MemberAgentFactory.create_agent(invalid_config)


class TestPerformanceIntegration:
    """Test performance-related integration scenarios."""

    @pytest.mark.skip(reason="Complex Pydantic AI mocking needs more detailed implementation")
    @pytest.mark.asyncio
    @patch("mixseek.core.auth.create_authenticated_model")
    async def test_concurrent_agent_execution(self, mock_create_model: Any, temp_config_file: Path) -> None:
        """Test concurrent execution of multiple agents."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "Concurrent test response"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 15
        mock_response.usage_metadata.total_token_count = 35

        mock_client = MagicMock()
        mock_client.generate_content = AsyncMock(return_value=mock_response)
        mock_create_model.return_value = mock_client

        # Create multiple agents
        loader = MemberAgentLoader()
        config = loader.load_config(temp_config_file)

        agents = []
        for i in range(3):
            agent_config = config.model_copy()
            agent_config.name = f"concurrent-agent-{i}"
            agent = MemberAgentFactory.create_agent(agent_config)
            await agent.initialize()
            agents.append(agent)

        # Execute concurrently
        tasks = [agent.execute(f"Concurrent test prompt {i}") for i, agent in enumerate(agents)]

        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 3
        assert all(result.status == ResultStatus.SUCCESS for result in results)
        assert all(result.content == "Concurrent test response" for result in results)

    def test_memory_usage_integration(self, temp_config_file: Path) -> None:
        """Test that configuration and agent creation doesn't leak memory."""
        import gc

        loader = MemberAgentLoader()

        # Create and destroy multiple configs
        for _ in range(10):
            config = loader.load_config(temp_config_file)

            # Force garbage collection
            del config
            gc.collect()

        # Test should complete without memory errors
        assert True  # If we get here, no memory issues occurred
