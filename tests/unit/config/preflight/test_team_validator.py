"""`_validate_teams` の invariant 系テスト（PR4 で追加）。

設計 invariant: 「全 entry が必ずどこかの validator で ERROR 化される」を担保するため、
`_detect_unit_kind` で `"unknown"` 判定された entry (TOML 解析失敗 / 両セクション同居 /
どちらもなし / file not found) は team validator 側で `load_unit_settings` が例外を
raise することにより ERROR 化される。本テストはその振る舞いを集中的に検証する。

なお `[team]` のみの正常系 / `missing.toml` / 空 teams の挙動は既存
`tests/unit/config/test_preflight.py::TestValidateTeams` でカバー済のため重複させない。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mixseek.config import OrchestratorSettings
from mixseek.config.preflight import _validate_teams
from mixseek.config.preflight.models import CheckStatus


def _write_team_toml(path: Path, team_id: str = "t1") -> Path:
    """正常 team TOML を作成"""
    path.write_text(
        f'[team]\nteam_id = "{team_id}"\nteam_name = "{team_id}"\n'
        "[[team.members]]\n"
        'agent_name = "a1"\nagent_type = "plain"\n'
        'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
        'system_instruction = "x"\n'
    )
    return path


class TestValidateTeamsInvariant:
    """`"unknown"` kind が必ず ERROR 化される invariant 検証"""

    def test_workflow_only_entry_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[workflow]` のみの entry → team validator では skip (CheckResult 積まない)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        wf_toml = tmp_path / "wf.toml"
        wf_toml.write_text(
            "[workflow]\n"
            'workflow_id = "wf-1"\n'
            'workflow_name = "WF1"\n'
            "[[workflow.steps]]\n"
            'id = "s1"\n'
            "[[workflow.steps.executors]]\n"
            'name = "a1"\n'
            'type = "plain"\n'
        )

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(wf_toml)}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        # workflow entry は team validator では skip され CheckResult 積まれない
        assert cat.checks == []
        assert not cat.has_errors
        assert team_list == []

    def test_both_team_and_workflow_sections_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]` と `[workflow]` 両方存在 → ERROR (`unknown` から ValueError)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        bad_toml = tmp_path / "both.toml"
        bad_toml.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n[workflow]\nworkflow_id = "wf-1"\nworkflow_name = "WF1"\n'
        )

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(bad_toml)}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        assert cat.has_errors
        assert team_list == []
        assert any(c.status == CheckStatus.ERROR for c in cat.checks)

    def test_neither_team_nor_workflow_sections_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]` も `[workflow]` も無い TOML → ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        neither_toml = tmp_path / "neither.toml"
        neither_toml.write_text('[other]\nname = "x"\n')

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(neither_toml)}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        assert cat.has_errors
        assert team_list == []

    def test_invalid_toml_syntax_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TOML 構文エラー → ERROR (`load_unit_settings` の TOMLDecodeError → ValueError)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        broken = tmp_path / "broken.toml"
        broken.write_text("[invalid\n")

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(broken)}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        assert cat.has_errors
        assert team_list == []

    def test_file_not_found_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """file not found → ERROR (`load_unit_settings` が FileNotFoundError)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(tmp_path / "missing.toml")}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        assert cat.has_errors
        assert team_list == []

    def test_mixed_team_and_workflow_entries(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team entry + workflow entry 混在 → team は OK、workflow は skip"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        team_toml = _write_team_toml(tmp_path / "team.toml")
        wf_toml = tmp_path / "wf.toml"
        wf_toml.write_text(
            "[workflow]\n"
            'workflow_id = "wf-1"\n'
            'workflow_name = "WF1"\n'
            "[[workflow.steps]]\n"
            'id = "s1"\n'
            "[[workflow.steps.executors]]\n"
            'name = "a1"\n'
            'type = "plain"\n'
        )

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [{"config": str(team_toml)}, {"config": str(wf_toml)}]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        # team は OK、workflow entry は skip
        assert not cat.has_errors
        assert len(team_list) == 1
        # team entry の CheckResult のみ積まれる (workflow は skip)
        assert len(cat.checks) == 1
        assert cat.checks[0].status == CheckStatus.OK

    def test_team_entry_with_unknown_entry_mixed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team entry OK + unknown entry ERROR の混在 → 両方積まれて ERROR 全体"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        team_toml = _write_team_toml(tmp_path / "team.toml")
        unknown_toml = tmp_path / "unknown.toml"
        unknown_toml.write_text('[other]\nname = "x"\n')

        mock_settings = MagicMock(spec=OrchestratorSettings)
        mock_settings.teams = [
            {"config": str(team_toml)},
            {"config": str(unknown_toml)},
        ]

        cat, team_list = _validate_teams(mock_settings, tmp_path)

        assert cat.has_errors
        assert len(team_list) == 1  # team の OK のみ list に入る
        # 1 OK + 1 ERROR の合計 2 CheckResult
        statuses = sorted(c.status for c in cat.checks)
        assert statuses == sorted([CheckStatus.OK, CheckStatus.ERROR])
