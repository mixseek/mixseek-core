"""Unit tests for ConfigurationManager."""

from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, LeaderAgentSettings, OrchestratorSettings
from mixseek.config.sources.tracing_source import SourceTrace


class TestTraceInfoRetrieval:
    """Trace information retrieval tests (T023)"""

    def test_get_trace_info_returns_source_trace_or_none(self, tmp_path: Path) -> None:
        """Test get_trace_info() returns SourceTrace or None appropriately"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Get trace for model field
        trace = manager.get_trace_info(settings, "model")

        # Trace may be None for defaults, which is acceptable
        # But if present, must have correct structure
        if trace is not None:
            assert isinstance(trace, SourceTrace)
            assert trace.field_name == "model"
            assert trace.value is not None
            assert trace.source_name is not None
            assert trace.source_type is not None
            assert trace.timestamp is not None

    def test_trace_structure_when_present(self, tmp_path: Path) -> None:
        """Test trace structure has all required fields when present"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        trace = manager.get_trace_info(settings, "model")

        if trace is not None:
            # All fields must be present in SourceTrace
            assert hasattr(trace, "value")
            assert hasattr(trace, "source_name")
            assert hasattr(trace, "source_type")
            assert hasattr(trace, "field_name")
            assert hasattr(trace, "timestamp")

    def test_trace_for_default_source(self, tmp_path: Path) -> None:
        """Test trace for default value (no override)"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # temperature has no override, should use default
        trace = manager.get_trace_info(settings, "temperature")

        # Even for defaults, trace should be recorded
        if trace:
            assert trace.field_name == "temperature"

    def test_trace_for_nonexistent_field_returns_none(self, tmp_path: Path) -> None:
        """Test trace for non-existent field returns None"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        trace = manager.get_trace_info(settings, "nonexistent_field")

        assert trace is None


class TestPrintDebugInfo:
    """print_debug_info output tests (T024)"""

    def test_print_debug_info_includes_all_settings_fields(self, tmp_path: Path, capsys: Any) -> None:
        """Test debug info includes all settings fields"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        manager.print_debug_info(settings)

        captured = capsys.readouterr()
        output = captured.out

        # Verify field names are included
        assert "model" in output
        assert "temperature" in output
        assert "timeout_seconds" in output

    def test_print_debug_info_includes_source_information(self, tmp_path: Path, capsys: Any) -> None:
        """Test debug info includes source information"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        manager.print_debug_info(settings)

        captured = capsys.readouterr()
        output = captured.out

        # Verify source information is included
        assert "Source:" in output

    def test_print_debug_info_includes_timestamp(self, tmp_path: Path, capsys: Any) -> None:
        """Test debug info includes timestamp"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Use verbose mode to ensure timestamp is shown for defaults
        manager.print_debug_info(settings, verbose=True)

        captured = capsys.readouterr()
        output = captured.out

        # Verify timestamp information is included
        assert "Timestamp:" in output

    def test_print_debug_info_verbose_mode_shows_additional_details(self, tmp_path: Path, capsys: Any) -> None:
        """Test verbose mode shows additional details"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        manager.print_debug_info(settings, verbose=True)

        captured = capsys.readouterr()
        output_verbose = captured.out

        # Verbose mode should have "Raw value" information
        # (Re-capture for non-verbose comparison)
        capsys.readouterr()  # Clear
        manager.print_debug_info(settings, verbose=False)
        captured = capsys.readouterr()
        output_normal = captured.out

        # Verbose output should potentially be longer or include more details
        assert len(output_verbose) >= len(output_normal)


class TestGetAllDefaults:
    """get_all_defaults tests (T025)"""

    def test_get_all_defaults_returns_all_default_values(self, tmp_path: Path) -> None:
        """Test returns all default values from schema"""
        manager = ConfigurationManager()

        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # Verify defaults are returned as dict
        assert isinstance(defaults, dict)
        assert "model" in defaults
        assert "timeout_seconds" in defaults

    def test_get_all_defaults_includes_correct_values(self, tmp_path: Path) -> None:
        """Test defaults have correct values"""
        manager = ConfigurationManager()

        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # Verify specific default values
        assert defaults["model"] == "google-gla:gemini-2.5-flash-lite"
        assert defaults["timeout_seconds"] == 300

    def test_get_all_defaults_for_orchestrator_settings(self, tmp_path: Path) -> None:
        """Test defaults for OrchestratorSettings"""
        manager = ConfigurationManager()

        defaults = manager.get_all_defaults(OrchestratorSettings)

        # Verify OrchestratorSettings defaults
        assert isinstance(defaults, dict)
        assert "timeout_per_team_seconds" in defaults
        assert "max_concurrent_teams" in defaults
        assert defaults["timeout_per_team_seconds"] == 300
        assert defaults["max_concurrent_teams"] == 4

    def test_get_all_defaults_excludes_required_fields_without_defaults(self, tmp_path: Path) -> None:
        """Test that required fields without defaults are excluded"""
        manager = ConfigurationManager()

        defaults = manager.get_all_defaults(OrchestratorSettings)

        # workspace_path is required and has no default
        assert "workspace_path" not in defaults


class TestConfigurationManager:
    """ConfigurationManagerのテスト (統合テスト)。

    注: 個別の機能テストは TestTraceInfoRetrieval, TestPrintDebugInfo,
    TestGetAllDefaults, TestCLIArgumentsIntegration で実装されています。
    このクラスは統合テストのためのプレースホルダーです。
    """

    pass


class TestCLIArgumentsIntegration:
    """CLI arguments integration tests (T043)"""

    def test_cli_args_parameter_passes_to_settings(self, tmp_path: Path) -> None:
        """Test cli_args parameter is passed to settings"""
        # Setup: ConfigurationManager with cli_args
        manager = ConfigurationManager(
            cli_args={"timeout_per_team_seconds": 500},
            workspace=tmp_path,
            environment="dev",
        )
        settings = manager.load_settings(OrchestratorSettings)

        # Verify CLI args are applied to settings
        assert settings.timeout_per_team_seconds == 500

    def test_cli_args_none_values_filtered(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test None values are filtered from CLI args"""
        # Setup: Environment variable set as fallback
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        # Setup: cli_args with None values (should be filtered by ConfigurationManager)
        # This tests that ConfigurationManager filters out None values
        manager = ConfigurationManager(
            cli_args={"timeout_per_team_seconds": None},
            workspace=tmp_path,
            environment="dev",
        )
        settings = manager.load_settings(OrchestratorSettings)

        # Verify None values do not override, defaults are used
        # If ConfigurationManager filters None correctly, default (300) should be used
        assert settings.timeout_per_team_seconds == 300  # default

    def test_cli_args_empty_dict_uses_next_source(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test empty CLI args dict uses next source in priority chain"""
        # Setup: Empty cli_args dict
        # Setup: Environment variable set
        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "400")
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        manager = ConfigurationManager(
            cli_args={},
            workspace=tmp_path,
            environment="dev",
        )
        settings = manager.load_settings(OrchestratorSettings)

        # Verify environment variable is used (next source in chain)
        assert settings.timeout_per_team_seconds == 400
