"""`_validate_workflows` の単体テスト。

`[workflow]` の entry のみが処理対象であり、team / unknown は skip される責任分担を検証する。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mixseek.config import OrchestratorSettings
from mixseek.config.preflight import _validate_workflows
from mixseek.config.preflight.models import CheckStatus

# ---------------------------------------------------------------------------
# TOML サンプル生成ヘルパー
# ---------------------------------------------------------------------------


def _write_workflow_toml(
    path: Path,
    *,
    workflow_id: str = "wf-1",
    default_model: str = "google-gla:gemini-2.5-flash",
    executor_model: str | None = None,
) -> Path:
    """最小構成の workflow TOML を作成する。"""
    executor_model_line = f'model = "{executor_model}"\n' if executor_model else ""
    path.write_text(
        f"[workflow]\n"
        f'workflow_id = "{workflow_id}"\n'
        f'workflow_name = "WF1"\n'
        f'default_model = "{default_model}"\n'
        f"\n"
        f"[[workflow.steps]]\n"
        f'id = "s1"\n'
        f"\n"
        f"[[workflow.steps.executors]]\n"
        f'name = "a1"\n'
        f'type = "plain"\n'
        f"{executor_model_line}"
    )
    return path


def _write_team_toml(path: Path) -> Path:
    """最小構成の team TOML を作成する。"""
    path.write_text(
        '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
        "[[team.members]]\n"
        'agent_name = "a1"\nagent_type = "plain"\n'
        'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
        'system_instruction = "x"\n'
    )
    return path


# ---------------------------------------------------------------------------
# `_validate_workflows` 主要パステスト
# ---------------------------------------------------------------------------


class TestValidateWorkflows:
    """`_validate_workflows` の dispatch + ロード挙動"""

    def test_workflow_only_entry_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """正常 workflow TOML の単独 entry → OK CheckResult、settings_list 1件"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        wf_toml = _write_workflow_toml(tmp_path / "wf.toml")

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(wf_toml)}]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        assert cat.category == "ワークフロー"
        assert not cat.has_errors
        assert len(wf_list) == 1
        assert wf_list[0].workflow_id == "wf-1"
        assert any(c.status == CheckStatus.OK for c in cat.checks)

    def test_workflow_invalid_schema_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """schema invalid (workflow_id 空) → ERROR CheckResult、settings_list 空"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        wf_toml = tmp_path / "bad_wf.toml"
        wf_toml.write_text(
            "[workflow]\n"
            'workflow_id = ""\n'  # 空の workflow_id (schema エラー)
            'workflow_name = "WF"\n'
            "[[workflow.steps]]\n"
            'id = "s1"\n'
            "[[workflow.steps.executors]]\n"
            'name = "a1"\n'
            'type = "plain"\n'
        )

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(wf_toml)}]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        assert cat.has_errors
        assert len(wf_list) == 0

    def test_team_entry_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]` のみの entry は skip (CheckResult 積まれない)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        team_toml = _write_team_toml(tmp_path / "team.toml")

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(team_toml)}]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        # team entry は workflow validator では skip するため CheckResult なし
        assert cat.checks == []
        assert not cat.has_errors
        assert len(wf_list) == 0

    def test_unknown_entry_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]` も `[workflow]` も無い entry は skip (team validator が ERROR 化担当)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        unknown_toml = tmp_path / "unknown.toml"
        unknown_toml.write_text('[other]\nname = "x"\n')

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(unknown_toml)}]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        # unknown は team validator 側で ERROR 報告するので workflow 側では沈黙
        assert cat.checks == []
        assert not cat.has_errors
        assert len(wf_list) == 0

    def test_only_team_entries_no_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team entry が複数 → checks=[]、has_errors=False"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        team1 = _write_team_toml(tmp_path / "t1.toml")
        team2 = _write_team_toml(tmp_path / "t2.toml")

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [
            {"config": str(team1)},
            {"config": str(team2)},
        ]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        assert cat.checks == []
        assert not cat.has_errors
        assert wf_list == []

    def test_mixed_workflow_ok_and_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """workflow 1件 OK + 1件 ERROR の混在 → 両方の CheckResult、list に 1 件のみ"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        good = _write_workflow_toml(tmp_path / "good.toml", workflow_id="wf-good")
        bad = tmp_path / "bad.toml"
        bad.write_text(
            "[workflow]\n"
            'workflow_id = "wf-bad"\n'
            'workflow_name = "WF Bad"\n'
            'default_model = "invalid_format_no_colon"\n'  # provider:model 形式違反
            "[[workflow.steps]]\n"
            'id = "s1"\n'
            "[[workflow.steps.executors]]\n"
            'name = "a1"\n'
            'type = "plain"\n'
        )

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(good)}, {"config": str(bad)}]

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        assert cat.has_errors
        assert len(wf_list) == 1
        assert wf_list[0].workflow_id == "wf-good"
        assert sum(1 for c in cat.checks if c.status == CheckStatus.OK) == 1
        assert sum(1 for c in cat.checks if c.status == CheckStatus.ERROR) == 1

    def test_empty_teams_no_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """teams=[] → checks=[]、has_errors=False (team validator が空チェック ERROR を担当)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = []

        cat, wf_list = _validate_workflows(mock_settings, tmp_path)

        assert cat.checks == []
        assert not cat.has_errors
        assert wf_list == []
