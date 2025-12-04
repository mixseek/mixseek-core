"""Unit tests for ConfigurationManager load_*_settings methods.

Article 3準拠: リファクタリング前にテストファーストで実装動作を保証。
"""

from pathlib import Path
from typing import Any

import pytest

from mixseek.config import (
    ConfigurationManager,
    EvaluatorSettings,
    MemberAgentSettings,
    OrchestratorSettings,
)
from mixseek.config.schema import TeamSettings

# ==========================================
# Fixtures
# ==========================================


@pytest.fixture
def team_toml_content() -> str:
    """Valid team.toml content for testing."""
    return """
[team]
team_id = "test_team"
team_name = "Test Team"
max_concurrent_members = 5
environment = "test"

[team.leader]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.7
timeout_seconds = 300

[[team.members]]
agent_name = "member1"
agent_type = "plain"
tool_description = "Test member agent"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 4096
"""


@pytest.fixture
def member_toml_content() -> str:
    """Valid member agent TOML content for testing."""
    return """
[agent]
name = "test_member"
type = "plain"
description = "Test member agent"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.5
max_tokens = 4096
"""


@pytest.fixture
def evaluation_toml_content() -> str:
    """Valid evaluator.toml content for testing."""
    return """
default_model = "anthropic:claude-sonnet-4-5-20250929"
max_retries = 3

[[metrics]]
name = "clarity_coherence"
weight = 0.4
model = "anthropic:claude-sonnet-4-5-20250929"

[[metrics]]
name = "coverage"
weight = 0.3

[[metrics]]
name = "relevance"
weight = 0.3
"""


@pytest.fixture
def orchestrator_toml_content() -> str:
    """Valid orchestrator.toml content for testing."""
    return """
[orchestrator]
timeout_per_team_seconds = 500
max_concurrent_teams = 2

[[orchestrator.teams]]
config = "configs/agents/team1.toml"
"""


@pytest.fixture
def workspace_with_configs(tmp_path: Path) -> Path:
    """Temporary workspace with all config types."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    configs_dir = workspace / "configs"
    configs_dir.mkdir()
    return workspace


# ==========================================
# TestLoadTeamSettings
# ==========================================


class TestLoadTeamSettings:
    """load_team_settings()のテスト（T091、T078対応）。"""

    def test_load_team_settings_returns_team_settings_instance(
        self,
        workspace_with_configs: Path,
        team_toml_content: str,
    ) -> None:
        """load_team_settings()がTeamSettingsインスタンスを返すことを確認。"""
        # Arrange
        team_toml = workspace_with_configs / "configs" / "team.toml"
        team_toml.write_text(team_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        team_settings = manager.load_team_settings(team_toml)

        # Assert
        assert isinstance(team_settings, TeamSettings)
        assert team_settings.team_id == "test_team"
        assert team_settings.team_name == "Test Team"

    def test_load_team_settings_includes_trace_info(
        self,
        workspace_with_configs: Path,
        team_toml_content: str,
    ) -> None:
        """load_team_settings()がトレース情報を含むことを確認。"""
        # Arrange
        team_toml = workspace_with_configs / "configs" / "team.toml"
        team_toml.write_text(team_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        team_settings = manager.load_team_settings(team_toml)

        # Assert: トレース情報が添付されている
        assert hasattr(team_settings, "__source_traces__")
        traces = getattr(team_settings, "__source_traces__")
        assert isinstance(traces, dict)

    def test_load_team_settings_with_cli_override(
        self,
        workspace_with_configs: Path,
        team_toml_content: str,
    ) -> None:
        """CLI引数がTOML設定を上書きすることを確認（優先順位テスト）。"""
        # Arrange
        team_toml = workspace_with_configs / "configs" / "team.toml"
        team_toml.write_text(team_toml_content)

        manager = ConfigurationManager(
            workspace=workspace_with_configs,
            cli_args={"team_id": "cli_team"},
        )

        # Act
        team_settings = manager.load_team_settings(team_toml)

        # Assert: CLI引数が優先
        assert team_settings.team_id == "cli_team"

    def test_load_team_settings_with_extra_kwargs(
        self,
        workspace_with_configs: Path,
        team_toml_content: str,
    ) -> None:
        """extra_kwargsがTOML設定を上書きすることを確認。"""
        # Arrange
        team_toml = workspace_with_configs / "configs" / "team.toml"
        team_toml.write_text(team_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        team_settings = manager.load_team_settings(team_toml, team_id="extra_team")

        # Assert: extra_kwargsが優先
        assert team_settings.team_id == "extra_team"

    def test_load_team_settings_filters_none_cli_args(
        self,
        workspace_with_configs: Path,
        team_toml_content: str,
    ) -> None:
        """None値のCLI引数がフィルタリングされることを確認（Article 9準拠）。"""
        # Arrange
        team_toml = workspace_with_configs / "configs" / "team.toml"
        team_toml.write_text(team_toml_content)

        manager = ConfigurationManager(
            workspace=workspace_with_configs,
            cli_args={"team_id": None},  # None値はフィルタリングされるべき
        )

        # Act
        team_settings = manager.load_team_settings(team_toml)

        # Assert: TOML値が使用される（Noneで上書きされない）
        assert team_settings.team_id == "test_team"


# ==========================================
# TestLoadMemberSettings
# ==========================================


class TestLoadMemberSettings:
    """load_member_settings()のテスト（T079対応）。"""

    def test_load_member_settings_returns_member_agent_settings_instance(
        self,
        workspace_with_configs: Path,
        member_toml_content: str,
    ) -> None:
        """load_member_settings()がMemberAgentSettingsインスタンスを返すことを確認。"""
        # Arrange
        member_toml = workspace_with_configs / "configs" / "member.toml"
        member_toml.write_text(member_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        member_settings = manager.load_member_settings(member_toml)

        # Assert
        assert isinstance(member_settings, MemberAgentSettings)
        assert member_settings.agent_name == "test_member"
        assert member_settings.model == "google-gla:gemini-2.5-flash-lite"

    def test_load_member_settings_includes_trace_info(
        self,
        workspace_with_configs: Path,
        member_toml_content: str,
    ) -> None:
        """load_member_settings()がトレース情報を含むことを確認。"""
        # Arrange
        member_toml = workspace_with_configs / "configs" / "member.toml"
        member_toml.write_text(member_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        member_settings = manager.load_member_settings(member_toml)

        # Assert: トレース情報が添付されている
        assert hasattr(member_settings, "__source_traces__")
        traces = getattr(member_settings, "__source_traces__")
        assert isinstance(traces, dict)

    def test_load_member_settings_with_cli_override(
        self,
        workspace_with_configs: Path,
        member_toml_content: str,
    ) -> None:
        """CLI引数がTOML設定を上書きすることを確認（優先順位テスト）。"""
        # Arrange
        member_toml = workspace_with_configs / "configs" / "member.toml"
        member_toml.write_text(member_toml_content)

        manager = ConfigurationManager(
            workspace=workspace_with_configs,
            cli_args={"agent_name": "cli_member"},
        )

        # Act
        member_settings = manager.load_member_settings(member_toml)

        # Assert: CLI引数が優先
        assert member_settings.agent_name == "cli_member"


# ==========================================
# TestLoadEvaluationSettings
# ==========================================


class TestLoadEvaluationSettings:
    """load_evaluation_settings()のテスト。"""

    def test_load_evaluation_settings_returns_evaluator_settings_instance(
        self,
        workspace_with_configs: Path,
        evaluation_toml_content: str,
    ) -> None:
        """load_evaluation_settings()がEvaluatorSettingsインスタンスを返すことを確認。"""
        # Arrange
        eval_toml = workspace_with_configs / "configs" / "evaluator.toml"
        eval_toml.write_text(evaluation_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        eval_settings = manager.load_evaluation_settings(eval_toml)

        # Assert
        assert isinstance(eval_settings, EvaluatorSettings)
        assert eval_settings.default_model == "anthropic:claude-sonnet-4-5-20250929"
        assert len(eval_settings.metrics) == 3

    def test_load_evaluation_settings_includes_trace_info(
        self,
        workspace_with_configs: Path,
        evaluation_toml_content: str,
    ) -> None:
        """load_evaluation_settings()がトレース情報を含むことを確認。"""
        # Arrange
        eval_toml = workspace_with_configs / "configs" / "evaluator.toml"
        eval_toml.write_text(evaluation_toml_content)

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        eval_settings = manager.load_evaluation_settings(eval_toml)

        # Assert: トレース情報が添付されている
        assert hasattr(eval_settings, "__source_traces__")
        traces = getattr(eval_settings, "__source_traces__")
        assert isinstance(traces, dict)


# ==========================================
# TestLoadOrchestratorSettings
# ==========================================


class TestLoadOrchestratorSettings:
    """load_orchestrator_settings()のテスト。"""

    def test_load_orchestrator_settings_returns_orchestrator_settings_instance(
        self,
        workspace_with_configs: Path,
        orchestrator_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """load_orchestrator_settings()がOrchestratorSettingsインスタンスを返すことを確認。"""
        # Arrange
        orch_toml = workspace_with_configs / "configs" / "orchestrator.toml"
        orch_toml.write_text(orchestrator_toml_content)

        # workspace_pathは環境変数またはCLI引数で提供される必要がある
        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_configs))

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        orch_settings = manager.load_orchestrator_settings(orch_toml)

        # Assert
        assert isinstance(orch_settings, OrchestratorSettings)
        assert orch_settings.timeout_per_team_seconds == 500
        assert orch_settings.max_concurrent_teams == 2
        assert orch_settings.workspace_path == workspace_with_configs

    def test_load_orchestrator_settings_includes_trace_info(
        self,
        workspace_with_configs: Path,
        orchestrator_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """load_orchestrator_settings()がトレース情報を含むことを確認。"""
        # Arrange
        orch_toml = workspace_with_configs / "configs" / "orchestrator.toml"
        orch_toml.write_text(orchestrator_toml_content)

        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_configs))

        manager = ConfigurationManager(workspace=workspace_with_configs)

        # Act
        orch_settings = manager.load_orchestrator_settings(orch_toml)

        # Assert: トレース情報が添付されている
        assert hasattr(orch_settings, "__source_traces__")
        traces = getattr(orch_settings, "__source_traces__")
        assert isinstance(traces, dict)

    def test_load_orchestrator_settings_with_cli_override(
        self,
        workspace_with_configs: Path,
        orchestrator_toml_content: str,
        monkeypatch: Any,
    ) -> None:
        """CLI引数がTOML設定を上書きすることを確認（優先順位テスト）。"""
        # Arrange
        orch_toml = workspace_with_configs / "configs" / "orchestrator.toml"
        orch_toml.write_text(orchestrator_toml_content)

        monkeypatch.setenv("MIXSEEK_WORKSPACE_PATH", str(workspace_with_configs))

        manager = ConfigurationManager(
            workspace=workspace_with_configs,
            cli_args={"timeout_per_team_seconds": 999},
        )

        # Act
        orch_settings = manager.load_orchestrator_settings(orch_toml)

        # Assert: CLI引数が優先
        assert orch_settings.timeout_per_team_seconds == 999
