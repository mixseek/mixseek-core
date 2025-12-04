"""Unit tests for Member Agent configuration models.

This test suite validates the Pydantic models for Member Agent configurations,
including validation rules, error handling, and field constraints.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the full implementation to ensure proper validation and error handling.
"""

from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from mixseek.models.member_agent import (
    MAX_TOKENS_LOWER_BOUND,
    AgentType,
    EnvironmentConfig,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
)


class TestAgentType:
    """Test AgentType enum values and behavior."""

    def test_agent_type_enum_values(self) -> None:
        """Test AgentType enum has correct values."""
        assert AgentType.PLAIN.value == "plain"
        assert AgentType.WEB_SEARCH.value == "web_search"
        assert AgentType.CODE_EXECUTION.value == "code_execution"

    def test_agent_type_str_conversion(self) -> None:
        """Test AgentType converts to string correctly."""
        assert str(AgentType.PLAIN) == "plain"
        assert str(AgentType.WEB_SEARCH) == "web_search"
        assert str(AgentType.CODE_EXECUTION) == "code_execution"


class TestMemberAgentConfig:
    """Test MemberAgentConfig model validation and behavior."""

    def get_valid_config_data(self) -> dict[str, Any]:
        """Get valid configuration data for testing."""
        return {
            "name": "test-agent",
            "type": AgentType.PLAIN,
            "model": "google-gla:gemini-2.5-flash-lite",
            "system_instruction": "Test system_instruction with minimum length.",
        }

    def test_valid_plain_agent_config(self) -> None:
        """Test valid plain agent configuration."""
        config_data = self.get_valid_config_data()
        config = MemberAgentConfig(**config_data)

        assert config.name == "test-agent"
        assert config.type == AgentType.PLAIN
        assert config.model == "google-gla:gemini-2.5-flash-lite"
        assert config.temperature is None  # Default (uses model default)
        assert config.max_tokens is None  # Default (uses model default)

    def test_model_validation_supported_providers(self) -> None:
        """Test model validation accepts Google Gemini and OpenAI models."""
        config_data = self.get_valid_config_data()

        # Valid Google Gemini models
        valid_google_models = [
            "google-gla:gemini-2.5-flash-lite",
            "google-gla:gemini-2.5-flash-lite",
            "google-gla:gemini-2.0-flash",
        ]

        for model in valid_google_models:
            config_data["model"] = model
            config = MemberAgentConfig(**config_data)
            assert config.model == model

        # Valid OpenAI models
        valid_openai_models = ["openai:gpt-4o", "openai:gpt-4o-mini", "openai:gpt-4-turbo"]

        for model in valid_openai_models:
            config_data["model"] = model
            config = MemberAgentConfig(**config_data)
            assert config.model == model

        # Valid Anthropic models
        valid_anthropic_models = [
            "anthropic:claude-3-5-sonnet-20241022",
            "anthropic:claude-3-5-haiku-20241022",
            "anthropic:claude-3-opus-20240229",
        ]

        for model in valid_anthropic_models:
            config_data["model"] = model
            config = MemberAgentConfig(**config_data)
            assert config.model == model

        # Invalid models
        invalid_models = [
            "gpt-4",  # Missing prefix
            "gemini-2.5-flash-lite",  # Missing prefix
            "claude-3-sonnet",  # Missing prefix
            "invalid:model",  # Unsupported provider
            "unsupported:model",  # Unsupported provider
        ]

        for model in invalid_models:
            config_data["model"] = model
            with pytest.raises(ValidationError, match="Unsupported model"):
                MemberAgentConfig(**config_data)

    def test_agent_name_validation(self) -> None:
        """Test agent name validation rules."""
        config_data = self.get_valid_config_data()

        # Valid names
        valid_names = ["test-agent", "data_analyst", "agent.v1", "MyAgent123", "simple"]

        for name in valid_names:
            config_data["name"] = name
            config = MemberAgentConfig(**config_data)
            assert config.name == name

        # Invalid names
        invalid_names = [
            "agent with spaces",
            "agent@domain.com",
            "agent#1",
            "agent/path",
            "",
        ]

        for name in invalid_names:
            config_data["name"] = name
            with pytest.raises(ValidationError, match="Invalid agent name"):
                MemberAgentConfig(**config_data)

    def test_temperature_bounds_validation(self) -> None:
        """Test temperature parameter bounds validation."""
        config_data = self.get_valid_config_data()

        # Valid bounds
        config_data["temperature"] = 0.0
        config = MemberAgentConfig(**config_data)
        assert config.temperature == 0.0

        config_data["temperature"] = 2.0
        config = MemberAgentConfig(**config_data)
        assert config.temperature == 2.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            config_data["temperature"] = -0.1
            MemberAgentConfig(**config_data)

        with pytest.raises(ValidationError):
            config_data["temperature"] = 2.1
            MemberAgentConfig(**config_data)

    def test_max_tokens_bounds_validation(self) -> None:
        """Test max_tokens parameter bounds validation."""
        config_data = self.get_valid_config_data()

        # Valid bounds
        config_data["max_tokens"] = MAX_TOKENS_LOWER_BOUND
        config = MemberAgentConfig(**config_data)
        assert config.max_tokens == MAX_TOKENS_LOWER_BOUND

        # max_tokens can be None or any positive value (no upper bound)
        config_data["max_tokens"] = None
        config = MemberAgentConfig(**config_data)
        assert config.max_tokens is None

        config_data["max_tokens"] = 100000
        config = MemberAgentConfig(**config_data)
        assert config.max_tokens == 100000

        # Invalid bounds (must be > 0)
        with pytest.raises(ValidationError):
            config_data["max_tokens"] = 0
            MemberAgentConfig(**config_data)

        with pytest.raises(ValidationError):
            config_data["max_tokens"] = -1
            MemberAgentConfig(**config_data)

    def test_required_fields_validation(self) -> None:
        """Test required fields are validated."""
        # Missing name
        with pytest.raises(ValidationError, match="Field required"):
            MemberAgentConfig(type=AgentType.PLAIN, system_instruction="Test instructions.")  # type: ignore[call-arg]

        # Missing type
        with pytest.raises(ValidationError, match="Field required"):
            MemberAgentConfig(name="test", system_instruction="Test instructions.")  # type: ignore[call-arg]

        # Note: model has a default value, so it's no longer required
        # system_instruction is also optional (str | None = None)
        # Only name and type are truly required
        config = MemberAgentConfig(name="test", type=AgentType.PLAIN)
        assert config.model == "google-gla:gemini-2.5-flash-lite"  # Uses default
        assert config.system_instruction is None  # Uses default None

    def test_system_instruction_string_format(self) -> None:
        """Test system_instruction accepts string format (recommended)."""
        config = MemberAgentConfig(
            name="test-agent",
            type=AgentType.PLAIN,
            system_instruction="You are a helpful assistant.",
        )
        assert config.system_instruction == "You are a helpful assistant."

    def test_system_instruction_dict_format(self) -> None:
        """Test system_instruction accepts dict format for future extensibility.

        The dict format allows future extensions like:
        - lang: Language specification (e.g., 'ja', 'en')
        - template: Whether to process as template with variables
        - metadata: Additional configuration
        """
        config = MemberAgentConfig(
            name="test-agent",
            type=AgentType.PLAIN,
            system_instruction={"text": "You are a helpful assistant."},  # type: ignore[arg-type]
        )
        # Dict format is normalized to string
        assert config.system_instruction == "You are a helpful assistant."

    def test_system_instruction_dict_with_extra_fields(self) -> None:
        """Test dict format preserves only text field (future fields are ignored for now)."""
        config = MemberAgentConfig(
            name="test-agent",
            type=AgentType.PLAIN,
            system_instruction={  # type: ignore[arg-type]
                "text": "あなたは親切なアシスタントです。",
                "lang": "ja",  # Future: language specification
                "template": False,  # Future: template processing flag
            },
        )
        # Only text is extracted, other fields are for future use
        assert config.system_instruction == "あなたは親切なアシスタントです。"

    def test_system_instruction_none(self) -> None:
        """Test system_instruction accepts None."""
        config = MemberAgentConfig(
            name="test-agent",
            type=AgentType.PLAIN,
            system_instruction=None,
        )
        assert config.system_instruction is None

    def test_system_instruction_invalid_dict_without_text(self) -> None:
        """Test dict format without 'text' key raises error."""
        with pytest.raises(ValidationError, match="system_instruction must be str or dict with 'text' key"):
            MemberAgentConfig(
                name="test-agent",
                type=AgentType.PLAIN,
                system_instruction={"lang": "ja"},  # type: ignore[arg-type]
            )

    def test_system_instruction_invalid_type(self) -> None:
        """Test invalid types raise error."""
        with pytest.raises(ValidationError, match="system_instruction must be str or dict with 'text' key"):
            MemberAgentConfig(
                name="test-agent",
                type=AgentType.PLAIN,
                system_instruction=123,  # type: ignore[arg-type]
            )

    def test_system_instruction_dict_text_not_string(self) -> None:
        """Test dict format with non-string text raises error."""
        with pytest.raises(ValidationError, match="system_instruction.text must be str"):
            MemberAgentConfig(
                name="test-agent",
                type=AgentType.PLAIN,
                system_instruction={"text": 123},  # type: ignore[arg-type]
            )


class TestEnvironmentConfig:
    """Test EnvironmentConfig model validation and environment variable handling."""

    def test_environment_config_defaults(self) -> None:
        """Test environment config default values."""
        config = EnvironmentConfig()
        assert config.development_mode is False
        assert config.log_level == "INFO"
        assert config.cli_output_format == "structured"
        assert config.google_genai_use_vertexai is False

    @patch.dict("os.environ", {"MIXSEEK_DEVELOPMENT_MODE": "true", "MIXSEEK_LOG_LEVEL": "DEBUG"}, clear=False)
    def test_environment_variable_override(self) -> None:
        """Test environment variables override defaults."""
        config = EnvironmentConfig()
        assert config.development_mode is True
        assert config.log_level == "DEBUG"

    @patch.dict(
        "os.environ", {"MIXSEEK_CLI_OUTPUT_FORMAT": "json", "MIXSEEK_GOOGLE_GENAI_USE_VERTEXAI": "true"}, clear=False
    )
    def test_environment_variable_types(self) -> None:
        """Test environment variable type conversion."""
        config = EnvironmentConfig()
        assert config.cli_output_format == "json"
        assert config.google_genai_use_vertexai is True


class TestResultStatus:
    """Test ResultStatus enum values."""

    def test_result_status_enum_values(self) -> None:
        """Test ResultStatus enum has correct values."""
        assert ResultStatus.SUCCESS.value == "success"
        assert ResultStatus.ERROR.value == "error"
        assert ResultStatus.WARNING.value == "warning"


class TestMemberAgentResult:
    """Test MemberAgentResult model and factory methods."""

    def test_success_result_creation(self) -> None:
        """Test successful result creation."""
        result = MemberAgentResult.success(
            content="Test response", agent_name="test-agent", agent_type="plain", execution_time_ms=1500
        )

        assert result.status == ResultStatus.SUCCESS
        assert result.content == "Test response"
        assert result.agent_name == "test-agent"
        assert result.agent_type == "plain"
        assert result.execution_time_ms == 1500
        assert result.error_message is None
        assert result.retry_count == 0
        assert result.is_success() is True
        assert result.is_error() is False

    def test_error_result_creation(self) -> None:
        """Test error result creation."""
        result = MemberAgentResult.error(
            error_message="API call failed",
            agent_name="test-agent",
            agent_type="plain",
            error_code="API_ERROR",
            retry_count=3,
            max_retries_exceeded=True,
        )

        assert result.status == ResultStatus.ERROR
        assert result.content == ""  # No content on error
        assert result.error_message == "API call failed"
        assert result.error_code == "API_ERROR"
        assert result.retry_count == 3
        assert result.max_retries_exceeded is True
        assert result.is_success() is False
        assert result.is_error() is True

    def test_result_metadata_handling(self) -> None:
        """Test result metadata is properly handled."""
        metadata = {"model_id": "gemini-2.5-flash-lite", "tokens_used": 150}

        result = MemberAgentResult.success(
            content="Test response", agent_name="test-agent", agent_type="plain", metadata=metadata
        )

        assert result.metadata == metadata

    def test_result_timestamp_auto_generation(self) -> None:
        """Test timestamp is automatically generated."""
        result = MemberAgentResult.success(content="Test response", agent_name="test-agent", agent_type="plain")

        assert result.timestamp is not None
        # Should be recent timestamp
        import datetime

        now = datetime.datetime.now(datetime.UTC)
        time_diff = (now - result.timestamp).total_seconds()
        assert time_diff < 1.0  # Should be within 1 second
