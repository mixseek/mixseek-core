"""Integration tests for configuration traceability."""

from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, LeaderAgentSettings, OrchestratorSettings


class TestTracingIntegration:
    """End-to-end tracing integration tests (T029)"""

    def test_trace_records_default_values(self) -> None:
        """Test that trace records default values appropriately"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Values should match defaults
        assert settings.model == "google-gla:gemini-2.5-flash-lite"
        assert settings.timeout_seconds == 300

    def test_print_debug_info_output_structure(self, capsys: Any) -> None:
        """Test print_debug_info() output structure"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        manager.print_debug_info(settings, verbose=False)

        captured = capsys.readouterr()
        output = captured.out

        # Verify output structure
        assert "Configuration Debug Information" in output
        assert "model" in output
        assert "temperature" in output
        assert "timeout_seconds" in output
        assert "Source:" in output

    def test_print_debug_info_verbose_output(self, capsys: Any) -> None:
        """Test verbose mode output includes additional details"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        manager.print_debug_info(settings, verbose=True)

        captured = capsys.readouterr()
        output = captured.out

        # Verbose output should have more information
        assert "Timestamp:" in output
        assert "Configuration Debug Information" in output

    def test_get_all_defaults_contains_expected_values(self) -> None:
        """Test get_all_defaults() contains expected configuration values"""
        manager = ConfigurationManager()

        leader_defaults = manager.get_all_defaults(LeaderAgentSettings)
        orchestrator_defaults = manager.get_all_defaults(OrchestratorSettings)

        # Verify LeaderAgentSettings defaults
        assert leader_defaults["model"] == "google-gla:gemini-2.5-flash-lite"
        # temperature is None, so it may be excluded from defaults dict
        assert leader_defaults["timeout_seconds"] == 300

        # Verify OrchestratorSettings defaults
        assert orchestrator_defaults["timeout_per_team_seconds"] == 300
        assert orchestrator_defaults["max_concurrent_teams"] == 4

    def test_trace_info_consistent_across_multiple_calls(self) -> None:
        """Test that trace info is consistent across multiple calls"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Get trace info multiple times
        trace1 = manager.get_trace_info(settings, "model")
        trace2 = manager.get_trace_info(settings, "model")

        # Trace info should be consistent
        if trace1 is not None and trace2 is not None:
            assert trace1.value == trace2.value
            assert trace1.source_name == trace2.source_name
            assert trace1.field_name == trace2.field_name

    def test_defaults_match_settings_values(self) -> None:
        """Test that default values match actual settings values when not overridden"""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)
        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # When no override is provided, settings should match defaults
        assert settings.model == defaults["model"]
        assert settings.timeout_seconds == defaults["timeout_seconds"]

    def test_multiple_settings_classes_tracing(self) -> None:
        """Test tracing works independently for multiple settings classes"""
        manager = ConfigurationManager()

        manager.load_settings(LeaderAgentSettings)
        defaults1 = manager.get_all_defaults(LeaderAgentSettings)

        manager.load_settings(OrchestratorSettings, workspace_path=Path("/tmp"))
        defaults2 = manager.get_all_defaults(OrchestratorSettings)

        # Verify each settings class has correct defaults
        assert "model" in defaults1
        assert "model" not in defaults2

        assert "timeout_per_team_seconds" in defaults2
        assert "timeout_per_team_seconds" not in defaults1
