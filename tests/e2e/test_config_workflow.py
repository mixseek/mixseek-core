"""End-to-end tests for Configuration Manager workflow (T088).

このテストは、実際のユーザーシナリオでConfiguration Managerが正しく動作することを検証します：
- mixseek team コマンドのワークフロー
- mixseek exec コマンドのCLIオーバーライド
- mixseek ui コマンドの環境変数
- 優先順位チェーン: CLI > ENV > .env > TOML > defaults
- トレーサビリティ: ソース追跡
- User Stories (US1-US7) のE2E検証
- SC-007: すべてのモジュールでConfigurationManager使用
"""

from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import OrchestratorSettings, UISettings


class TestPriorityChainE2E:
    """優先順位チェーンのE2Eテスト: CLI > ENV > .env > TOML > defaults。"""

    def test_cli_overrides_env_and_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI引数が環境変数とTOMLを上書きする（US1準拠）。"""
        # Arrange: Create workspace with .env and TOML
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # .env file
        env_file = workspace / ".env"
        env_file.write_text("MIXSEEK_WORKSPACE=/env/workspace\n")

        # Set environment variable (higher priority than .env)
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path / "env_workspace"))

        # Act: CLI argument (highest priority)
        cli_workspace = tmp_path / "cli_workspace"
        cli_workspace.mkdir()
        manager = ConfigurationManager(workspace=cli_workspace)

        # Load settings
        orchestrator_settings = manager.load_settings(OrchestratorSettings)

        # Assert: CLI workspace wins
        assert orchestrator_settings.workspace_path == cli_workspace

    def test_env_overrides_toml_and_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """環境変数がTOMLとデフォルト値を上書きする（US2準拠）。"""
        # Arrange: Set environment variable (use MIXSEEK_WORKSPACE_PATH for OrchestratorSettings)
        workspace = tmp_path / "env_workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        # Act: Load settings without CLI args
        manager = ConfigurationManager(workspace=None)
        orchestrator_settings = manager.load_settings(OrchestratorSettings)

        # Assert: ENV workspace wins
        assert orchestrator_settings.workspace_path == workspace


class TestTeamCommandWorkflow:
    """mixseek team コマンドのE2Eワークフロー。"""

    def test_team_command_loads_team_config(self, tmp_path: Path) -> None:
        """team.tomlを正しく読み込める（US3準拠）。"""
        # Arrange: Create team.toml
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "e2e-test-team"
team_name = "E2E Test Team"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Agent 1"
system_instruction = "You are agent1"
"""
        )

        # Act: Load team config via ConfigurationManager
        manager = ConfigurationManager(workspace=workspace)
        team_settings = manager.load_team_settings(Path("team.toml"))

        # Assert: Team config loaded correctly
        assert team_settings.team_id == "e2e-test-team"
        assert team_settings.team_name == "E2E Test Team"
        assert len(team_settings.members) == 1
        assert team_settings.members[0].agent_name == "agent1"  # members is list[MemberAgentSettings]

    def test_team_command_with_workspace_override(self, tmp_path: Path) -> None:
        """--workspaceオプションでワークスペースを上書きできる（US1準拠）。"""
        # Arrange: Create two workspaces
        workspace1 = tmp_path / "workspace1"
        workspace1.mkdir()
        workspace2 = tmp_path / "workspace2"
        workspace2.mkdir()

        # Team config in workspace2
        team_toml = workspace2 / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "workspace2-team"
team_name = "Workspace 2 Team"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Agent 1"
"""
        )

        # Act: Load with workspace2 override
        manager = ConfigurationManager(workspace=workspace2)
        team_settings = manager.load_team_settings(Path("team.toml"))

        # Assert: Workspace2 team loaded
        assert team_settings.team_id == "workspace2-team"


class TestExecCommandWorkflow:
    """mixseek exec コマンドのE2Eワークフロー。"""

    def test_exec_command_loads_orchestrator_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """orchestrator.tomlを正しく読み込める（US4準拠, FR-011）。"""
        from mixseek.orchestrator import load_orchestrator_settings

        # Arrange: Clear environment variables to avoid interference
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: Create orchestrator.toml
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        orchestrator_toml = workspace / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "team1.toml"

[[orchestrator.teams]]
config = "team2.toml"
"""
        )

        # Act: Load orchestrator settings (FR-011: direct OrchestratorSettings)
        orchestrator_settings = load_orchestrator_settings(orchestrator_toml, workspace=workspace)

        # Assert: Settings loaded correctly
        assert orchestrator_settings.timeout_per_team_seconds == 600
        assert len(orchestrator_settings.teams) == 2

    def test_exec_command_workspace_resolution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """workspace解決が正しく動作する（Article 9準拠）。"""
        # Arrange: Set MIXSEEK_WORKSPACE_PATH (correct env var for OrchestratorSettings)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace))

        # Act: Load OrchestratorSettings without explicit workspace
        manager = ConfigurationManager(workspace=None)
        orchestrator_settings = manager.load_settings(OrchestratorSettings)

        # Assert: Workspace resolved from ENV
        assert orchestrator_settings.workspace_path == workspace


class TestUICommandWorkflow:
    """mixseek ui コマンドのE2Eワークフロー。"""

    def test_ui_command_loads_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """UISettingsを正しく読み込める（US5準拠）。"""
        # Arrange: Set environment variables
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_UI__WORKSPACE_PATH", str(workspace))
        monkeypatch.setenv("MIXSEEK_UI__PORT", "9000")

        # Act: Load UI settings
        manager = ConfigurationManager(workspace=None)
        ui_settings = manager.load_settings(UISettings)

        # Assert: Settings loaded from ENV
        assert ui_settings.workspace_path == workspace
        assert ui_settings.port == 9000

    def test_ui_command_cli_port_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--portオプションでポートを上書きできる（US1準拠）。"""
        # Arrange: Set ENV port and workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.setenv("MIXSEEK_UI__WORKSPACE_PATH", str(workspace))
        monkeypatch.setenv("MIXSEEK_UI__PORT", "8000")

        # Act: Load with CLI override via cli_args
        manager = ConfigurationManager(workspace=None, cli_args={"port": 9999})
        ui_settings = manager.load_settings(UISettings)

        # Assert: CLI port wins, workspace from ENV
        assert ui_settings.workspace_path == workspace
        assert ui_settings.port == 9999


class TestTraceabilityE2E:
    """トレーサビリティのE2Eテスト: ソース追跡機能。"""

    def test_team_settings_source_traces(self, tmp_path: Path) -> None:
        """TeamSettingsのソース追跡が動作する（US6準拠）。"""
        # Arrange: Create team.toml
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "trace-test"
team_name = "Trace Test"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 8000
tool_description = "Agent 1"
"""
        )

        # Act: Load team settings with tracing
        manager = ConfigurationManager(workspace=workspace)
        team_settings = manager.load_team_settings(Path("team.toml"))

        # Assert: Source traces exist
        assert hasattr(team_settings, "__source_traces__")
        traces = getattr(team_settings, "__source_traces__")
        assert isinstance(traces, dict)

        # Verify specific field traces
        if "team_id" in traces:
            trace = traces["team_id"]
            assert trace.source_type == "toml"
            assert trace.value == "trace-test"
            assert "team.toml" in trace.source_name


class TestBackwardCompatibilityE2E:
    """後方互換性のE2Eテスト（FR-020）。"""

    def test_legacy_evaluation_config_api(self, tmp_path: Path) -> None:
        """EvaluationConfig.from_toml_file()が動作する（FR-020準拠）。"""
        from mixseek.models.evaluation_config import EvaluationConfig

        # Arrange: Create legacy evaluator.toml
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        configs_dir = workspace / "configs"
        configs_dir.mkdir()
        evaluator_toml = configs_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.3
max_tokens = 3000
max_retries = 5

[[metrics]]
name = "TestMetric"
weight = 1.0
"""
        )

        # Act: Use legacy API
        evaluation_config = EvaluationConfig.from_toml_file(workspace)

        # Assert: Legacy API still works
        assert evaluation_config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluation_config.llm_default.temperature == 0.3
        assert evaluation_config.llm_default.max_retries == 5


class TestArticle9ComplianceE2E:
    """Article 9準拠のE2Eテスト: 暗黙的なフォールバック禁止。"""

    def test_no_workspace_raises_explicit_error(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """workspace未指定時に明示的エラー（Article 9準拠）。"""
        from pydantic_core import ValidationError

        # Arrange: Clear environment variables to ensure workspace is truly not specified
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Act & Assert: Should raise explicit error (ValidationError)
        with pytest.raises(ValidationError) as exc_info:
            manager = ConfigurationManager(workspace=None)
            manager.load_settings(OrchestratorSettings)

        # Verify error message identifies missing workspace_path field
        error_msg = str(exc_info.value)
        assert "workspace_path" in error_msg
        assert "Field required" in error_msg

    def test_load_team_config_no_implicit_cwd(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """load_team_config()が暗黙的にCWDを使わない（Article 9準拠 - T078 fix）。"""
        from mixseek.agents.leader.config import load_team_config
        from mixseek.exceptions import WorkspacePathNotSpecifiedError

        # Arrange: Clear environment variables to ensure workspace is truly not specified
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Act & Assert: Should raise explicit error, not fall back to CWD
        with pytest.raises(WorkspacePathNotSpecifiedError):
            load_team_config(Path("team.toml"), workspace=None)


class TestMemberAgentConfigGenerationE2E:
    """MemberAgentConfig生成の一貫性テスト（Issue #146対応）。"""

    def test_member_settings_to_config_preserves_details(self, tmp_path: Path) -> None:
        """member_settings_to_config()が詳細設定を保持する（Issue #146準拠）。"""
        from mixseek.config.member_agent_loader import member_settings_to_config
        from mixseek.config.schema import MemberAgentSettings

        # Arrange: MemberAgentSettings with detailed configuration
        member_settings = MemberAgentSettings(
            agent_name="test_agent",
            agent_type="plain",
            model="google-gla:gemini-2.5-flash-lite",
            temperature=0.5,
            max_tokens=8000,
            tool_description="Test Agent",
            system_instruction="Test instruction",
        )

        # Act: Convert to MemberAgentConfig
        member_config = member_settings_to_config(member_settings, agent_data=None)

        # Assert: All fields preserved
        assert member_config.name == "test_agent"
        assert member_config.type == "plain"
        assert member_config.model == "google-gla:gemini-2.5-flash-lite"
        assert member_config.temperature == 0.5
        assert member_config.max_tokens == 8000
        assert member_config.description == ""  # agent_data=Noneなのでデフォルト
        assert member_config.system_instruction == "Test instruction"

        # Note: retry_config and usage_limits have been removed (delegated to pydantic_ai)
        # tool_settings is now optional (None by default) per PR#155 refactoring

    def test_team_command_preserves_member_agent_details(self, tmp_path: Path) -> None:
        """team commandがMember Agent詳細設定を保持する（Issue #146対応）。"""
        from mixseek.config import ConfigurationManager
        from mixseek.config.member_agent_loader import member_settings_to_config

        # Arrange: Create team.toml with member configuration
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "issue146-test"
team_name = "Issue 146 Test"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Agent 1"
system_instruction = "You are agent1"
"""
        )

        # Act: Load team settings and convert member
        manager = ConfigurationManager(workspace=workspace)
        team_settings = manager.load_team_settings(team_toml)
        member_settings = team_settings.members[0]
        member_config = member_settings_to_config(member_settings, agent_data=None)

        # Assert: Member config preserves all settings
        assert member_config.name == "agent1"
        assert member_config.temperature == 0.2
        assert member_config.max_tokens == 4096
        assert member_config.system_instruction == "You are agent1"

        # Note: retry_config and usage_limits have been removed (delegated to pydantic_ai)
        # tool_settings is now optional (None by default) per PR#155 refactoring


class TestUserStoriesE2E:
    """User Stories (US1-US7) のE2Eテスト。"""

    def test_us1_cli_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """US1: 開発者・運用者・ユーザが環境変数で設定を上書き。"""
        # Arrange: ENV variable
        workspace_env = tmp_path / "env_workspace"
        workspace_env.mkdir()
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace_env))

        # CLI override
        workspace_cli = tmp_path / "cli_workspace"
        workspace_cli.mkdir()

        # Act: CLI wins
        manager = ConfigurationManager(workspace=workspace_cli)
        settings = manager.load_settings(OrchestratorSettings)

        # Assert
        assert settings.workspace_path == workspace_cli

    def test_us3_config_show_equivalent(self, tmp_path: Path) -> None:
        """US3: 開発者が現在の設定値を確認（mixseek config show相当）。"""
        # Arrange: Workspace with settings
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Act: Load settings
        manager = ConfigurationManager(workspace=workspace)
        settings = manager.load_settings(OrchestratorSettings)

        # Assert: Can inspect all settings
        assert settings.workspace_path == workspace
        assert settings.timeout_per_team_seconds >= 10  # Default value check

    def test_us6_source_tracking(self, tmp_path: Path) -> None:
        """US6: 運用者が設定値の出所をトレース。"""
        # Arrange: Team config
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "us6-test"
team_name = "US6 Test"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Agent 1"
"""
        )

        # Act: Load with tracing
        manager = ConfigurationManager(workspace=workspace)
        team_settings = manager.load_team_settings(Path("team.toml"))

        # Assert: Source traces available
        traces = getattr(team_settings, "__source_traces__", {})
        assert len(traces) > 0  # At least some fields have traces
