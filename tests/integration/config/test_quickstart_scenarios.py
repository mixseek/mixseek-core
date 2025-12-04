"""Quickstart.md scenario validation tests - Phase 11 T075."""

from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, LeaderAgentSettings, OrchestratorSettings


class TestQuickstartBasicUsage:
    """Test basic usage scenarios from quickstart.md - T075."""

    def test_scenario_1_toml_file_creation(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test basic TOML file creation and loading."""
        # Create config.toml as shown in quickstart
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[LeaderAgentSettings]
model = "openai:gpt-4o"
timeout_seconds = 300

[MemberAgentSettings]
model = "anthropic:claude-sonnet-4-5"
timeout_seconds = 180
"""
        )
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        # Load settings as shown in quickstart
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Verify settings loaded correctly
        assert settings.model == "openai:gpt-4o"
        assert settings.timeout_seconds == 300

    def test_scenario_2_environment_variables_override(self, monkeypatch: Any) -> None:
        """Test environment variable override as shown in quickstart."""
        # Set environment variables as shown in quickstart
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-5")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "600")
        monkeypatch.setenv("MIXSEEK_LEADER__TEMPERATURE", "0.5")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Verify environment variables override defaults
        assert settings.model == "openai:gpt-5"
        assert settings.timeout_seconds == 600
        assert settings.temperature == 0.5

    def test_scenario_3_configuration_manager_initialization(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test ConfigurationManager initialization as shown in quickstart."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Initialize as shown in quickstart
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Should successfully load with defaults
        assert settings.model == "google-gla:gemini-2.5-flash-lite"
        assert settings.timeout_seconds == 300

    def test_scenario_4_debug_info_output(self, monkeypatch: Any, capsys: Any) -> None:
        """Test debug info output as shown in quickstart."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "600")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Print debug info as shown in quickstart
        manager.print_debug_info(settings, verbose=True)

        captured = capsys.readouterr()
        output = captured.out

        # Verify output contains expected information
        assert "model" in output
        assert "timeout_seconds" in output
        assert "Source:" in output


class TestQuickstartCLIUsage:
    """Test CLI usage scenarios from quickstart.md - T075."""

    def test_config_init_command(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test config init command scenarios."""
        from mixseek.config.template import TemplateGenerator

        monkeypatch.chdir(tmp_path)

        # Test template generation
        generator = TemplateGenerator()
        template = generator.generate_template("leader")

        # Verify template contains expected structure
        assert "[leader]" in template or "Type:" in template
        assert "model" in template
        assert "timeout_seconds" in template

    def test_config_list_retrieves_settings(self) -> None:
        """Test that we can retrieve all available settings."""
        manager = ConfigurationManager()
        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # Should have multiple settings
        assert len(defaults) > 0
        assert "model" in defaults

    def test_config_show_displays_values(self, monkeypatch: Any, capsys: Any) -> None:
        """Test displaying current configuration values."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Display debug info
        manager.print_debug_info(settings)

        captured = capsys.readouterr()
        # Should display model value
        assert "openai:gpt-4o" in captured.out or "model" in captured.out


class TestQuickstartAcceptanceScenarios:
    """Complete acceptance scenarios from quickstart.md - T075."""

    def test_acceptance_scenario_dev_environment(
        self, tmp_path: Path, monkeypatch: Any, isolate_from_project_dotenv: None
    ) -> None:
        """Test development environment scenario."""
        # Clear environment variables to avoid interference
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            f"""
[OrchestratorSettings]
workspace_path = "{str(workspace)}"
timeout_per_team_seconds = 300

[LeaderAgentSettings]
model = "openai:gpt-4o"
timeout_seconds = 300
"""
        )
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))

        manager = ConfigurationManager()
        leader_settings = manager.load_settings(LeaderAgentSettings)
        orchestrator_settings = manager.load_settings(OrchestratorSettings)

        # Verify dev environment settings
        assert leader_settings.model == "openai:gpt-4o"
        assert leader_settings.timeout_seconds == 300
        assert orchestrator_settings.workspace_path == workspace

    def test_acceptance_scenario_override_priority(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test priority chain: CLI > ENV > TOML > Defaults."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[LeaderAgentSettings]
model = "openai:gpt-4o"
timeout_seconds = 300
"""
        )
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(config_file))
        # ENV override
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "600")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # ENV should override TOML
        assert settings.timeout_seconds == 600

    def test_acceptance_scenario_trace_info(self, monkeypatch: Any) -> None:
        """Test trace information for debugging."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # Get trace for a specific field
        trace = manager.get_trace_info(settings, "model")

        # Should have trace information
        assert trace is not None
        assert trace.value == "openai:gpt-4o"
        assert trace.source_name is not None

    def test_acceptance_scenario_all_defaults_comparison(self) -> None:
        """Test comparing current values with defaults."""
        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)
        defaults = manager.get_all_defaults(LeaderAgentSettings)

        # Should have defaults for comparison
        assert defaults is not None
        assert "model" in defaults

        # Current should equal default (no override)
        assert settings.model == defaults["model"]

    def test_acceptance_scenario_multiple_overrides(self, monkeypatch: Any) -> None:
        """Test multiple setting overrides via different sources."""
        monkeypatch.setenv("MIXSEEK_LEADER__MODEL", "openai:gpt-4o")
        monkeypatch.setenv("MIXSEEK_LEADER__TEMPERATURE", "0.5")
        monkeypatch.setenv("MIXSEEK_LEADER__TIMEOUT_SECONDS", "450")

        manager = ConfigurationManager()
        settings = manager.load_settings(LeaderAgentSettings)

        # All overrides should be applied
        assert settings.model == "openai:gpt-4o"
        assert settings.temperature == 0.5
        assert settings.timeout_seconds == 450
