"""Integration tests for TOML file loading and configuration discovery."""

import os
from pathlib import Path
from typing import Any

import pytest

from mixseek.config import (
    ConfigurationManager,
    EvaluatorSettings,
    LeaderAgentSettings,
    MemberAgentSettings,
    OrchestratorSettings,
)


class TestTomlFileLoading:
    """TOML file loading tests (T048)"""

    def test_load_flat_toml_structure(self, tmp_path: Path) -> None:
        """Test loading flat TOML structure (OrchestratorSettings)"""
        # Setup: Create config.toml with flat structure
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 600\nmax_concurrent_teams = 8\n")

        # Setup: Change to tmp_path to make config.toml discoverable
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load OrchestratorSettings
            manager = ConfigurationManager(
                workspace=tmp_path,
                environment="dev",
            )
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: TOML values are loaded correctly
            assert settings.timeout_per_team_seconds == 600
            assert settings.max_concurrent_teams == 8
        finally:
            os.chdir(original_cwd)

    def test_load_nested_toml_structure(self, tmp_path: Path) -> None:
        """Test loading nested TOML structure (LeaderAgentSettings)"""
        # Setup: Create config.toml with nested structure
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[LeaderAgentSettings]\nmodel = "openai:gpt-4o"\ntemperature = 0.7\ntimeout_seconds = 300\n'
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load LeaderAgentSettings (does not require workspace)
            manager = ConfigurationManager(environment="dev")
            settings = manager.load_settings(LeaderAgentSettings)

            # Assertion: Nested values are loaded correctly
            assert settings.model == "openai:gpt-4o"
            assert settings.temperature == 0.7
            assert settings.timeout_seconds == 300
        finally:
            os.chdir(original_cwd)

    def test_load_multiple_nested_sections(self, tmp_path: Path) -> None:
        """Test loading multiple nested sections from same TOML file"""
        # Setup: Create config.toml with multiple sections
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[LeaderAgentSettings]\n"
            'model = "openai:gpt-4o"\n'
            "timeout_seconds = 300\n"
            "\n"
            "[MemberAgentSettings]\n"
            'agent_name = "test_member"\n'
            'agent_type = "code_analyzer"\n'
            'tool_description = "Code analysis tool"\n'
            'model = "anthropic:claude-opus"\n'
            "max_tokens = 4000\n"
            "timeout_seconds = 300\n"
            "\n"
            "[EvaluatorSettings]\n"
            'default_model = "openai:gpt-4o"\n'
            "timeout_seconds = 300\n"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load all settings classes
            manager = ConfigurationManager(environment="dev")
            leader_settings = manager.load_settings(LeaderAgentSettings)
            member_settings = manager.load_settings(MemberAgentSettings)
            evaluator_settings = manager.load_settings(EvaluatorSettings)

            # Assertion: Each section loads correctly without interference
            assert leader_settings.model == "openai:gpt-4o"
            assert member_settings.model == "anthropic:claude-opus"
            assert evaluator_settings.default_model == "openai:gpt-4o"
            # Verify no cross-section contamination
            assert leader_settings.model != member_settings.model
        finally:
            os.chdir(original_cwd)

    def test_toml_syntax_error_handling(self, tmp_path: Path) -> None:
        """Test TOML syntax error handling with clear message"""
        # Setup: Create invalid TOML syntax
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings\n"  # Missing closing bracket
            "timeout_per_team_seconds = 600\n"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Attempt to load settings with invalid TOML
            manager = ConfigurationManager(workspace=tmp_path)
            with pytest.raises(Exception):  # Should raise TOML parsing error
                manager.load_settings(OrchestratorSettings)
        finally:
            os.chdir(original_cwd)

    def test_missing_toml_file_handling(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test missing TOML file does not cause error"""
        # Setup: Do NOT create config.toml, only workspace
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load OrchestratorSettings without TOML file
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: Loading succeeds with defaults
            # workspace_path from ConfigurationManager is used
            assert settings.workspace_path == tmp_path
            # Default values used for other fields
            assert settings.timeout_per_team_seconds == 300  # default
            assert settings.max_concurrent_teams == 4  # default
        finally:
            os.chdir(original_cwd)

    def test_toml_overrides_defaults(self, tmp_path: Path) -> None:
        """Test TOML values override defaults in priority chain"""
        # Setup: Create TOML with only one field
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 500\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load OrchestratorSettings
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: TOML value used, defaults for unspecified fields
            assert settings.timeout_per_team_seconds == 500  # from TOML, not default 300
            assert settings.max_concurrent_teams == 4  # default, not in TOML

            # Verify trace shows TOML as source
            trace = manager.get_trace_info(settings, "timeout_per_team_seconds")
            if trace:
                assert trace.source_name == "TOML"
                assert trace.source_type == "toml"
                assert trace.value == 500
        finally:
            os.chdir(original_cwd)

    def test_toml_priority_over_defaults_multiple_fields(self, tmp_path: Path) -> None:
        """Test TOML priority for multiple fields"""
        # Setup: Create TOML with multiple fields
        config_file = tmp_path / "config.toml"
        config_file.write_text('[LeaderAgentSettings]\nmodel = "custom:model"\ntimeout_seconds = 600\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load LeaderAgentSettings
            manager = ConfigurationManager(environment="dev")
            settings = manager.load_settings(LeaderAgentSettings)

            # Assertion: TOML values override defaults
            assert settings.model == "custom:model"  # from TOML
            assert settings.timeout_seconds == 600  # from TOML
            assert settings.temperature is None  # default (not in TOML)
        finally:
            os.chdir(original_cwd)


class TestCustomTomlFilePath:
    """Custom TOML file path tests (T049)"""

    def test_toml_file_discovery_in_workspace(self, tmp_path: Path) -> None:
        """Test automatic TOML file discovery in workspace"""
        # Setup: Create workspace/config.toml
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 550\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load settings without explicit config path
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: config.toml is automatically discovered and timeout set
            assert settings.timeout_per_team_seconds == 550
            # workspace_path passed by ConfigurationManager
            assert settings.workspace_path == tmp_path
        finally:
            os.chdir(original_cwd)

    def test_toml_with_trace_recording(self, tmp_path: Path) -> None:
        """Test TOML sources are properly traced"""
        # Setup: Create config.toml
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 750\nmax_concurrent_teams = 12\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load settings and retrieve trace
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: Trace information is recorded with TOML source
            trace_timeout = manager.get_trace_info(settings, "timeout_per_team_seconds")
            assert trace_timeout is not None
            assert trace_timeout.source_name == "TOML"
            assert trace_timeout.source_type == "toml"
            assert trace_timeout.value == 750
            assert trace_timeout.timestamp is not None

            trace_teams = manager.get_trace_info(settings, "max_concurrent_teams")
            assert trace_teams is not None
            assert trace_teams.source_name == "TOML"
            assert trace_teams.value == 12
        finally:
            os.chdir(original_cwd)

    def test_toml_priority_chain_env_over_toml(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that ENV overrides TOML (priority chain)"""
        # Setup: Create config.toml
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 400\n")

        # Setup: Set environment variable
        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "900")
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load settings with both TOML and ENV
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: ENV value wins over TOML
            assert settings.timeout_per_team_seconds == 900  # from ENV, not TOML (400)

            # Verify trace shows ENV as source
            trace = manager.get_trace_info(settings, "timeout_per_team_seconds")
            assert trace is not None
            assert trace.source_name == "environment_variables"
            assert trace.value == "900"  # env vars are strings
        finally:
            os.chdir(original_cwd)

    def test_custom_toml_file_via_mixseek_config_file_env(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test MIXSEEK_CONFIG_FILE environment variable overrides config.toml path (spec.md:258)"""
        # Setup: Create custom.toml in tmp_path
        custom_file = tmp_path / "custom.toml"
        custom_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 700\nmax_concurrent_teams = 10\n")

        # Setup: Also create config.toml with different values (should be ignored)
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 300\nmax_concurrent_teams = 4\n")

        # Setup: Set MIXSEEK_CONFIG_FILE to point to custom.toml
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(custom_file))
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load settings
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: custom.toml values are used, NOT config.toml
            assert settings.timeout_per_team_seconds == 700  # from custom.toml, not config.toml (300)
            assert settings.max_concurrent_teams == 10  # from custom.toml, not config.toml (4)

            # Verify trace shows TOML as source (not ENV)
            trace = manager.get_trace_info(settings, "timeout_per_team_seconds")
            assert trace is not None
            assert trace.source_name == "TOML"
            assert trace.source_type == "toml"
            assert trace.value == 700
        finally:
            os.chdir(original_cwd)

    def test_mixseek_config_file_with_nonexistent_file(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test MIXSEEK_CONFIG_FILE pointing to nonexistent file falls back to defaults"""
        # Setup: MIXSEEK_CONFIG_FILE points to nonexistent file
        nonexistent_file = tmp_path / "nonexistent.toml"
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(nonexistent_file))
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Load settings
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assertion: Defaults are used when specified file doesn't exist (Article 9 compliance)
            assert settings.timeout_per_team_seconds == 300  # default
            assert settings.max_concurrent_teams == 4  # default
        finally:
            os.chdir(original_cwd)

    def test_custom_toml_file_syntax_error_propagates(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test TOML syntax error in custom file raises exception"""
        # Setup: Create custom.toml with invalid syntax
        custom_file = tmp_path / "custom.toml"
        custom_file.write_text(
            "[OrchestratorSettings\n"  # Missing closing bracket
            "timeout_per_team_seconds = 700\n"
        )

        # Setup: Set MIXSEEK_CONFIG_FILE to point to custom.toml
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(custom_file))
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute: Attempt to load settings with invalid TOML
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            with pytest.raises(Exception):  # Should raise TOML parsing error
                manager.load_settings(OrchestratorSettings)
        finally:
            os.chdir(original_cwd)
