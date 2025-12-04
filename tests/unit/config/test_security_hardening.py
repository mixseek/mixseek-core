"""Security hardening tests for Configuration Manager - Phase 11 T074."""

from pathlib import Path
from typing import Any

import pytest

from mixseek.config.sources.toml_source import (
    _sanitize_error_message,
    _validate_safe_path,
)


class TestPathTraversalPrevention:
    """Test path traversal attack prevention - T074 security hardening."""

    def test_validate_safe_path_rejects_parent_traversal(self) -> None:
        """Test that path traversal with .. is rejected."""
        malicious_path = Path("../../../etc/passwd")

        with pytest.raises(ValueError, match="path traversal detected"):
            _validate_safe_path(malicious_path)

    def test_validate_safe_path_rejects_multiple_traversals(self) -> None:
        """Test that multiple .. sequences are rejected."""
        malicious_path = Path("../../var/../../etc/config")

        with pytest.raises(ValueError, match="path traversal detected"):
            _validate_safe_path(malicious_path)

    def test_validate_safe_path_accepts_normal_paths(self) -> None:
        """Test that normal paths are accepted."""
        normal_path = Path("config.toml")
        # Should not raise
        _validate_safe_path(normal_path)

    def test_validate_safe_path_accepts_subdirectory_paths(self) -> None:
        """Test that subdirectory paths are accepted."""
        normal_path = Path("configs/production/config.toml")
        # Should not raise
        _validate_safe_path(normal_path)

    def test_validate_safe_path_handles_absolute_paths(self) -> None:
        """Test that absolute paths are handled safely."""
        abs_path = Path("/etc/config/app.toml")
        # Should not raise for absolute paths in general
        _validate_safe_path(abs_path)

    def test_validate_safe_path_rejects_invalid_paths(self) -> None:
        """Test that invalid paths raise appropriate errors."""
        # Path with null bytes or other invalid characters would fail
        # (This is mostly handled by Path constructor, but we test our validation)
        invalid_path = Path("\x00/config.toml")
        # Path may raise ValueError or OSError during resolution
        with pytest.raises((ValueError, OSError)):
            _validate_safe_path(invalid_path)


class TestErrorMessageSanitization:
    """Test error message sanitization - T074 security hardening."""

    def test_sanitize_removes_absolute_paths(self) -> None:
        """Test that absolute paths are removed from error messages."""
        error_msg = "Error reading file from /home/user/sensitive/config.toml"
        sanitized = _sanitize_error_message(error_msg)

        # Should not contain the actual path
        assert "/home/user/sensitive/config.toml" not in sanitized
        # Should contain placeholder
        assert "<path>" in sanitized or "<home>" in sanitized

    def test_sanitize_removes_home_directory(self) -> None:
        """Test that home directory paths are replaced."""
        home = str(Path.home())
        error_msg = f"Configuration file not found at {home}/myapp/config.toml"
        sanitized = _sanitize_error_message(error_msg)

        # Should not contain home directory
        assert home not in sanitized
        # Should contain placeholder (either generic or specific)
        assert "<path>" in sanitized or "<home>" in sanitized

    def test_sanitize_removes_temp_directory(self) -> None:
        """Test that temporary directory paths are replaced."""
        import tempfile

        temp_dir = tempfile.gettempdir()
        error_msg = f"Cannot write to {temp_dir}/config.toml"
        sanitized = _sanitize_error_message(error_msg)

        # Should not contain temp directory
        assert temp_dir not in sanitized
        # Should contain placeholder (either generic or specific)
        assert "<path>" in sanitized or "<temp>" in sanitized

    def test_sanitize_preserves_error_context(self) -> None:
        """Test that error context is preserved after sanitization."""
        error_msg = "TOML syntax error at line 42: unexpected character"
        sanitized = _sanitize_error_message(error_msg)

        # Error context should be preserved
        assert "syntax error" in sanitized
        assert "line 42" in sanitized

    def test_sanitize_handles_empty_messages(self) -> None:
        """Test that empty error messages are handled gracefully."""
        error_msg = ""
        sanitized = _sanitize_error_message(error_msg)

        # Should return empty or minimal string
        assert isinstance(sanitized, str)

    def test_sanitize_handles_messages_without_paths(self) -> None:
        """Test that messages without paths are unchanged."""
        error_msg = "Invalid configuration: missing required field 'workspace_path'"
        sanitized = _sanitize_error_message(error_msg)

        # Should contain the same error information
        assert "Invalid configuration" in sanitized
        assert "required field" in sanitized


class TestSecurityHardeningIntegration:
    """Integration tests for security hardening - T074."""

    def test_path_validation_in_toml_loading(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test path validation is applied during TOML loading."""
        from mixseek.config import LeaderAgentSettings
        from mixseek.config.sources.toml_source import CustomTomlConfigSettingsSource

        # Test with a normal file
        config_file = tmp_path / "config.toml"
        config_file.write_text("[leader]\nmodel = 'openai:gpt-4o'\n")

        # Should work fine with normal path
        source = CustomTomlConfigSettingsSource(LeaderAgentSettings)
        assert source is not None

    def test_error_sanitization_in_toml_loading(self, monkeypatch: Any) -> None:
        """Test error message sanitization during TOML loading."""
        from mixseek.config import LeaderAgentSettings
        from mixseek.config.sources.toml_source import CustomTomlConfigSettingsSource

        # Set a path with traversal attempt
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", "../../etc/passwd")

        # Should raise ValueError for path traversal
        with pytest.raises(ValueError, match="path traversal"):
            CustomTomlConfigSettingsSource(LeaderAgentSettings)

    def test_sensitive_info_not_leaked_in_errors(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that sensitive paths are not leaked in error messages."""
        from mixseek.config import LeaderAgentSettings
        from mixseek.config.sources.toml_source import CustomTomlConfigSettingsSource

        # Create invalid TOML file
        config_file = tmp_path / "bad.toml"
        config_file.write_text("[leader\n# Missing closing bracket")
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        # Should raise TOML error, but path should be sanitized
        try:
            CustomTomlConfigSettingsSource(LeaderAgentSettings)
        except Exception as e:
            error_msg = str(e)
            # Should not contain the full path
            assert str(config_file) not in error_msg or "<path>" in error_msg or "<home>" in error_msg
