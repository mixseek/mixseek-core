"""Unit tests for CLISource configuration source."""

from pydantic import Field
from pydantic_settings import BaseSettings

from mixseek.config.sources.cli_source import CLISource


class TestCLISource:
    """CLISourceのテスト"""

    def test_get_field_value_with_matching_cli_args(self) -> None:
        """Test get_field_value() with matching CLI args"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")

        cli_args = {"model": "openai:gpt-4o"}
        source = CLISource(settings_cls=TestSettings, cli_args=cli_args)

        # Get field info
        field_info = TestSettings.model_fields["model"]

        # Test retrieval
        value, key, value_is_set = source.get_field_value(field_info, "model")

        assert value == "openai:gpt-4o"
        assert key == "model"
        assert value_is_set is True

    def test_get_field_value_with_no_matching_cli_args(self) -> None:
        """Test get_field_value() with no matching CLI args"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")

        cli_args: dict[str, object] = {}
        source = CLISource(settings_cls=TestSettings, cli_args=cli_args)

        field_info = TestSettings.model_fields["model"]
        value, key, value_is_set = source.get_field_value(field_info, "model")

        assert value is None
        assert key == "model"
        assert value_is_set is False

    def test_field_name_mapping(self) -> None:
        """Test field name mapping (timeout_seconds → timeout-seconds)"""

        class TestSettings(BaseSettings):
            timeout_seconds: int = Field(default=300)

        # Test both underscore and hyphen formats
        cli_args_underscore = {"timeout_seconds": 600}
        source_underscore = CLISource(settings_cls=TestSettings, cli_args=cli_args_underscore)

        field_info = TestSettings.model_fields["timeout_seconds"]
        value, _, value_is_set = source_underscore.get_field_value(field_info, "timeout_seconds")

        assert value == 600
        assert value_is_set is True

        # Test hyphen format
        cli_args_hyphen = {"timeout-seconds": 900}
        source_hyphen = CLISource(settings_cls=TestSettings, cli_args=cli_args_hyphen)

        value, _, value_is_set = source_hyphen.get_field_value(field_info, "timeout_seconds")

        assert value == 900
        assert value_is_set is True

    def test_call_returns_all_cli_values(self) -> None:
        """Test __call__() returns all CLI values"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")
            temperature: float = Field(default=0.7)
            max_tokens: int = Field(default=2048)

        cli_args = {"model": "openai:gpt-4o", "temperature": 0.9, "max_tokens": 4096}
        source = CLISource(settings_cls=TestSettings, cli_args=cli_args)

        result = source()

        assert result == {"model": "openai:gpt-4o", "temperature": 0.9, "max_tokens": 4096}

    def test_none_value_handling(self) -> None:
        """Test None value handling"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")
            temperature: float | None = Field(default=None)

        # None values should be filtered out in __call__()
        cli_args = {"model": "openai:gpt-4o", "temperature": None}
        source = CLISource(settings_cls=TestSettings, cli_args=cli_args)

        result = source()

        # None values are excluded from result
        assert result == {"model": "openai:gpt-4o"}
        assert "temperature" not in result

    def test_empty_cli_args(self) -> None:
        """Test with empty CLI args"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")

        source = CLISource(settings_cls=TestSettings, cli_args={})

        result = source()

        # Empty CLI args should return empty dict
        assert result == {}

    def test_multiple_cli_args(self) -> None:
        """Test with multiple CLI args"""

        class TestSettings(BaseSettings):
            model: str = Field(default="default_model")
            temperature: float = Field(default=0.7)
            max_tokens: int = Field(default=2048)
            timeout_seconds: int = Field(default=300)

        cli_args = {
            "model": "anthropic:claude-sonnet-4",
            "temperature": 0.8,
            "max_tokens": 8192,
            "timeout-seconds": 600,  # Test hyphen format
        }
        source = CLISource(settings_cls=TestSettings, cli_args=cli_args)

        result = source()

        # Verify all args are processed correctly
        assert result["model"] == "anthropic:claude-sonnet-4"
        assert result["temperature"] == 0.8
        assert result["max_tokens"] == 8192
        assert result["timeout_seconds"] == 600
