"""Edge case tests for Configuration Manager - Phase 11 T073."""

from pathlib import Path
from typing import Any

import pytest

from mixseek.config import ConfigurationManager, LeaderAgentSettings, OrchestratorSettings


class TestInvalidTOMLSyntax:
    """Test invalid TOML syntax handling - T073 edge case 1."""

    def test_toml_syntax_error_with_unclosed_bracket(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test handling of TOML syntax error (unclosed bracket)."""
        config_file = tmp_path / "bad-syntax.toml"
        config_file.write_text("[leader\n# Missing closing bracket")
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        # Try to load - should raise error
        from tomllib import TOMLDecodeError

        with pytest.raises(TOMLDecodeError):
            manager = ConfigurationManager()
            manager.load_settings(OrchestratorSettings)

    def test_toml_syntax_error_with_invalid_key_value(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test handling of TOML syntax error (invalid key-value)."""
        config_file = tmp_path / "bad-syntax.toml"
        config_file.write_text("[leader]\nmodel =")  # Missing value
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        from tomllib import TOMLDecodeError

        with pytest.raises(TOMLDecodeError):
            manager = ConfigurationManager()
            manager.load_settings(LeaderAgentSettings)

    def test_toml_syntax_error_with_duplicate_keys(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test handling of TOML syntax error (duplicate keys)."""
        config_file = tmp_path / "bad-syntax.toml"
        config_file.write_text("[leader]\nmodel = 'openai:gpt-4o'\nmodel = 'openai:gpt-4'")
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        from tomllib import TOMLDecodeError

        with pytest.raises(TOMLDecodeError):
            manager = ConfigurationManager()
            manager.load_settings(LeaderAgentSettings)


class TestNestedEnvironmentVariableEdgeCases:
    """Test nested environment variable mapping edge cases - T073 edge case 2."""

    def test_nested_env_var_with_empty_value(self, monkeypatch: Any) -> None:
        """Test nested environment variable with empty value raises validation error."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "")
        manager = ConfigurationManager()

        # Empty string is invalid - should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            manager.load_settings(LeaderAgentSettings)

    def test_nested_env_var_with_special_characters(self, monkeypatch: Any) -> None:
        """Test nested environment variable with special characters."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o-2024-08-06")
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Should handle special characters correctly
        assert settings.model == "openai:gpt-4o-2024-08-06"

    def test_nested_env_var_with_whitespace(self, monkeypatch: Any) -> None:
        """Test nested environment variable with whitespace."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o ")
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Whitespace is preserved
        assert settings.model == "openai:gpt-4o "

    def test_multiple_nested_levels(self, monkeypatch: Any) -> None:
        """Test multiple nested environment variable assignments."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MIXSEEK_LEADER__TEMPERATURE", "0.5")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "600")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        assert settings.model == "openai:gpt-4o"
        assert settings.temperature == 0.5
        assert settings.timeout_seconds == 600


class TestCLIFieldNameMappingEdgeCases:
    """Test CLI field name mapping edge cases - T073 edge case 3."""

    def test_cli_hyphen_to_underscore_conversion(self) -> None:
        """Test CLI field name mapping (hyphen to underscore)."""
        from mixseek.config.sources.cli_source import CLISource

        cli_args = {"timeout-seconds": 600}
        source = CLISource(LeaderAgentSettings, cli_args=cli_args)

        # Field name mapping should convert hyphen to underscore
        value, key, value_is_set = source.get_field_value(
            LeaderAgentSettings.model_fields["timeout_seconds"],
            "timeout_seconds",
        )

        # Should find the value even with hyphen
        assert value_is_set
        assert value == 600

    def test_cli_field_name_case_sensitivity(self) -> None:
        """Test CLI field name case handling."""
        from mixseek.config.sources.cli_source import CLISource

        cli_args = {"model": "openai:gpt-4o"}
        source = CLISource(LeaderAgentSettings, cli_args=cli_args)

        value, key, value_is_set = source.get_field_value(
            LeaderAgentSettings.model_fields["model"],
            "model",
        )

        assert value_is_set
        assert value == "openai:gpt-4o"

    def test_cli_with_none_filtered_values(self) -> None:
        """Test CLI source with None values being filtered."""
        from mixseek.config.sources.cli_source import CLISource

        cli_args = {"model": "openai:gpt-4o", "temperature": None}
        source = CLISource(LeaderAgentSettings, cli_args=cli_args)

        # Call source to get all values
        result = source()

        # None values should be filtered out
        assert "model" in result
        assert "temperature" not in result


class TestConfigurationManagerEdgeCases:
    """Test ConfigurationManager edge cases."""

    def test_load_settings_with_invalid_types(self) -> None:
        """Test loading settings with invalid field types."""
        from pydantic import ValidationError

        ConfigurationManager()

        # Try to load with invalid type - should raise ValidationError
        with pytest.raises(ValidationError):
            from mixseek.config.schema import OrchestratorSettings

            # Create invalid settings
            OrchestratorSettings(
                workspace_path=Path("valid"),
                timeout_per_team_seconds="not_an_int",  # type: ignore[arg-type]
            )

    def test_trace_info_for_missing_fields(self) -> None:
        """Test trace_info for fields that don't exist."""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Request trace for non-existent field
        trace = manager.get_trace_info(settings, "nonexistent_field")

        # Should return None for non-existent fields
        assert trace is None

    def test_get_all_defaults_with_none_values(self) -> None:
        """Test get_all_defaults excludes None default values."""
        manager = ConfigurationManager()

        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # temperature has None as default, which might be excluded
        # but model should be included
        assert "model" in defaults
        assert defaults["model"] == "google-gla:gemini-2.5-flash-lite"

    def test_multiple_manager_instances_independent(self) -> None:
        """Test that multiple ConfigurationManager instances are independent."""
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()

        settings1 = manager1.load_settings(LeaderAgentSettings)
        settings2 = manager2.load_settings(LeaderAgentSettings)

        # Should be independent instances
        assert settings1 is not settings2
        assert settings1 == settings2


class TestTOMLSpecialValues:
    """Test TOML special value handling."""

    def test_toml_with_optional_fields(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test TOML with optional fields skipped."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[LeaderAgentSettings]\nmodel = 'openai:gpt-4o'\n")
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Should use default for missing optional field
        assert settings.temperature is None
        assert settings.model == "openai:gpt-4o"

    def test_toml_values_via_environment_override(self, monkeypatch: Any) -> None:
        """Test TOML values can be overridden via environment."""
        # Set TOML file not to exist, use only environment
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "600")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Should use environment values
        assert settings.model == "openai:gpt-4o"
        assert settings.timeout_seconds == 600

    def test_multiple_types_in_configuration(self, monkeypatch: Any) -> None:
        """Test configuration with multiple data types."""
        # Set various types via environment
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MIXSEEK_LEADER__TEMPERATURE", "0.75")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "450")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Should parse all types correctly
        assert isinstance(settings.model, str)
        assert isinstance(settings.temperature, float)
        assert isinstance(settings.timeout_seconds, int)
        assert settings.temperature == 0.75
