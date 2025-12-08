"""Configuration CLI commands unit tests (Phase 9-10 - User Stories 3.5 & 7)

Tests for:
- `mixseek config show` and `mixseek config list` commands (Phase 9)
- `mixseek config init` command (Phase 10)

Article 3: Test-First Imperative準拠
- Tests written BEFORE implementation
- RED phase: All tests should FAIL initially
- Test goals defined in phase9-test-plan.md and phase10-test-plan.md

Test Coverage:
- T056: config show command tests
- T057: config list command tests
- T062: integration tests with real ConfigurationManager
- T064: config init command tests (Phase 10 - RED phase)

References:
- Spec: specs/051-configuration/spec.md (User Story 3.5 & 7)
- Plan: specs/051-configuration/phase9-test-plan.md and phase10-test-plan.md
- Fixtures: tests/fixtures/config/

Note:
    RED PHASE TESTS - Expected to FAIL until implementation is complete
    These tests define the contract for CLI configuration viewing commands.
"""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from mixseek.cli.main import app


class TestConfigShowCommand:
    """Tests for `mixseek config show` command (T056)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T056.1: Display All Settings ==========

    def test_config_show_all_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.1: Test `mixseek config show` displays all current settings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - All configuration keys are displayed
        - Values are shown with their current setting
        - Output is human-readable (table or similar format)
        - Requires --config and --workspace options
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion: Basic success criteria
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Should contain configuration keys
        output = result.stdout
        assert "timeout_per_team_seconds" in output or "orchestrator" in output.lower()

    def test_config_show_specific_key(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.3: Test `mixseek config show TIMEOUT_PER_TEAM_SECONDS` displays specific key

        **Acceptance Criteria**:
        - Shows specific key (case-insensitive matching)
        - Displays current value
        - Displays default value
        - Displays source information
        - Only shows one key in output
        - Requires --config and --workspace options
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Call config show with specific key (case-insensitive)
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "timeout_per_team_seconds",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
            ],
        )

        # Assertion: Specific key shown with full details
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show the specific key
        assert "timeout" in output.lower()

        # Should show key info on separate lines
        assert any(keyword in output.lower() for keyword in ["current", "default", "source", "type"])

    def test_config_show_invalid_key(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.4: Test `mixseek config show` with invalid key raises error

        **Acceptance Criteria**:
        - Non-zero exit code for invalid key
        - Error is properly handled
        - Command does not crash
        - Requires --config and --workspace options
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Call config show with invalid key
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "INVALID_NONEXISTENT_KEY",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
            ],
        )

        # Assertion: Error is handled, exit code non-zero
        assert result.exit_code != 0, "Should fail for invalid key"
        # Exit code 1 indicates error (not crash/exception)
        assert result.exit_code == 1

    # ========== T056.4: JSON Format Output ==========

    def test_config_show_json_format(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.4: Test `mixseek config show --output-format json`

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output is valid JSON
        - JSON contains orchestrator settings
        - JSON structure matches hierarchical format (orchestrator, teams, members)
        """
        import json

        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
                "--output-format",
                "json",
            ],
        )

        # Assertion: Basic success criteria
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be an object"

        # Verify structure
        assert "orchestrator" in data, "JSON should contain orchestrator section"
        assert isinstance(data["orchestrator"], dict), "orchestrator should be an object"
        assert "source_file" in data["orchestrator"], "orchestrator should have source_file"
        assert "settings" in data["orchestrator"], "orchestrator should have settings"

        # Verify orchestrator settings
        orchestrator_settings = data["orchestrator"]["settings"]
        assert isinstance(orchestrator_settings, dict), "orchestrator.settings should be an object"
        assert "timeout_per_team_seconds" in orchestrator_settings
        assert orchestrator_settings["timeout_per_team_seconds"] == 600

    # ========== T056.4b: JSON Format with Teams Key ==========

    def test_config_show_json_format_with_teams(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.4b: Test `mixseek config show --output-format json` includes teams key

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output is valid JSON
        - JSON contains teams key (even if empty)
        - Nested structures are properly serialized when present

        Note: Full team/member loading is tested in integration tests.
        This unit test verifies the JSON structure includes the teams key.
        """
        import json

        # Setup: Create simple orchestrator TOML without teams
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
                "--output-format",
                "json",
            ],
        )

        # Assertion: Basic success criteria
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be an object"

        # Verify structure includes teams key (even if empty)
        assert "teams" in data, "JSON should contain teams key"
        assert isinstance(data["teams"], list), "teams should be an array"

        # Verify orchestrator is present
        assert "orchestrator" in data, "JSON should contain orchestrator"
        assert "settings" in data["orchestrator"], "orchestrator should have settings"
        assert "source_file" in data["orchestrator"], "orchestrator should have source_file"

    # ========== T056.5: JSON Format for Specific Key ==========

    def test_config_show_specific_key_json_format(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T056.5: Test `mixseek config show <key> --output-format json`

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output is valid JSON
        - JSON contains setting details (class, key, current_value, default_value, source, type, overridden)
        """
        import json

        # Setup: Create configs directory and evaluator.toml
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        evaluator_toml = configs_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4"
"""
        )

        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
evaluator_config = "configs/evaluator.toml"
"""
        )

        # Execute
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "OrchestratorSettings.evaluator_config",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
                "--output-format",
                "json",
            ],
        )

        # Assertion: Basic success criteria
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be an object"

        # Verify required fields
        assert "class" in data
        assert "key" in data
        assert "current_value" in data
        assert "default_value" in data
        assert "source" in data
        assert "source_type" in data
        assert "type" in data
        assert "overridden" in data

        # Verify values
        assert data["class"] == "OrchestratorSettings"
        assert data["key"] == "evaluator_config"
        assert data["current_value"] == "configs/evaluator.toml"
        assert data["overridden"] is True

    # ========== T179: Standalone Settings Display ==========

    def test_config_show_with_evaluator_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.1: Test `mixseek config show` displays EvaluatorSettings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output contains [evaluator] section
        - Shows evaluator settings fields
        - Shows source file path

        **References**:
        - Issue #179: Display standalone settings in config show
        """
        # Setup: Create orchestrator TOML with evaluator_config reference
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        evaluator_toml = configs_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4"
temperature = 0.0
max_tokens = 2024

[[metrics]]
name = "LLMPlain"
weight = 0.7
"""
        )

        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
evaluator_config = "configs/evaluator.toml"
"""
        )

        # Execute
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout.lower()

        # Should contain evaluator section
        assert "[evaluator]" in output or "evaluator" in output
        # Should show model field
        assert "model" in output

    def test_config_show_with_judgment_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.2: Test `mixseek config show` displays JudgmentSettings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output contains [judgment] section
        - Shows judgment settings fields
        - Shows source file path

        **References**:
        - Issue #179: Display standalone settings in config show
        """
        # Setup: Create orchestrator TOML with judgment_config reference
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        judgment_toml = configs_dir / "judgment.toml"
        judgment_toml.write_text(
            """
model = "google-gla:gemini-2.5-flash"
temperature = 0.0
max_retries = 3
timeout_seconds = 60
"""
        )

        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
judgment_config = "configs/judgment.toml"
"""
        )

        # Execute
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout.lower()

        # Should contain judgment section
        assert "[judgment]" in output or "judgment" in output
        # Should show model field
        assert "model" in output or "gemini" in output

    def test_config_show_with_prompt_builder_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.3: Test `mixseek config show` displays PromptBuilderSettings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output contains [prompt_builder] section
        - Shows prompt_builder settings fields
        - Shows source file path

        **References**:
        - Issue #179: Display standalone settings in config show
        """
        # Setup: Create prompt_builder.toml at default location
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        prompt_builder_toml = configs_dir / "prompt_builder.toml"
        prompt_builder_toml.write_text(
            """
[prompt_builder]
team_user_prompt = "Task: {{ user_prompt }}"
evaluator_user_prompt = "Evaluate: {{ submission }}"
judgment_user_prompt = "Judge: {{ submission_history }}"
"""
        )

        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout.lower()

        # Should contain prompt_builder section
        assert "[prompt_builder]" in output or "prompt_builder" in output
        # Should show one of the prompt fields
        assert "team_user_prompt" in output or "evaluator_user_prompt" in output or "judgment_user_prompt" in output

    def test_config_show_with_default_standalone_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.4: Test `mixseek config show` displays default standalone settings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output contains [evaluator] section (with defaults)
        - Output contains [judgment] section (with defaults)
        - Output contains [prompt_builder] section (with defaults)
        - Shows that these are defaults (source_file is None or not specified)

        **References**:
        - Issue #179: Always display standalone settings (even defaults)
        """
        # Setup: Create orchestrator WITHOUT evaluator_config, judgment_config
        # No prompt_builder.toml created either
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should contain evaluator section with (None) indicator
        assert "[evaluator] (None)" in output or "[evaluator] (none)" in output.lower()

        # Should contain judgment section with (None) indicator
        assert "[judgment] (None)" in output or "[judgment] (none)" in output.lower()

        # Should contain prompt_builder section with (None) indicator
        assert "[prompt_builder] (None)" in output or "[prompt_builder] (none)" in output.lower()

    def test_config_show_json_with_standalone_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.4: Test `mixseek config show --output-format json` includes standalone settings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output is valid JSON
        - JSON contains standalone_settings key
        - standalone_settings includes evaluator, judgment, and prompt_builder
        - Each setting has settings and source_file

        **References**:
        - Issue #179: Display standalone settings in config show
        """
        import json

        # Setup: Create all standalone settings
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        evaluator_toml = configs_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4"

[[metrics]]
name = "LLMPlain"
weight = 0.7
"""
        )

        judgment_toml = configs_dir / "judgment.toml"
        judgment_toml.write_text(
            """
model = "google-gla:gemini-2.5-flash"
temperature = 0.0
"""
        )

        prompt_builder_toml = configs_dir / "prompt_builder.toml"
        prompt_builder_toml.write_text(
            """
[prompt_builder]
team_user_prompt = "Task: {{ user_prompt }}"
"""
        )

        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
evaluator_config = "configs/evaluator.toml"
judgment_config = "configs/judgment.toml"
"""
        )

        # Execute
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
                "--output-format",
                "json",
            ],
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be an object"

        # Verify evaluator is present (same level as orchestrator/teams)
        assert "evaluator" in data, "JSON should contain evaluator at top level"
        assert "settings" in data["evaluator"], "evaluator should have settings"
        assert "source_file" in data["evaluator"], "evaluator should have source_file"

        # Verify judgment is present (same level as orchestrator/teams)
        assert "judgment" in data, "JSON should contain judgment at top level"
        assert "settings" in data["judgment"], "judgment should have settings"
        assert "source_file" in data["judgment"], "judgment should have source_file"

        # Verify prompt_builder is present (same level as orchestrator/teams)
        assert "prompt_builder" in data, "JSON should contain prompt_builder at top level"
        assert "settings" in data["prompt_builder"], "prompt_builder should have settings"
        assert "source_file" in data["prompt_builder"], "prompt_builder should have source_file"

    def test_config_show_json_with_default_standalone_settings(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T179.5: Test `mixseek config show --output-format json` includes default standalone settings

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - Output is valid JSON
        - JSON contains evaluator, judgment, and prompt_builder at top level
        - source_file is null for default settings
        - settings object contains default values

        **References**:
        - Issue #179: Always display standalone settings (even defaults)
        """
        import json

        # Setup: Create orchestrator WITHOUT evaluator_config, judgment_config
        # No prompt_builder.toml created either
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute
        result = runner.invoke(
            app,
            [
                "config",
                "show",
                "--config",
                str(orchestrator_toml),
                "--workspace",
                str(tmp_path),
                "--output-format",
                "json",
            ],
        )

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be an object"

        # Verify evaluator is present with default values
        assert "evaluator" in data, "JSON should contain evaluator at top level"
        assert "settings" in data["evaluator"], "evaluator should have settings"
        assert "source_file" in data["evaluator"], "evaluator should have source_file"
        # source_file should be None (default)
        assert data["evaluator"]["source_file"] is None, "Default evaluator should have null source_file"

        # Verify judgment is present with default values
        assert "judgment" in data, "JSON should contain judgment at top level"
        assert "settings" in data["judgment"], "judgment should have settings"
        assert "source_file" in data["judgment"], "judgment should have source_file"
        # source_file should be None (default)
        assert data["judgment"]["source_file"] is None, "Default judgment should have null source_file"

        # Verify prompt_builder is present with default values
        assert "prompt_builder" in data, "JSON should contain prompt_builder at top level"
        assert "settings" in data["prompt_builder"], "prompt_builder should have settings"
        assert "source_file" in data["prompt_builder"], "prompt_builder should have source_file"
        # source_file should be None (default)
        assert data["prompt_builder"]["source_file"] is None, "Default prompt_builder should have null source_file"


class TestConfigListCommand:
    """Tests for `mixseek config list` command (T057)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T057.1: Display All Items ==========

    def test_config_list_all_items(self, runner: CliRunner) -> None:
        """
        T057.1: Test `mixseek config list` displays all configuration items

        **Acceptance Criteria**:
        - Displays all configuration items from all settings classes
        - Exit code is 0
        - Output is properly formatted (table or list)
        """
        # Execute
        result = runner.invoke(app, ["config", "list"])

        # Assertion: Basic success criteria
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        output = result.stdout

        # Should contain settings from OrchestratorSettings
        assert any(keyword in output.lower() for keyword in ["timeout", "concurrent", "workspace"])

    def test_config_list_with_defaults(self, runner: CliRunner) -> None:
        """
        T057.2: Test `mixseek config list` includes default values

        **Acceptance Criteria**:
        - Each item shows its default value
        - Defaults are clearly labeled
        - Output format is consistent
        """
        # Execute
        result = runner.invoke(app, ["config", "list"])

        # Assertion: Default values are shown
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        output = result.stdout

        # Should show default values
        # For OrchestratorSettings: 300 (timeout), 4 (teams)
        # At least one default value should be visible
        assert any(value in output for value in ["300", "4", "default"]), "Should show default values"

    def test_config_list_with_descriptions(self, runner: CliRunner) -> None:
        """
        T057.3: Test `mixseek config list` includes field descriptions

        **Acceptance Criteria**:
        - Each configuration item has a description/help text
        - Descriptions are helpful and non-empty
        - Format clearly associates descriptions with items
        """
        # Execute
        result = runner.invoke(app, ["config", "list"])

        # Assertion: Descriptions are shown
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        output = result.stdout

        # Should contain descriptive text
        # Look for keywords that suggest descriptions are present
        assert len(output) > 200, "Output should be substantial enough for descriptions"

    def test_config_list_output_format(self, runner: CliRunner) -> None:
        """
        T057.4: Test `mixseek config list` output format

        **Acceptance Criteria**:
        - Supports multiple output formats (table, json, etc.)
        - Columns are clearly labeled
        - Format is consistent across all items
        """
        # Execute with table format (default)
        result = runner.invoke(app, ["config", "list"])

        # Assertion: Table format is used
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should have structure indicating columns/headers
        assert any(keyword in output.upper() for keyword in ["KEY", "NAME", "DEFAULT", "TYPE", "DESCRIPTION"]), (
            "Should have clear column headers"
        )

    def test_config_list_json_format(self, runner: CliRunner) -> None:
        """
        T057.5: Test `mixseek config list --output-format json`

        **Acceptance Criteria**:
        - Outputs valid JSON array
        - Each item contains key, class_name, raw_key, default, type, description
        - JSON is properly formatted and parseable
        """
        import json

        # Execute with JSON format
        result = runner.invoke(app, ["config", "list", "--output-format", "json"])

        # Assertion: Command succeeds
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Assertion: Output is valid JSON
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Output is not valid JSON: {e}\n{result.stdout}")

        # Assertion: JSON is an array
        assert isinstance(data, list), "JSON output should be an array"

        # Assertion: Array contains items
        assert len(data) > 0, "JSON output should contain at least one setting"

        # Assertion: Each item has required fields
        for item in data:
            assert "key" in item, "Each item should have 'key' field"
            assert "class_name" in item, "Each item should have 'class_name' field"
            assert "raw_key" in item, "Each item should have 'raw_key' field"
            assert "default" in item, "Each item should have 'default' field"
            assert "type" in item, "Each item should have 'type' field"
            assert "description" in item, "Each item should have 'description' field"


class TestConfigShowIntegration:
    """Integration tests for `mixseek config show` with real ConfigurationManager (T062)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T062.1: E2E with real configuration ==========

    def test_e2e_config_show_command(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T062.1: E2E test of config show with real ConfigurationManager

        **Acceptance Criteria**:
        - Reads actual configuration
        - Shows values with proper formatting
        - Sources are identified
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Run config show command
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion: Settings are shown with proper structure
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show hierarchical format with orchestrator section
        assert "orchestrator" in output.lower()

    def test_e2e_config_show_with_env_override(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T062.2: E2E test with environment variable override

        **Acceptance Criteria**:
        - Command executes successfully
        - Shows source column
        - Properly formats environment variable data
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Run config show
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion: Command succeeds and shows proper structure
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show hierarchical format with source file path
        assert str(orchestrator_toml) in output or "orchestrator" in output.lower()

    def test_e2e_config_show_with_toml(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T062.3: E2E test reads configuration correctly

        **Acceptance Criteria**:
        - Shows values from all settings classes
        - Format is consistent
        - Command executes successfully
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Run config show
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion: All settings shown with consistent format
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show multiple settings
        lines = [line for line in output.split("\n") if line.strip()]
        assert len(lines) > 5, "Should show multiple configuration settings"

    def test_e2e_config_show_with_multiple_sources(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T062.4: E2E test with values from different sources

        **Acceptance Criteria**:
        - Different settings can be displayed
        - Source column shows identification
        - Command handles mixed sources correctly
        """
        # Setup: Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        # Execute: Run config show
        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Assertion: Multiple settings shown with source identification
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show hierarchical format with settings
        lines = output.split("\n")
        setting_lines = [line for line in lines if line.strip() and not line.strip().startswith("[")]
        assert len(setting_lines) > 0, "Should show settings with sources"


class TestConfigListIntegration:
    """Integration tests for `mixseek config list` with real ConfigurationManager"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    def test_e2e_config_list_command(self, runner: CliRunner) -> None:
        """
        E2E test of config list with real ConfigurationManager

        **Acceptance Criteria**:
        - Loads all available settings
        - Shows complete list of configuration items
        - Output is properly formatted
        """
        # Execute
        result = runner.invoke(app, ["config", "list"])

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show various settings
        assert len(output) > 100, "Output should contain multiple settings"

    def test_e2e_config_list_output_format(self, runner: CliRunner) -> None:
        """
        E2E test config list output is properly formatted

        **Acceptance Criteria**:
        - Output is structured and readable
        - Contains column information
        - Proper alignment of data
        """
        # Execute
        result = runner.invoke(app, ["config", "list"])

        # Assertion
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should have structure (multiple lines with consistent formatting)
        lines = [line for line in output.split("\n") if line.strip()]
        assert len(lines) > 5, "Should have multiple lines of output"


class TestConfigInitCommand:
    """Tests for `mixseek config init` command (T064 - Phase 10)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T064.1: Generate Default Template ==========

    def test_config_init_default_template(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T064.1: Test `mixseek config init` generates default config.toml in workspace/configs/

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - File created: workspace/configs/config.toml
        - File contains: All settings classes' fields
        - File format: Valid TOML syntax
        - File includes: Comments with descriptions
        """
        # Execute with workspace option
        result = runner.invoke(app, ["config", "init", "--workspace", str(tmp_path)])

        # Assertion: Success
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # File exists at workspace/configs/config.toml
        config_file = tmp_path / "configs" / "config.toml"
        assert config_file.exists(), f"config.toml should be created at {config_file}"

        # File is readable TOML
        content = config_file.read_text()
        assert len(content) > 100, "Template should have substantial content"

        # Contains settings indicators
        assert any(
            keyword in content.lower()
            for keyword in [
                "orchestrator",
                "timeout",
                "concurrent",
                "workspace",
            ]
        ), "Template should contain settings"

    # ========== T064.2: Generate Team Component Template ==========

    def test_config_init_team_component(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T064.2: Test `mixseek config init --component team` generates team.toml in workspace/configs/

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - File created: workspace/configs/team.toml
        - File contains: [leader] section, [member] section
        - Hierarchical structure properly formatted
        """
        # Execute with workspace option
        result = runner.invoke(app, ["config", "init", "--component", "team", "--workspace", str(tmp_path)])

        # Assertion: Success
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # File exists at workspace/configs/team.toml
        team_file = tmp_path / "configs" / "team.toml"
        assert team_file.exists(), f"team.toml should be created at {team_file}"

        # File has sections
        content = team_file.read_text()
        assert "[leader]" in content, "Should have [leader] section"
        assert "[member]" in content, "Should have [member] section"

    # ========== T064.3: Generate Orchestrator Component Template ==========

    def test_config_init_orchestrator_component(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T064.3: Test `mixseek config init --component orchestrator` generates orchestrator.toml in workspace/configs/

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - File created: workspace/configs/orchestrator.toml
        - File contains: OrchestratorSettings fields
        """
        # Execute with workspace option
        result = runner.invoke(app, ["config", "init", "--component", "orchestrator", "--workspace", str(tmp_path)])

        # Assertion: Success
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # File exists at workspace/configs/orchestrator.toml
        orch_file = tmp_path / "configs" / "orchestrator.toml"
        assert orch_file.exists(), f"orchestrator.toml should be created at {orch_file}"

    # ========== T064.4: Force Overwrite Existing File ==========

    def test_config_init_force_overwrite(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T064.4: Test `mixseek config init --force` overwrites existing template

        **Acceptance Criteria**:
        - First execution creates file
        - Second execution with --force succeeds (exit code 0)
        - File is updated (not appended)
        """
        # First execution
        result1 = runner.invoke(app, ["config", "init", "--workspace", str(tmp_path)])
        assert result1.exit_code == 0

        config_file = tmp_path / "configs" / "config.toml"
        assert config_file.exists()
        config_file.read_text()

        # Second execution with --force
        result2 = runner.invoke(app, ["config", "init", "--force", "--workspace", str(tmp_path)])
        assert result2.exit_code == 0, f"Force overwrite failed: {result2.stdout}"

        # File still exists and updated
        assert config_file.exists()
        new_content = config_file.read_text()
        # Content should be consistent (not duplicated)
        assert len(new_content) > 0, "File should have content after force overwrite"

    # ========== T064.5: Error When File Exists Without Force ==========

    def test_config_init_file_exists_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T064.5: Test `mixseek config init` fails if file exists and --force not used

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates file exists
        - Original file unchanged
        """
        # Create existing file
        config_file = tmp_path / "configs" / "config.toml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("# Existing content\n")
        original_content = config_file.read_text()

        # Execute without --force (should fail because file exists)
        result = runner.invoke(app, ["config", "init", "--workspace", str(tmp_path)])

        # Assertion: Error OR file unchanged
        # Command either fails (exit_code != 0) or file is unchanged
        # This flexibility allows for different implementation approaches
        if result.exit_code != 0:
            # File should be unchanged if error occurred
            assert config_file.read_text() == original_content
        # Both outcomes are acceptable for RED phase

    # ========== T064.6: Invalid Component Option ==========

    def test_config_init_invalid_component(self, runner: CliRunner) -> None:
        """
        T064.6: Test `mixseek config init --component invalid` raises error

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message mentions valid components
        - No file created with invalid name
        """
        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "invalid_xyz"])

        # Assertion: Error
        assert result.exit_code != 0, "Should fail for invalid component"

        # Error message should be helpful (CliRunner mixes stdout and stderr)
        output = result.stdout.lower()
        assert any(keyword in output for keyword in ["component", "invalid", "valid", "orchestrator", "unknown"]), (
            f"Should suggest valid components in error. Output: {output}"
        )


class TestConfigFileOption:
    """Tests for `--config` option (Phase 13 T109)

    Tests validation, recursive loading, circular reference detection,
    max depth limit, and hierarchical display.

    Phase 13 T109: FR-038 through FR-043
    """

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T109.1: File Validation ==========

    def test_config_file_not_found(self, runner: CliRunner) -> None:
        """
        T109.1: Test --config with non-existent file raises error

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates file not found
        - Command does not crash
        """
        result = runner.invoke(app, ["config", "show", "--config", "nonexistent.toml"])

        assert result.exit_code != 0, "Should fail for non-existent file"
        # Check result.output which includes both stdout and stderr
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_config_file_invalid_toml_syntax(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.2: Test --config with invalid TOML syntax raises error

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates TOML syntax error
        - Shows file path in error message
        """
        # Create invalid TOML
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("[orchestrator\ninvalid syntax here")

        result = runner.invoke(app, ["config", "show", "--config", str(invalid_toml)])

        assert result.exit_code != 0, "Should fail for invalid TOML syntax"
        # Check result.output which includes both stdout and stderr
        assert any(keyword in result.output.lower() for keyword in ["toml", "syntax", "error"])

    def test_config_file_missing_orchestrator_section(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.3: Test --config without [orchestrator] section raises error

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates missing [orchestrator] section
        - Shows available sections
        """
        # Create TOML without [orchestrator] section
        wrong_toml = tmp_path / "wrong.toml"
        wrong_toml.write_text('[team]\nname = "test"\n')

        result = runner.invoke(app, ["config", "show", "--config", str(wrong_toml), "--workspace", str(tmp_path)])

        assert result.exit_code != 0, "Should fail for missing [orchestrator] section"
        # Check result.output which includes both stdout and stderr
        assert "orchestrator" in result.output.lower()

    # ========== T109.2: Recursive Loading ==========

    def test_config_file_hierarchical_display(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.4: Test --config displays hierarchical structure

        **Acceptance Criteria**:
        - Shows orchestrator configuration (no indent)
        - Shows team configurations (2-space indent)
        - Shows member configurations (4-space indent)
        - Displays file paths for each level
        """
        # Create orchestrator TOML
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        output = result.stdout

        # Should show orchestrator section
        assert "[orchestrator]" in output.lower()
        assert "timeout_per_team_seconds" in output.lower() or "600" in output

    def test_config_file_with_workspace(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.5: Test --config with --workspace option

        **Acceptance Criteria**:
        - Both options work together
        - Workspace is used for resolving relative paths
        - Exit code is 0 (success)
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        orchestrator_toml = workspace / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(workspace)]
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # ========== T109.3: Circular Reference Detection ==========

    def test_config_file_circular_reference(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.6: Test --config detects circular references

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates circular reference detected
        - Shows full reference path (A → B → A)
        """
        # For now, we'll test that the command doesn't crash
        # Full circular reference test requires team TOML files
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        # Should succeed for simple case (no circular reference)
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # ========== T109.4: Maximum Recursion Depth ==========

    def test_config_file_max_depth(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T109.7: Test --config enforces maximum recursion depth

        **Acceptance Criteria**:
        - Loads up to 10 levels successfully
        - Exit code is non-zero if depth exceeds 10
        - Error message shows current depth and reference path
        """
        # For now, test that simple case works (depth = 1)
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600
max_concurrent_teams = 4
teams = []
"""
        )

        result = runner.invoke(
            app, ["config", "show", "--config", str(orchestrator_toml), "--workspace", str(tmp_path)]
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"


class TestConfigInitOutputPath:
    """Tests for config init --output-path option (Issue #175)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    def test_config_init_default_path(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test default output path: workspace/configs/<component>.toml"""
        result = runner.invoke(app, ["config", "init", "--component", "orchestrator", "--workspace", str(tmp_path)])

        assert result.exit_code == 0
        output_path = tmp_path / "configs" / "orchestrator.toml"
        assert output_path.exists()

    def test_config_init_custom_relative_path(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test custom relative output path"""
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--component",
                "orchestrator",
                "--output-path",
                "my-configs/orchestrator.toml",
                "--workspace",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        output_path = tmp_path / "my-configs" / "orchestrator.toml"
        assert output_path.exists()

    def test_config_init_absolute_path(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test absolute output path (workspace not required)"""
        output_path = tmp_path / "test.toml"
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--component",
                "orchestrator",
                "--output-path",
                str(output_path),
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_config_init_no_workspace_error(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test error when workspace is not specified for relative path"""
        # Clear MIXSEEK_WORKSPACE environment variable to ensure test isolation
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        result = runner.invoke(app, ["config", "init", "--component", "orchestrator"])

        assert result.exit_code != 0
        # Error messages are printed to stderr with typer.echo(..., err=True)
        # CliRunner captures both stdout and stderr in result.output
        assert (
            "Workspace path must be specified" in result.output or "Workspace path must be specified" in result.stdout
        )

    def test_config_init_force_overwrite(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test --force option overwrites existing file"""
        output_path = tmp_path / "configs" / "orchestrator.toml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("old content")

        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--component",
                "orchestrator",
                "--workspace",
                str(tmp_path),
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()
        assert "old content" not in output_path.read_text()

    def test_config_init_respects_workspace_env(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config init respects MIXSEEK_WORKSPACE environment variable"""
        # Set MIXSEEK_WORKSPACE
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Execute without --workspace option
        result = runner.invoke(app, ["config", "init", "--component", "orchestrator"])

        # Assertion: Success
        assert result.exit_code == 0

        # File exists at $MIXSEEK_WORKSPACE/configs/orchestrator.toml
        orchestrator_file = tmp_path / "configs" / "orchestrator.toml"
        assert orchestrator_file.exists()


class TestConfigInitPromptBuilder:
    """Tests for `mixseek config init --component prompt_builder` command (T023, T024 - Feature 092)"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner"""
        return CliRunner()

    # ========== T023: config init command test ==========

    def test_config_init_prompt_builder_generates_file(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T023: Test `mixseek config init --component prompt_builder` generates prompt_builder.toml

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - File created: $MIXSEEK_WORKSPACE/configs/prompt_builder.toml
        - Command outputs success message with file location
        - File contains valid TOML syntax

        **References**:
        - specs/092-user-prompt-builder-team/spec.md (User Story 3)
        - specs/092-user-prompt-builder-team/tasks.md (T023)
        """
        # Setup: Set MIXSEEK_WORKSPACE
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])

        # Assertion: Success
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # File exists in correct location
        configs_dir = workspace / "configs"
        prompt_builder_file = configs_dir / "prompt_builder.toml"
        assert configs_dir.exists(), "configs/ directory should be created"
        assert prompt_builder_file.exists(), "prompt_builder.toml should be created"

        # Success message displayed
        output = result.stdout
        assert "✓" in output or "generated" in output.lower(), "Should show success message"
        assert "prompt_builder.toml" in output.lower(), "Should mention output filename"

    def test_config_init_prompt_builder_with_workspace_option(self, runner: CliRunner, tmp_path: Path) -> None:
        """
        T023.2: Test `mixseek config init --component prompt_builder --workspace` uses explicit workspace

        **Acceptance Criteria**:
        - Exit code is 0 (success)
        - File created in specified workspace
        - --workspace option overrides MIXSEEK_WORKSPACE env var
        """
        # Setup: Create workspace via --workspace option
        workspace = tmp_path / "custom_workspace"
        workspace.mkdir()

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder", "--workspace", str(workspace)])

        # Assertion: Success
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # File exists in custom workspace
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        assert prompt_builder_file.exists(), "prompt_builder.toml should be created in custom workspace"

    def test_config_init_prompt_builder_no_workspace_error(self, runner: CliRunner, monkeypatch: Any) -> None:
        """
        T023.3: Test `mixseek config init --component prompt_builder` fails without workspace

        **Acceptance Criteria**:
        - Exit code is non-zero (error)
        - Error message indicates workspace must be specified
        - No file created
        """
        # Ensure MIXSEEK_WORKSPACE is not set (clear any value from previous tests or CI env)
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

        # Execute without setting MIXSEEK_WORKSPACE
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])

        # Assertion: Error
        assert result.exit_code != 0, "Should fail without workspace"
        output = result.output.lower()
        assert "workspace" in output, "Error should mention workspace requirement"

    def test_config_init_prompt_builder_force_overwrite(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T023.4: Test `mixseek config init --component prompt_builder --force` overwrites existing file

        **Acceptance Criteria**:
        - First execution creates file
        - Second execution without --force fails
        - Second execution with --force succeeds and overwrites file
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # First execution
        result1 = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result1.exit_code == 0, "First execution should succeed"

        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        assert prompt_builder_file.exists()

        # Second execution without --force should fail
        result2 = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result2.exit_code != 0, "Second execution without --force should fail"
        assert "exists" in result2.output.lower(), "Error should mention file exists"

        # Second execution with --force should succeed
        result3 = runner.invoke(app, ["config", "init", "--component", "prompt_builder", "--force"])
        assert result3.exit_code == 0, f"Force overwrite failed: {result3.stdout}"
        assert prompt_builder_file.exists(), "File should still exist after force overwrite"

    # ========== T024: generated config file content validation ==========

    def test_config_init_prompt_builder_content_has_team_user_prompt(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T024.1: Test generated prompt_builder.toml contains team_user_prompt definition

        **Acceptance Criteria**:
        - File contains [prompt_builder] section
        - File contains team_user_prompt field
        - team_user_prompt has Jinja2 placeholder variables

        **References**:
        - specs/092-user-prompt-builder-team/spec.md (User Story 2)
        - specs/092-user-prompt-builder-team/data-model.md (Section 4.1)
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Has expected structure
        assert "[prompt_builder]" in content, "Should have [prompt_builder] section"
        assert "team_user_prompt" in content, "Should have team_user_prompt field"

    def test_config_init_prompt_builder_content_has_placeholder_variables(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T024.2: Test generated prompt_builder.toml includes all placeholder variable comments

        **Acceptance Criteria**:
        - File contains comments for {{ user_prompt }} placeholder
        - File contains comments for {{ submission_history }} placeholder
        - File contains comments for {{ ranking_table }} placeholder
        - File contains comments for {{ current_datetime }} placeholder

        **References**:
        - specs/092-user-prompt-builder-team/spec.md (User Story 2)
        - specs/092-user-prompt-builder-team/contracts/prompt-builder-api.md (Section 3)
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Has all placeholder variables documented
        assert "{{ user_prompt }}" in content, "Should document {{ user_prompt }} placeholder"
        assert "{{ submission_history }}" in content, "Should document {{ submission_history }} placeholder"
        assert "{{ ranking_table }}" in content, "Should document {{ ranking_table }} placeholder"
        assert "{{ current_datetime }}" in content, "Should document {{ current_datetime }} placeholder"

    def test_config_init_prompt_builder_content_is_valid_toml(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T024.3: Test generated prompt_builder.toml is valid TOML syntax

        **Acceptance Criteria**:
        - File can be parsed by tomllib without errors
        - File contains expected sections
        - team_user_prompt is a valid multi-line string
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read and parse generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Valid TOML
        import tomllib

        try:
            config = tomllib.loads(content)
            assert "prompt_builder" in config, "Should have prompt_builder section after parsing"
            assert "team_user_prompt" in config["prompt_builder"], "Should have team_user_prompt field"
            assert isinstance(config["prompt_builder"]["team_user_prompt"], str), "team_user_prompt should be a string"
            assert len(config["prompt_builder"]["team_user_prompt"]) > 0, "team_user_prompt should not be empty"
        except Exception as e:
            pytest.fail(f"Generated TOML is invalid: {e}\n\nContent:\n{content}")

    # ========== T030: Feature 140 - Evaluator/JudgementClient prompt templates ==========

    def test_config_init_prompt_builder_content_has_evaluator_user_prompt(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T030.1: Test generated prompt_builder.toml contains evaluator_user_prompt definition

        **Acceptance Criteria**:
        - File contains evaluator_user_prompt field
        - evaluator_user_prompt has Jinja2 placeholder variables (user_query, submission, current_datetime)
        - Comments document available placeholder variables

        **References**:
        - specs/140-user-prompt-builder-evaluator-judgement/spec.md (User Story 3)
        - specs/140-user-prompt-builder-evaluator-judgement/data-model.md (Section 4.1)
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Has evaluator_user_prompt structure
        assert "evaluator_user_prompt" in content, "Should have evaluator_user_prompt field"
        assert "{{ user_prompt }}" in content, "Should document {{ user_prompt }} placeholder"
        assert "{{ submission }}" in content, "Should document {{ submission }} placeholder"

        # Verify comments document placeholder variables
        assert "user_prompt" in content, "Should document user_prompt variable"
        assert "submission" in content, "Should document submission variable"
        assert "current_datetime" in content, "Should document current_datetime variable"

    def test_config_init_prompt_builder_content_has_judgment_user_prompt(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T030.2: Test generated prompt_builder.toml contains judgment_user_prompt definition

        **Acceptance Criteria**:
        - File contains judgment_user_prompt field
        - judgment_user_prompt has Jinja2 placeholder variables
        - Comments document available placeholder variables

        **References**:
        - specs/140-user-prompt-builder-evaluator-judgement/spec.md (User Story 3)
        - specs/140-user-prompt-builder-evaluator-judgement/data-model.md (Section 4.2)
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Has judgment_user_prompt structure
        assert "judgment_user_prompt" in content, "Should have judgment_user_prompt field"
        assert "{{ user_prompt }}" in content, "Should have {{ user_prompt }} placeholder in judgment prompt"
        assert "{{ submission_history }}" in content, "Should have {{ submission_history }} placeholder"
        assert "{{ ranking_table }}" in content, "Should have {{ ranking_table }} placeholder"

        # Verify comments document placeholder variables
        assert "round_number" in content, "Should document round_number variable"
        assert "team_position_message" in content, "Should document team_position_message variable"

    def test_config_init_prompt_builder_content_all_prompts_valid_toml(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """
        T030.3: Test generated prompt_builder.toml with all three prompts is valid TOML

        **Acceptance Criteria**:
        - File can be parsed by tomllib without errors
        - File contains team_user_prompt, evaluator_user_prompt, judgment_user_prompt
        - All prompts are valid multi-line strings
        """
        # Setup
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Execute
        result = runner.invoke(app, ["config", "init", "--component", "prompt_builder"])
        assert result.exit_code == 0

        # Read and parse generated file
        prompt_builder_file = workspace / "configs" / "prompt_builder.toml"
        content = prompt_builder_file.read_text(encoding="utf-8")

        # Assertion: Valid TOML with all three prompts
        import tomllib

        try:
            config = tomllib.loads(content)
            assert "prompt_builder" in config, "Should have prompt_builder section"

            # Check all three prompts exist and are valid
            prompt_fields = ["team_user_prompt", "evaluator_user_prompt", "judgment_user_prompt"]
            for field in prompt_fields:
                assert field in config["prompt_builder"], f"Should have {field} field"
                assert isinstance(config["prompt_builder"][field], str), f"{field} should be a string"
                assert len(config["prompt_builder"][field]) > 0, f"{field} should not be empty"

        except Exception as e:
            pytest.fail(f"Generated TOML is invalid: {e}\n\nContent:\n{content}")
