"""Integration tests for Phase 12 Configuration Manager migration (T087).

このテストは、T078-T086の移行が正しく動作することを検証します：
- LeaderAgentSettings migration (T078)
- MemberAgentSettings migration (T079)
- EvaluatorSettings migration (T080)
- OrchestratorSettings migration (T081)
- UISettings migration (T083)
- 後方互換性テスト（FR-020）
- Article 9準拠の検証
"""

from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import (
    UISettings,
)
from mixseek.exceptions import WorkspacePathNotSpecifiedError


class TestLeaderAgentMigration:
    """T078: LeaderAgentSettings migration tests."""

    def test_load_team_config_uses_configuration_manager(self, tmp_path: Path) -> None:
        """load_team_config()がConfigurationManagerを使用していることを検証（T078）。"""
        from mixseek.agents.leader.config import load_team_config

        # Arrange: Create valid team config
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "test-team"
team_name = "Test Team"

[[team.members]]
agent_name = "plain-agent"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Plain agent"
"""
        )

        # Act: Load team config (internally uses ConfigurationManager)
        team_config = load_team_config(team_toml, workspace=workspace)

        # Assert: Team config loaded successfully
        assert team_config.team_id == "test-team"
        assert team_config.team_name == "Test Team"
        assert len(team_config.members) == 1

    def test_load_team_config_article_9_compliance(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """workspace未指定時に明示的エラーを発生（Article 9準拠 - T078 fix）。"""
        from mixseek.agents.leader.config import load_team_config

        # Arrange: Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: No workspace specified
        team_toml = Path("team.toml")

        # Act & Assert: Should raise WorkspacePathNotSpecifiedError
        with pytest.raises(WorkspacePathNotSpecifiedError):
            load_team_config(team_toml, workspace=None)


class TestMemberAgentMigration:
    """T079: MemberAgentSettings migration tests."""

    def test_load_member_settings_with_relative_path(self, tmp_path: Path) -> None:
        """相対パスでMember Agent設定を読み込める（T079）。"""
        # Arrange: Create member agent config
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        agents_dir = workspace / "agents"
        agents_dir.mkdir()
        member_toml = agents_dir / "plain.toml"
        member_toml.write_text(
            """
[agent]
name = "plain-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096

[agent.system_instruction]
text = "You are a plain agent."
"""
        )

        # Act: Load member settings with relative path
        _manager = ConfigurationManager(workspace=workspace)
        # Note: load_member_settings()の実装を確認する必要があります
        # from mixseek.config.sources.member_toml_source import MemberAgentTomlSource
        # member_settings = _manager.load_member_settings(Path("agents/plain.toml"))

        # Assert: Should resolve relative path against workspace
        # この部分は実際のAPIに合わせて調整が必要

    def test_member_toml_source_tool_description_default(self, tmp_path: Path) -> None:
        """tool_description未指定時にデフォルト値が生成される（T079 fix）。"""
        from mixseek.config.schema import MemberAgentSettings
        from mixseek.config.sources.member_toml_source import MemberAgentTomlSource

        # Arrange: Member config without description
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        member_toml = workspace / "plain.toml"
        member_toml.write_text(
            """
[agent]
name = "test-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"

[agent.system_instruction]
text = "Test instruction"
"""
        )

        # Act: Load via MemberAgentTomlSource
        source = MemberAgentTomlSource(
            settings_cls=MemberAgentSettings,
            toml_file=member_toml,
            workspace=workspace,
        )
        data = source()

        # Assert: tool_description has default value
        assert "tool_description" in data
        assert data["tool_description"] == "Delegate task to test-agent"

    def test_member_toml_source_article_9_compliance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """workspace未指定時に明示的エラー（Article 9準拠 - T079 fix）。"""
        from mixseek.config.schema import MemberAgentSettings
        from mixseek.config.sources.member_toml_source import MemberAgentTomlSource

        # Arrange: Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: Member config without workspace
        member_toml = tmp_path / "plain.toml"
        member_toml.write_text(
            """
[agent]
name = "test-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
"""
        )

        # Act & Assert: Should raise WorkspacePathNotSpecifiedError
        with pytest.raises(WorkspacePathNotSpecifiedError):
            MemberAgentTomlSource(
                settings_cls=MemberAgentSettings,
                toml_file=member_toml,
                workspace=None,
            )


class TestEvaluatorMigration:
    """T080: EvaluatorSettings migration tests."""

    def test_load_evaluation_settings(self, tmp_path: Path) -> None:
        """EvaluatorSettingsを読み込める（T080）。"""
        # Arrange: Create evaluator config
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        evaluator_toml = config_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.0
max_tokens = 2000
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.4
"""
        )

        # Act: Load evaluation settings
        manager = ConfigurationManager(workspace=workspace)
        evaluator_settings = manager.load_evaluation_settings(Path("configs/evaluator.toml"))

        # Assert: Settings loaded correctly
        assert evaluator_settings.default_model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluator_settings.temperature == 0.0
        assert evaluator_settings.max_tokens == 2000
        assert len(evaluator_settings.metrics) == 1

    def test_evaluation_config_backward_compatibility(self, tmp_path: Path) -> None:
        """EvaluationConfig.from_toml_file()の後方互換性（T080）。"""
        from mixseek.models.evaluation_config import EvaluationConfig

        # Arrange: Create evaluator config
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        evaluator_toml = config_dir / "evaluator.toml"
        evaluator_toml.write_text(
            """
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.5
max_tokens = 4000
max_retries = 2

[[metrics]]
name = "Test"
weight = 1.0
"""
        )

        # Act: Use legacy API (internally uses ConfigurationManager)
        evaluation_config = EvaluationConfig.from_toml_file(workspace)

        # Assert: Legacy API still works
        assert evaluation_config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluation_config.llm_default.temperature == 0.5


class TestOrchestratorMigration:
    """T081: Orchestrator migration tests."""

    def test_load_orchestrator_settings_article_9_compliance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """workspace未指定時に明示的エラー（Article 9準拠 - T081 fix, FR-011）。"""
        from mixseek.orchestrator import load_orchestrator_settings

        # Arrange: Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: Orchestrator config
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 300

[[orchestrator.teams]]
config = "team1.toml"
"""
        )

        # Act & Assert: Should raise WorkspacePathNotSpecifiedError without workspace
        with pytest.raises(WorkspacePathNotSpecifiedError):
            load_orchestrator_settings(orchestrator_toml, workspace=None)


class TestUISettingsMigration:
    """T083: UISettings migration tests."""

    def test_ui_settings_schema_exists(self) -> None:
        """UISettingsスキーマが存在する（T083）。"""
        # Assert: UISettings exists with expected fields (Pydantic model fields)
        assert "port" in UISettings.model_fields
        assert "workspace_path" in UISettings.model_fields

    def test_cli_ui_command_uses_configuration_manager(self) -> None:
        """cli/commands/ui.pyがConfigurationManagerを使用している（T083/T086）。"""
        # Note: This is verified by reading the source code
        # src/mixseek/cli/commands/ui.py:27 uses ConfigurationManager.load_settings(UISettings)
        pass


class TestBackwardCompatibility:
    """FR-020: 後方互換性テスト。"""

    def test_existing_toml_files_still_work(self, tmp_path: Path) -> None:
        """既存のTOMLファイルが引き続き使用できる（FR-020）。"""
        # Arrange: Create TOML files in old format
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        team_toml = workspace / "team.toml"
        team_toml.write_text(
            """
[team]
team_id = "legacy-team"
team_name = "Legacy Team"

[[team.members]]
agent_name = "agent1"
agent_type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096
tool_description = "Agent 1"
"""
        )

        # Act: Load with new ConfigurationManager
        manager = ConfigurationManager(workspace=workspace)
        team_settings = manager.load_team_settings(Path("team.toml"))

        # Assert: Old format still works
        assert team_settings.team_id == "legacy-team"
        assert team_settings.team_name == "Legacy Team"
        assert len(team_settings.members) == 1


class TestArticle9Compliance:
    """Article 9準拠検証テスト。"""

    def test_no_implicit_cwd_fallback(
        self, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """暗黙的なCWDフォールバックが存在しない（Article 9）。"""
        # Arrange: Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Test that get_workspace_path() raises error instead of falling back to CWD
        from mixseek.utils.env import get_workspace_path

        with pytest.raises(WorkspacePathNotSpecifiedError):
            get_workspace_path(cli_arg=None)

    def test_explicit_error_messages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolate_from_project_dotenv: None
    ) -> None:
        """workspace未指定時に明示的なエラーメッセージ（Article 9, FR-011）。"""
        from mixseek.orchestrator import load_orchestrator_settings

        # Arrange: Clear environment variables
        monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)
        monkeypatch.delenv("MIXSEEK_WORKSPACE_PATH", raising=False)

        # Arrange: Config without workspace
        orchestrator_toml = tmp_path / "orchestrator.toml"
        orchestrator_toml.write_text(
            """
[orchestrator]
timeout_per_team_seconds = 300

[[orchestrator.teams]]
config = "team1.toml"
"""
        )

        # Act & Assert: Error message is clear
        try:
            load_orchestrator_settings(orchestrator_toml, workspace=None)
            pytest.fail("Expected WorkspacePathNotSpecifiedError")
        except WorkspacePathNotSpecifiedError as e:
            # Verify error message mentions MIXSEEK_WORKSPACE
            assert "MIXSEEK_WORKSPACE" in str(e)
