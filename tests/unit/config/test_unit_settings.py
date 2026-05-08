"""`ConfigurationManager.load_unit_settings` と `load_workflow_settings` の単体テスト。

Invariant 対応（PR2 計画 §Invariants 対応表）:
    #13 load_unit_settings が [team] / [workflow] で型振り分け、
        両方あり/どちらもなしは ValueError
"""

from pathlib import Path
from textwrap import dedent

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import TeamSettings, WorkflowSettings


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def _write_toml(workspace: Path, name: str, content: str) -> Path:
    path = workspace / name
    path.write_text(dedent(content).lstrip())
    return path


def _team_toml(workspace: Path) -> Path:
    return _write_toml(
        workspace,
        "team.toml",
        """
        [team]
        team_id = "team-1"
        team_name = "Team 1"
        max_concurrent_members = 3

        [team.leader]
        model = "google-gla:gemini-2.5-flash"

        [[team.members]]
        agent_name = "agent-1"
        agent_type = "plain"
        tool_name = "search_tool"
        tool_description = "Search tool"
        model = "google-gla:gemini-2.5-flash"
        """,
    )


def _workflow_toml(workspace: Path) -> Path:
    return _write_toml(
        workspace,
        "wf.toml",
        """
        [workflow]
        workflow_id = "wf-1"
        workflow_name = "Workflow 1"

        [[workflow.steps]]
        id = "s1"

        [[workflow.steps.executors]]
        name = "e1"
        type = "plain"
        """,
    )


# ---- load_workflow_settings ----


class TestLoadWorkflowSettings:
    def test_returns_workflow_settings(self, workspace: Path) -> None:
        _workflow_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_workflow_settings(Path("wf.toml"))
        assert isinstance(settings, WorkflowSettings)
        assert settings.workflow_id == "wf-1"
        assert settings.workflow_name == "Workflow 1"
        # team_id / team_name は互換 @property
        assert settings.team_id == "wf-1"
        assert settings.team_name == "Workflow 1"

    def test_default_model_applies_when_omitted(self, workspace: Path) -> None:
        _workflow_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_workflow_settings(Path("wf.toml"))
        assert settings.default_model == "google-gla:gemini-2.5-flash"


# ---- load_unit_settings: dispatch ----


class TestLoadUnitSettingsDispatch:
    def test_team_toml_returns_team_settings(self, workspace: Path) -> None:
        _team_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_unit_settings(Path("team.toml"))
        assert isinstance(settings, TeamSettings)
        assert settings.team_id == "team-1"

    def test_workflow_toml_returns_workflow_settings(self, workspace: Path) -> None:
        _workflow_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_unit_settings(Path("wf.toml"))
        assert isinstance(settings, WorkflowSettings)
        assert settings.workflow_id == "wf-1"

    def test_absolute_path_works(self, workspace: Path) -> None:
        path = _workflow_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_unit_settings(path)
        assert isinstance(settings, WorkflowSettings)


# ---- load_unit_settings: error paths ----


class TestLoadUnitSettingsErrors:
    def test_both_sections_raises_value_error(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "both.toml",
            """
            [team]
            team_id = "t"
            team_name = "T"

            [workflow]
            workflow_id = "w"
            workflow_name = "W"
            """,
        )
        cm = ConfigurationManager(workspace=workspace)
        with pytest.raises(ValueError, match="both"):
            cm.load_unit_settings(Path("both.toml"))

    def test_neither_section_raises_value_error(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "neither.toml",
            """
            [something_else]
            key = "value"
            """,
        )
        cm = ConfigurationManager(workspace=workspace)
        with pytest.raises(ValueError, match="neither"):
            cm.load_unit_settings(Path("neither.toml"))

    def test_file_not_found(self, workspace: Path) -> None:
        cm = ConfigurationManager(workspace=workspace)
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            cm.load_unit_settings(Path("nonexistent.toml"))

    def test_invalid_toml_syntax(self, workspace: Path) -> None:
        path = workspace / "broken.toml"
        path.write_text("this = is = not = valid = [[")
        cm = ConfigurationManager(workspace=workspace)
        with pytest.raises(ValueError, match="Invalid TOML syntax"):
            cm.load_unit_settings(Path("broken.toml"))


# ---- 回帰防止: 既存 load_team_settings への影響がないこと ----


class TestLoadTeamSettingsUntouched:
    """PR2 で既存 `load_team_settings` の挙動が変わっていないことを確認する。"""

    def test_load_team_settings_still_works(self, workspace: Path) -> None:
        _team_toml(workspace)
        cm = ConfigurationManager(workspace=workspace)
        settings = cm.load_team_settings(Path("team.toml"))
        assert isinstance(settings, TeamSettings)
        assert settings.team_id == "team-1"


# ---- workspace=None + MIXSEEK_WORKSPACE 経路 ----


class TestLoadUnitSettingsWithoutWorkspace:
    """`ConfigurationManager(workspace=None)` の場合、`MIXSEEK_WORKSPACE` 環境変数から
    workspace を解決する。`load_team_settings` / `load_workflow_settings` と同じルール
    （内部 source クラスが `get_workspace_for_config()` で解決）を `load_unit_settings` の
    判別フェーズでも統一する回帰テスト。
    """

    def test_workspace_none_uses_env_variable_for_workflow_dispatch(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _workflow_toml(workspace)
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
        cm = ConfigurationManager(workspace=None)
        settings = cm.load_unit_settings(Path("wf.toml"))
        assert isinstance(settings, WorkflowSettings)
        assert settings.workflow_id == "wf-1"

    def test_workspace_none_uses_env_variable_for_team_dispatch(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _team_toml(workspace)
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
        cm = ConfigurationManager(workspace=None)
        settings = cm.load_unit_settings(Path("team.toml"))
        assert isinstance(settings, TeamSettings)
        assert settings.team_id == "team-1"
