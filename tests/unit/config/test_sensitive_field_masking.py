"""Tests for sensitive field masking in configuration output.

Article 3 Compliance: Test-First Implementation
Article 9 Compliance: Explicit security policy for sensitive data
"""

from pathlib import Path

import pytest
from pydantic import Field

from mixseek.config.constants import (
    MASKED_VALUE,
    NON_SENSITIVE_FIELD_EXCEPTIONS,
    SENSITIVE_FIELD_PATTERNS,
)
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import MixSeekBaseSettings
from mixseek.config.views import ConfigViewService


class DummySettingsWithSensitiveFields(MixSeekBaseSettings):
    """Test settings class with sensitive fields."""

    model: str = Field(default="gemini-2.5-flash-lite", description="Model name")
    api_key: str = Field(default="secret-123", description="API Key")
    password: str = Field(default="my-password", description="Password")
    secret_token: str = Field(default="token-abc", description="Secret Token")
    workspace_path: Path = Field(default=Path("/tmp/test"), description="Workspace")


class TestSensitiveFieldPatterns:
    """Test sensitive field pattern constants."""

    def test_sensitive_patterns_defined(self) -> None:
        """SENSITIVE_FIELD_PATTERNS constant is defined."""
        assert isinstance(SENSITIVE_FIELD_PATTERNS, tuple)
        assert len(SENSITIVE_FIELD_PATTERNS) > 0
        assert "api_key" in SENSITIVE_FIELD_PATTERNS
        assert "password" in SENSITIVE_FIELD_PATTERNS
        assert "secret" in SENSITIVE_FIELD_PATTERNS
        assert "token" in SENSITIVE_FIELD_PATTERNS

    def test_masked_value_defined(self) -> None:
        """MASKED_VALUE constant is defined."""
        assert isinstance(MASKED_VALUE, str)
        assert len(MASKED_VALUE) > 0
        assert MASKED_VALUE == "[REDACTED]"

    def test_non_sensitive_exceptions_defined(self) -> None:
        """NON_SENSITIVE_FIELD_EXCEPTIONS constant is defined."""
        assert isinstance(NON_SENSITIVE_FIELD_EXCEPTIONS, tuple)
        assert len(NON_SENSITIVE_FIELD_EXCEPTIONS) > 0
        assert "max_tokens" in NON_SENSITIVE_FIELD_EXCEPTIONS


class TestIsSensitiveField:
    """Test _is_sensitive_field() helper method."""

    def test_detects_api_key(self) -> None:
        """Detects 'api_key' as sensitive."""
        assert ConfigViewService._is_sensitive_field("api_key") is True

    def test_detects_api_key_uppercase(self) -> None:
        """Detects 'API_KEY' as sensitive (case-insensitive)."""
        assert ConfigViewService._is_sensitive_field("API_KEY") is True

    def test_detects_password(self) -> None:
        """Detects 'password' as sensitive."""
        assert ConfigViewService._is_sensitive_field("password") is True

    def test_detects_secret_token(self) -> None:
        """Detects 'secret_token' as sensitive."""
        assert ConfigViewService._is_sensitive_field("secret_token") is True

    def test_detects_private_key(self) -> None:
        """Detects 'private_key' as sensitive."""
        assert ConfigViewService._is_sensitive_field("private_key") is True

    def test_detects_credential(self) -> None:
        """Detects 'credential' as sensitive."""
        assert ConfigViewService._is_sensitive_field("credential") is True

    def test_non_sensitive_field(self) -> None:
        """Detects 'model' as non-sensitive."""
        assert ConfigViewService._is_sensitive_field("model") is False

    def test_non_sensitive_workspace_path(self) -> None:
        """Detects 'workspace_path' as non-sensitive."""
        assert ConfigViewService._is_sensitive_field("workspace_path") is False

    def test_max_tokens_not_masked(self) -> None:
        """Detects 'max_tokens' as non-sensitive (exception list)."""
        assert ConfigViewService._is_sensitive_field("max_tokens") is False

    def test_auth_token_still_masked(self) -> None:
        """Detects 'auth_token' as sensitive (not in exception list)."""
        assert ConfigViewService._is_sensitive_field("auth_token") is True

    def test_access_token_still_masked(self) -> None:
        """Detects 'access_token' as sensitive (not in exception list)."""
        assert ConfigViewService._is_sensitive_field("access_token") is True


class TestMaskValue:
    """Test _mask_value() helper method."""

    def test_masks_sensitive_field(self) -> None:
        """Masks value of sensitive field."""
        result = ConfigViewService._mask_value("api_key", "secret-123")
        assert result == "[REDACTED]"

    def test_masks_password_field(self) -> None:
        """Masks value of password field."""
        result = ConfigViewService._mask_value("password", "my-password")
        assert result == "[REDACTED]"

    def test_preserves_non_sensitive_field(self) -> None:
        """Preserves value of non-sensitive field."""
        result = ConfigViewService._mask_value("model", "gemini-2.5-flash-lite")
        assert result == "gemini-2.5-flash-lite"

    def test_preserves_workspace_path(self) -> None:
        """Preserves value of workspace_path field."""
        result = ConfigViewService._mask_value("workspace_path", "/tmp/test")
        assert result == "/tmp/test"

    def test_preserves_max_tokens(self) -> None:
        """Preserves value of max_tokens field (exception list)."""
        result = ConfigViewService._mask_value("max_tokens", "4096")
        assert result == "4096"

    def test_masks_auth_token(self) -> None:
        """Masks value of auth_token field (not in exception list)."""
        result = ConfigViewService._mask_value("auth_token", "secret-token-123")
        assert result == "[REDACTED]"


class TestFormatTableMasksSensitiveFields:
    """Test format_table() masks sensitive fields."""

    def test_format_table_masks_api_key(self) -> None:
        """format_table() masks api_key field."""
        manager = ConfigurationManager(workspace=Path("/tmp/test"))
        service = ConfigViewService(manager)

        # Get all settings as dict
        from mixseek.config.views import SettingInfo

        settings_dict = {
            "DummySettingsWithSensitiveFields.api_key": SettingInfo(
                key="DummySettingsWithSensitiveFields.api_key",
                raw_key="api_key",
                class_name="DummySettingsWithSensitiveFields",
                current_value="secret-123",
                default_value="secret-123",
                source="default",
                source_type="default",
                value_type="str",
                is_overridden=False,
            ),
            "DummySettingsWithSensitiveFields.model": SettingInfo(
                key="DummySettingsWithSensitiveFields.model",
                raw_key="model",
                class_name="DummySettingsWithSensitiveFields",
                current_value="gemini-2.5-flash-lite",
                default_value="gemini-2.5-flash-lite",
                source="default",
                source_type="default",
                value_type="str",
                is_overridden=False,
            ),
        }

        output = service.format_table(settings_dict)

        # Check that api_key is masked
        assert "[REDACTED]" in output
        assert "secret-123" not in output

        # Check that model is not masked
        assert "gemini-2.5-flash-lite" in output


class TestFormatSingleMasksSensitiveFields:
    """Test format_single() masks sensitive fields."""

    def test_format_single_masks_password(self) -> None:
        """format_single() masks password field."""
        manager = ConfigurationManager(workspace=Path("/tmp/test"))
        service = ConfigViewService(manager)

        from mixseek.config.views import SettingInfo

        setting = SettingInfo(
            key="DummySettingsWithSensitiveFields.password",
            raw_key="password",
            class_name="DummySettingsWithSensitiveFields",
            current_value="my-password",
            default_value="my-password",
            source="default",
            source_type="default",
            value_type="str",
            is_overridden=False,
        )

        output = service.format_single(setting)

        # Check that password is masked
        assert "[REDACTED]" in output
        assert "my-password" not in output

    def test_format_single_preserves_model(self) -> None:
        """format_single() preserves non-sensitive model field."""
        manager = ConfigurationManager(workspace=Path("/tmp/test"))
        service = ConfigViewService(manager)

        from mixseek.config.views import SettingInfo

        setting = SettingInfo(
            key="DummySettingsWithSensitiveFields.model",
            raw_key="model",
            class_name="DummySettingsWithSensitiveFields",
            current_value="gemini-2.5-flash-lite",
            default_value="gemini-2.5-flash-lite",
            source="default",
            source_type="default",
            value_type="str",
            is_overridden=False,
        )

        output = service.format_single(setting)

        # Check that model is not masked
        assert "gemini-2.5-flash-lite" in output
        assert "[REDACTED]" not in output


class TestFormatSettingsFieldsMasksSensitiveFields:
    """Test _format_settings_fields() masks sensitive fields."""

    def test_format_settings_fields_masks_secret_token(self) -> None:
        """_format_settings_fields() masks secret_token field."""
        settings = DummySettingsWithSensitiveFields()

        output = ConfigViewService._format_settings_fields(settings, indent=0)

        # Check that secret_token is masked
        assert "secret_token: [REDACTED]" in output
        assert "token-abc" not in output

    def test_format_settings_fields_preserves_workspace_path(self) -> None:
        """_format_settings_fields() preserves workspace_path field."""
        settings = DummySettingsWithSensitiveFields()

        output = ConfigViewService._format_settings_fields(settings, indent=0)

        # Check that workspace_path is not masked
        assert "/tmp/test" in output


class TestPrintDebugInfoMasksSensitiveFields:
    """Test print_debug_info() masks sensitive fields."""

    def test_print_debug_info_masks_api_key(self, capsys: pytest.CaptureFixture[str]) -> None:
        """print_debug_info() masks api_key field."""
        manager = ConfigurationManager(workspace=Path("/tmp/test"))
        settings = DummySettingsWithSensitiveFields()

        manager.print_debug_info(settings, verbose=False)

        captured = capsys.readouterr()

        # Check that api_key is masked
        assert "[REDACTED]" in captured.out
        assert "secret-123" not in captured.out

    def test_print_debug_info_preserves_model(self, capsys: pytest.CaptureFixture[str]) -> None:
        """print_debug_info() preserves non-sensitive model field."""
        manager = ConfigurationManager(workspace=Path("/tmp/test"))
        settings = DummySettingsWithSensitiveFields()

        manager.print_debug_info(settings, verbose=False)

        captured = capsys.readouterr()

        # Check that model is not masked
        assert "gemini-2.5-flash-lite" in captured.out
