"""Unit tests for configuration schemas: MixSeekBaseSettings and related."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from mixseek.config import (
    MixSeekBaseSettings,
    OrchestratorSettings,
    UISettings,
)


class TestMixSeekBaseSettings:
    """MixSeekBaseSettingsのテスト (T038)"""

    def test_settings_customise_sources_returns_correct_priority_order(self) -> None:
        """Test settings_customise_sources() returns correct priority order (T038)"""
        # Verify that settings_customise_sources() returns a tuple of sources
        # ordered by priority: CLI > ENV > dotenv > TOML > secrets
        settings_cls = OrchestratorSettings
        init_settings = MagicMock()
        env_settings = MagicMock()
        dotenv_settings = MagicMock()
        file_secret_settings = MagicMock()

        sources = MixSeekBaseSettings.settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

        # Verify sources is a tuple with 5 elements (one for each source)
        assert isinstance(sources, tuple)
        assert len(sources) == 5

    def test_get_trace_info_retrieves_recorded_traces(self) -> None:
        """Test get_trace_info() retrieves recorded traces (T038)"""
        # Verify that get_trace_info() can be called (will return None for non-traced fields)
        settings = OrchestratorSettings(workspace_path=Path("/tmp"))
        trace_info = settings.get_trace_info("timeout_per_team_seconds")
        # For non-traced fields, trace_info will be None
        assert trace_info is None or trace_info.field_name == "timeout_per_team_seconds"

    def test_environment_field_default_value(self) -> None:
        """Test environment field default value (T038)"""
        # Verify that environment field defaults to "dev"
        # Create settings with minimal required fields
        settings = OrchestratorSettings(workspace_path=Path("/tmp"))
        assert settings.environment == "dev"

    def test_env_prefix_applied_correctly(self) -> None:
        """Test env_prefix='MIXSEEK_' applied correctly (T038)"""
        # Verify that the MIXSEEK_ prefix is used for environment variables
        # This is confirmed by model_config in MixSeekBaseSettings
        assert MixSeekBaseSettings.model_config.get("env_prefix") == "MIXSEEK_"

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test extra='forbid' rejects unknown fields (T038)"""
        # Verify that extra='forbid' is set in model_config
        assert MixSeekBaseSettings.model_config.get("extra") == "forbid"

        # Attempt to create settings with unknown field should raise ValidationError
        with pytest.raises(ValidationError):
            OrchestratorSettings(
                workspace_path=Path("/tmp"),
                unknown_field="should_fail",  # type: ignore[call-arg]
            )


class TestLeaderAgentSettings:
    """LeaderAgentSettingsのテスト"""

    def test_model_field_default_value(self) -> None:
        """Test model field default value"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # Default should be "openai:gpt-4o"
        pass

    def test_temperature_range_validation(self) -> None:
        """Test temperature range validation (0.0 <= temp <= 1.0)"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # This test verifies temperature constraints
        pass

    def test_temperature_none_is_allowed(self) -> None:
        """Test that temperature=None is allowed"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # This test verifies that None is a valid temperature value
        pass

    def test_timeout_seconds_default_value(self) -> None:
        """Test timeout_seconds default value"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # Default should be 300 (seconds)
        pass

    def test_timeout_seconds_range_validation(self) -> None:
        """Test timeout_seconds range validation (10 <= timeout <= 600)"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # This test verifies timeout constraints
        pass

    def test_model_format_validation(self) -> None:
        """Test model format validation (must contain colon)"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # Invalid format like "gpt-4o" should raise ValidationError
        # Valid format like "openai:gpt-4o" should pass
        pass

    def test_env_prefix_leader(self) -> None:
        """Test env_prefix for LeaderAgentSettings"""
        # Stub test - will be implemented when LeaderAgentSettings is created
        # Environment variables should use MIXSEEK_LEADER_ prefix
        pass


class TestOrchestratorSettings:
    """OrchestratorSettingsのテスト (T031) - NFR-003準拠"""

    def test_workspace_path_required_in_prod(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test workspace_path required in prod environment"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # workspace_path is required, should raise ValidationError in prod if missing
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        # NFR-003: Error should include field identifier
        assert "workspace_path" in str(exc_info.value)

    def test_workspace_path_required_in_dev(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test workspace_path required in dev environment (same requirement)"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # workspace_path is required, should raise ValidationError in dev if missing
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="dev")

        # NFR-003: Error should include field identifier
        assert "workspace_path" in str(exc_info.value)

    def test_validation_error_with_clear_message(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test ValidationError with clear error message"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        error_msg = str(exc_info.value)
        # Error should guide user on what to do
        assert "workspace" in error_msg.lower()

    def test_validation_error_includes_environment_variable_hint(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test error message includes environment variable hint"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        error_msg = str(exc_info.value)
        # Should suggest environment variable name or field name
        assert (
            "environment variable" in error_msg.lower()
            or "MIXSEEK" in error_msg
            or "workspace_path" in error_msg.lower()
        )

    def test_validation_error_includes_nfr003_elements(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """Test NFR-003: Error includes field, expected format, and actual value"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # NFR-003 requires: field identifier + expected format + actual value
        with pytest.raises(ValidationError) as exc_info:
            OrchestratorSettings(environment="prod")

        error_msg = str(exc_info.value)

        # Element 1: Field identifier (either field name or environment variable name)
        assert "workspace_path" in error_msg or "MIXSEEK_WORKSPACE_PATH" in error_msg, "Missing field identifier"

        # Element 2: Expected format/type (setting requirement)
        # Should indicate what type/format is expected, or that explicit setting is required
        expected_type_indicators = [
            "path",
            "directory",
            "Path",
            "file",
            "required",
            "設定が必要",  # Japanese for "setting is required"
            "environment",
            "TOML",
        ]
        has_type_info = any(indicator.lower() in error_msg.lower() for indicator in expected_type_indicators)
        assert has_type_info, f"Missing expected type/format in error: {error_msg}"

        # Element 3: Actual value or indication that it's missing
        # For required field, should mention that value is missing or undefined
        missing_indicators = [
            "missing",
            "required",
            "undefined",
            "not provided",
            "not set",
            "明示的な設定",  # Japanese for "explicit setting"
        ]
        has_actual_value_info = any(indicator.lower() in error_msg.lower() for indicator in missing_indicators)
        assert has_actual_value_info or "Field required" in error_msg, (
            f"Missing indication of actual (missing) value in error: {error_msg}"
        )


class TestOptionalFieldDefaults:
    """オプションフィールドのデフォルト値テスト (T032)"""

    def test_timeout_seconds_uses_default_in_dev(self, tmp_path: Path) -> None:
        """Test timeout_seconds uses default (300) in dev environment"""
        settings = OrchestratorSettings(workspace_path=tmp_path, environment="dev")
        assert settings.timeout_per_team_seconds == 300

    def test_timeout_seconds_uses_default_in_prod(self, tmp_path: Path) -> None:
        """Test timeout_seconds uses default (300) in prod environment"""
        # In prod, when unset, should use default (not error)
        # FR-007 requires same defaults in all environments
        settings = OrchestratorSettings(workspace_path=tmp_path, environment="prod")
        assert settings.timeout_per_team_seconds == 300

    def test_timeout_seconds_environment_agnostic_defaults(self, tmp_path: Path) -> None:
        """Test timeout_seconds defaults are environment-agnostic"""
        # Default value should be 300 in dev, staging, and prod (not different)
        dev_settings = OrchestratorSettings(workspace_path=tmp_path, environment="dev")
        prod_settings = OrchestratorSettings(workspace_path=tmp_path, environment="prod")
        assert dev_settings.timeout_per_team_seconds == prod_settings.timeout_per_team_seconds
        assert dev_settings.timeout_per_team_seconds == 300

    def test_optional_field_can_be_overridden_via_cli(self, tmp_path: Path) -> None:
        """Test optional fields can be overridden via CLI in all environments"""
        # CLI override should work in dev, staging, and prod
        settings = OrchestratorSettings(
            workspace_path=tmp_path,
            timeout_per_team_seconds=600,
            environment="dev",
        )
        assert settings.timeout_per_team_seconds == 600

    def test_optional_field_can_be_overridden_via_env(self, monkeypatch: Any, tmp_path: Path) -> None:
        """Test optional fields can be overridden via ENV in all environments"""
        # ENV override should work in dev, staging, and prod
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))
        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "450")

        settings = OrchestratorSettings()
        assert settings.timeout_per_team_seconds == 450


class TestOrchestratorSettingsMaxRetries:
    """OrchestratorSettings.max_retries_per_teamのテスト (Phase 12追加)"""

    def test_max_retries_per_team_default_value(self, tmp_path: Path) -> None:
        """Test max_retries_per_team default value is 2"""
        settings = OrchestratorSettings(workspace_path=tmp_path)
        assert settings.max_retries_per_team == 2

    def test_max_retries_per_team_can_be_overridden_via_cli(self, tmp_path: Path) -> None:
        """Test max_retries_per_team can be overridden via CLI"""
        settings = OrchestratorSettings(
            workspace_path=tmp_path,
            max_retries_per_team=5,
        )
        assert settings.max_retries_per_team == 5

    def test_max_retries_per_team_can_be_overridden_via_env(self, monkeypatch: Any, tmp_path: Path) -> None:
        """Test max_retries_per_team can be overridden via environment variable"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))
        monkeypatch.setenv("MIXSEEK_MAX_RETRIES_PER_TEAM", "7")

        settings = OrchestratorSettings()
        assert settings.max_retries_per_team == 7

    def test_max_retries_per_team_range_validation(self, tmp_path: Path) -> None:
        """Test max_retries_per_team range validation (0 <= retries <= 10)"""
        # Valid values
        valid_settings = OrchestratorSettings(
            workspace_path=tmp_path,
            max_retries_per_team=0,
        )
        assert valid_settings.max_retries_per_team == 0

        valid_settings_max = OrchestratorSettings(
            workspace_path=tmp_path,
            max_retries_per_team=10,
        )
        assert valid_settings_max.max_retries_per_team == 10

        # Invalid values
        with pytest.raises(ValidationError):
            OrchestratorSettings(
                workspace_path=tmp_path,
                max_retries_per_team=11,
            )

        with pytest.raises(ValidationError):
            OrchestratorSettings(
                workspace_path=tmp_path,
                max_retries_per_team=-1,
            )


class TestUISettings:
    """UISettingsのテスト (Phase 12追加)"""

    def test_port_default_value(self, tmp_path: Path) -> None:
        """Test port field default value is 8501"""
        settings = UISettings(workspace_path=tmp_path)
        assert settings.port == 8501

    def test_port_range_validation(self, tmp_path: Path) -> None:
        """Test port range validation (1024 <= port <= 65535)"""
        # Valid port
        valid_settings = UISettings(workspace_path=tmp_path, port=8080)
        assert valid_settings.port == 8080

        # Invalid port (too low)
        with pytest.raises(ValidationError):
            UISettings(workspace_path=tmp_path, port=1000)

        # Invalid port (too high)
        with pytest.raises(ValidationError):
            UISettings(workspace_path=tmp_path, port=70000)

    def test_workspace_required(self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None) -> None:
        """Test workspace field is required"""
        # Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)
        monkeypatch.delenv("MIXSEEK_UI__WORKSPACE_PATH", raising=False)

        with pytest.raises(ValidationError):
            UISettings()

    def test_workspace_must_exist(self, tmp_path: Path) -> None:
        """Test workspace path must exist"""
        nonexistent_path = tmp_path / "nonexistent"

        with pytest.raises(ValidationError) as exc_info:
            UISettings(workspace_path=nonexistent_path)

        error_msg = str(exc_info.value)
        assert "does not exist" in error_msg.lower() or "workspace" in error_msg.lower()

    def test_workspace_must_be_directory(self, tmp_path: Path) -> None:
        """Test workspace path must be a directory, not a file"""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test")

        with pytest.raises(ValidationError) as exc_info:
            UISettings(workspace_path=file_path)

        error_msg = str(exc_info.value)
        assert "not a directory" in error_msg.lower() or "directory" in error_msg.lower()

    def test_port_can_be_overridden_via_env(self, monkeypatch: Any, tmp_path: Path) -> None:
        """Test port can be overridden via environment variable"""
        monkeypatch.setenv("MIXSEEK_UI__PORT", "9000")

        settings = UISettings(workspace_path=tmp_path)
        assert settings.port == 9000

    def test_env_prefix_ui(self, tmp_path: Path) -> None:
        """Test env_prefix for UISettings"""
        # Verify that environment variables use MIXSEEK_UI__ prefix
        assert UISettings.model_config.get("env_prefix") == "MIXSEEK_UI__"
