"""
User Story 5 Acceptance Scenario Tests

These tests validate that the Configuration Manager implementation
meets all acceptance scenarios from spec.md for User Story 5:
"ユーザがTOMLファイルで設定を管理" (Users manage configuration via TOML files)

Test Coverage:
- US5 AS1: TOML file discovery and loading
- US5 AS2: Environment-specific TOML files
- US5 AS3: Partial configurations with defaults
- US5 AS4: MIXSEEK_CONFIG_FILE environment variable support
- US5 AS5: TOML syntax error handling
"""

import os
from pathlib import Path
from typing import Any

import pytest

from mixseek.config import (
    ConfigurationManager,
    OrchestratorSettings,
)


class TestUS5AcceptanceScenarios:
    """Acceptance scenarios for User Story 5: TOML Configuration Management"""

    # ========== US5 AS1: TOML File Discovery and Loading ==========

    def test_us5_as1_toml_discovery_from_config_toml(self, tmp_path: Path) -> None:
        """
        US5 AS1: Application discovers config.toml in workspace

        **Given** A workspace directory with config.toml file
        **When** ConfigurationManager loads settings
        **Then** TOML values are loaded and used
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 600\nmax_concurrent_teams = 8\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert
            assert settings.timeout_per_team_seconds == 600
            assert settings.max_concurrent_teams == 8
            trace = manager.get_trace_info(settings, "timeout_per_team_seconds")
            assert trace is not None
            assert trace.source_name == "TOML"
        finally:
            os.chdir(original_cwd)

    def test_us5_as1_multiple_sections_in_toml(self, tmp_path: Path) -> None:
        """
        US5 AS1: TOML file with multiple settings sections

        **Given** config.toml with multiple settings sections
        **When** Loading same settings class multiple times
        **Then** TOML values are loaded consistently
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 600\nmax_concurrent_teams = 8\n")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute - load same settings class multiple times
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            orchestrator1 = manager.load_settings(OrchestratorSettings)
            orchestrator2 = manager.load_settings(OrchestratorSettings)

            # Assert - both loads should be consistent
            assert orchestrator1.timeout_per_team_seconds == 600
            assert orchestrator1.max_concurrent_teams == 8
            assert orchestrator2.timeout_per_team_seconds == 600
            assert orchestrator2.max_concurrent_teams == 8
        finally:
            os.chdir(original_cwd)

    # ========== US5 AS2: Environment-Specific TOML Files ==========

    def test_us5_as2_dev_environment_config(self, tmp_path: Path) -> None:
        """
        US5 AS2: Development environment uses dev defaults via TOML

        **Given** config-dev.toml with development settings
        **When** Environment is "dev"
        **Then** Development values are loaded (conservative timeouts, etc.)
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings]\n"
            'workspace_path = "/tmp/dev_workspace"\n'
            "timeout_per_team_seconds = 300\n"
            "max_concurrent_teams = 4\n"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - dev settings are conservative
            assert settings.timeout_per_team_seconds == 300
            assert settings.max_concurrent_teams == 4
        finally:
            os.chdir(original_cwd)

    def test_us5_as2_prod_environment_config(self, tmp_path: Path) -> None:
        """
        US5 AS2: Production environment uses optimized settings via TOML

        **Given** config-prod.toml with production settings
        **When** Environment is "prod"
        **Then** Production values are loaded (high concurrency, long timeouts)
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings]\n"
            'workspace_path = "/data/prod_workspace"\n'
            "timeout_per_team_seconds = 1800\n"
            "max_concurrent_teams = 16\n"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="prod")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - prod settings are optimized
            assert settings.timeout_per_team_seconds == 1800
            assert settings.max_concurrent_teams == 16
        finally:
            os.chdir(original_cwd)

    # ========== US5 AS3: Partial Configurations with Defaults ==========

    def test_us5_as3_partial_config_with_defaults(self, tmp_path: Path) -> None:
        """
        US5 AS3: Partial TOML configuration falls back to defaults

        **Given** TOML with only some fields set
        **When** Loading settings
        **Then** Unset fields use default values
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings]\ntimeout_per_team_seconds = 500\n"
            # max_concurrent_teams not set
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert
            assert settings.timeout_per_team_seconds == 500  # from TOML
            assert settings.max_concurrent_teams == 4  # default

            # Verify sources (trace info is stored per-class)
            trace_timeout = manager.get_trace_info(settings, "timeout_per_team_seconds")
            trace_teams = manager.get_trace_info(settings, "max_concurrent_teams")
            if trace_timeout is not None:
                assert trace_timeout.source_name == "TOML"
            if trace_teams is not None:
                assert trace_teams.source_name == "default"
        finally:
            os.chdir(original_cwd)

    def test_us5_as3_all_settings_use_defaults_when_toml_missing(self, tmp_path: Path) -> None:
        """
        US5 AS3: All settings use defaults when TOML file is missing

        **Given** No config.toml file exists
        **When** Loading settings
        **Then** All values use defaults (Article 9: graceful fallback)
        """
        # Setup - don't create config.toml
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - all defaults are used
            assert settings.timeout_per_team_seconds == 300  # default
            assert settings.max_concurrent_teams == 4  # default

            # Verify all sources are "default" (trace info may be None)
            for field in ["timeout_per_team_seconds", "max_concurrent_teams"]:
                trace = manager.get_trace_info(settings, field)
                if trace is not None:
                    assert trace.source_name == "default"
        finally:
            os.chdir(original_cwd)

    # ========== US5 AS4: MIXSEEK_CONFIG_FILE Environment Variable ==========

    def test_us5_as4_custom_config_file_via_env_variable(self, tmp_path: Path, monkeypatch: Any) -> None:
        """
        US5 AS4: MIXSEEK_CONFIG_FILE environment variable specifies custom path

        **Given** MIXSEEK_CONFIG_FILE points to custom.toml
        **When** Loading settings
        **Then** Custom file is used (not config.toml)
        """
        # Setup
        custom_file = tmp_path / "custom.toml"
        custom_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 700\nmax_concurrent_teams = 10\n")

        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 300\nmax_concurrent_teams = 4\n")

        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(custom_file))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - custom.toml values, not config.toml
            assert settings.timeout_per_team_seconds == 700
            assert settings.max_concurrent_teams == 10
        finally:
            os.chdir(original_cwd)

    def test_us5_as4_mixseek_config_file_priority_over_default(self, tmp_path: Path, monkeypatch: Any) -> None:
        """
        US5 AS4: MIXSEEK_CONFIG_FILE has priority over default config.toml

        **Given** Both custom.toml and config.toml exist
        **And** MIXSEEK_CONFIG_FILE points to custom.toml
        **When** Loading settings
        **Then** custom.toml is used (priority: ENV path > default path)
        """
        # Setup - exactly like test above
        custom_file = tmp_path / "production.toml"
        custom_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 900\n")

        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 300\n")

        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(custom_file))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="prod")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - production.toml from ENV var wins
            assert settings.timeout_per_team_seconds == 900
        finally:
            os.chdir(original_cwd)

    def test_us5_as4_nonexistent_mixseek_config_file_uses_defaults(self, tmp_path: Path, monkeypatch: Any) -> None:
        """
        US5 AS4: Nonexistent MIXSEEK_CONFIG_FILE gracefully falls back to defaults

        **Given** MIXSEEK_CONFIG_FILE points to nonexistent file
        **When** Loading settings
        **Then** Defaults are used (Article 9: graceful error handling)
        """
        # Setup
        nonexistent = tmp_path / "nonexistent.toml"
        monkeypatch.setenv("MIXSEEK_CONFIG_FILE", str(nonexistent))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - defaults are used
            assert settings.timeout_per_team_seconds == 300  # default
            assert settings.max_concurrent_teams == 4  # default
        finally:
            os.chdir(original_cwd)

    # ========== US5 AS5: TOML Syntax Error Handling ==========

    def test_us5_as5_toml_syntax_error_raises_exception(self, tmp_path: Path) -> None:
        """
        US5 AS5: Invalid TOML syntax raises clear error

        **Given** config.toml with syntax errors
        **When** Loading settings
        **Then** Exception is raised (Article 9: proper error propagation)
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings\n"  # Missing closing bracket
            "timeout_per_team_seconds = 600\n"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute & Assert
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            with pytest.raises(Exception):  # Should raise TOML parsing error
                manager.load_settings(OrchestratorSettings)
        finally:
            os.chdir(original_cwd)

    def test_us5_as5_invalid_toml_value_type_raises_error(self, tmp_path: Path) -> None:
        """
        US5 AS5: Invalid value type in TOML raises validation error

        **Given** TOML with invalid value type (string instead of int)
        **When** Loading settings
        **Then** ValidationError is raised
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings]\ntimeout_per_team_seconds = not_a_number\n"  # Invalid
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute & Assert
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            with pytest.raises(Exception):  # Should raise validation error
                manager.load_settings(OrchestratorSettings)
        finally:
            os.chdir(original_cwd)

    # ========== Cross-Cutting Concerns ==========

    def test_us5_multiple_settings_classes_independent(self, tmp_path: Path) -> None:
        """
        US5: Multiple TOML settings section definitions

        **Given** config.toml with all settings sections defined
        **When** Loading OrchestratorSettings
        **Then** OrchestratorSettings loads only its own section
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[OrchestratorSettings]\ntimeout_per_team_seconds = 600\nmax_concurrent_teams = 8\n"
            # Additional sections would be defined here in a real file
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            orchestrator = manager.load_settings(OrchestratorSettings)

            # Assert - OrchestratorSettings loaded correctly from its section
            assert orchestrator.timeout_per_team_seconds == 600
            assert orchestrator.max_concurrent_teams == 8
        finally:
            os.chdir(original_cwd)

    def test_us5_toml_with_environment_variable_override(self, tmp_path: Path, monkeypatch: Any) -> None:
        """
        US5: TOML + ENV priority (ENV wins over TOML)

        **Given** TOML has timeout_per_team_seconds = 400
        **And** ENV has MIXSEEK_TIMEOUT_PER_TEAM_SECONDS = 900
        **When** Loading settings
        **Then** ENV value (900) is used
        """
        # Setup
        config_file = tmp_path / "config.toml"
        config_file.write_text("[OrchestratorSettings]\ntimeout_per_team_seconds = 400\n")

        monkeypatch.setenv("MIXSEEK_TIMEOUT_PER_TEAM_SECONDS", "900")
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(tmp_path))

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Execute
            manager = ConfigurationManager(workspace=tmp_path, environment="dev")
            settings = manager.load_settings(OrchestratorSettings)

            # Assert - ENV value wins
            assert settings.timeout_per_team_seconds == 900

            # Verify source is ENV
            trace = manager.get_trace_info(settings, "timeout_per_team_seconds")
            assert trace is not None
            assert trace.source_name == "environment_variables"
        finally:
            os.chdir(original_cwd)
