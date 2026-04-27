"""`run_preflight_check` を経由した team / workflow dispatch の e2e 風テスト。

validator 単体テストでは検証できない、runner.py の dispatch 配線
(両 validator 呼び出し → `workflow_settings_list` の auth 伝播) を保証する。
特に「全 entry が必ずどこかの validator で ERROR 化される」設計 invariant の
end-to-end 確認を担う。
"""

from pathlib import Path

import pytest

from mixseek.config.preflight import run_preflight_check
from mixseek.config.preflight.models import CategoryResult, CheckStatus, PreflightResult

# ---------------------------------------------------------------------------
# TOML サンプル生成ヘルパー
# ---------------------------------------------------------------------------


def _write_team_toml(path: Path) -> Path:
    path.write_text(
        '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
        "[[team.members]]\n"
        'agent_name = "a1"\nagent_type = "plain"\n'
        'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
        'system_instruction = "x"\n'
    )
    return path


def _write_workflow_toml(
    path: Path,
    *,
    default_model: str = "google-gla:gemini-2.5-flash",
) -> Path:
    path.write_text(
        f"[workflow]\n"
        f'workflow_id = "wf-1"\n'
        f'workflow_name = "WF1"\n'
        f'default_model = "{default_model}"\n'
        f"\n"
        f"[[workflow.steps]]\n"
        f'id = "s1"\n'
        f"\n"
        f"[[workflow.steps.executors]]\n"
        f'name = "a1"\n'
        f'type = "plain"\n'
    )
    return path


def _write_orchestrator(config: Path, team_paths: list[Path]) -> Path:
    """orchestrator.toml を作成する。`teams` は team / workflow 両 unit を列挙できる"""
    teams_blocks = "\n".join(f'[[orchestrator.teams]]\nconfig = "{p}"' for p in team_paths)
    config.write_text(f"[orchestrator]\n{teams_blocks}\n")
    return config


def _category(result: PreflightResult, name: str) -> CategoryResult:
    """カテゴリ名で `categories` から取得する。"""
    for cat in result.categories:
        if cat.category == name:
            return cat
    raise AssertionError(f"category {name!r} not found in {[c.category for c in result.categories]}")


# ---------------------------------------------------------------------------
# 正常系 dispatch
# ---------------------------------------------------------------------------


class TestRunnerDispatch:
    """team / workflow 両 validator の配線を検証"""

    def test_team_only_orchestrator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team-only TOML 1 件 → 「チーム」OK + 「ワークフロー」 (CheckResult 空)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team_toml = _write_team_toml(tmp_path / "team.toml")
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [team_toml])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        wf_cat = _category(result, "ワークフロー")
        assert not team_cat.has_errors
        assert any(c.status == CheckStatus.OK for c in team_cat.checks)
        assert wf_cat.checks == []
        assert result.is_valid

    def test_workflow_only_orchestrator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """workflow-only TOML 1 件 → 「チーム」 (CheckResult 空) + 「ワークフロー」 OK"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        wf_toml = _write_workflow_toml(tmp_path / "wf.toml")
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [wf_toml])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        wf_cat = _category(result, "ワークフロー")
        # workflow entry のみ → team validator は CheckResult なし
        assert team_cat.checks == []
        assert not wf_cat.has_errors
        assert any(c.status == CheckStatus.OK for c in wf_cat.checks)
        assert result.is_valid

    def test_team_and_workflow_mixed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team + workflow 各 1 件 混在 → 両カテゴリ OK"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team_toml = _write_team_toml(tmp_path / "team.toml")
        wf_toml = _write_workflow_toml(tmp_path / "wf.toml")
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [team_toml, wf_toml])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        wf_cat = _category(result, "ワークフロー")
        assert not team_cat.has_errors
        assert not wf_cat.has_errors
        assert sum(1 for c in team_cat.checks if c.status == CheckStatus.OK) == 1
        assert sum(1 for c in wf_cat.checks if c.status == CheckStatus.OK) == 1
        assert result.is_valid


# ---------------------------------------------------------------------------
# auth 伝播
# ---------------------------------------------------------------------------


class TestRunnerAuthDispatch:
    """workflow 由来モデルが auth に伝播することの e2e 確認"""

    def test_workflow_default_model_reaches_auth(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """workflow の `default_model` が認証検証で参照される (provider key 不在で ERROR)"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        # OPENAI_API_KEY を消して provider key 不在を作る
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # workflow の default_model に openai を指定 → auth で OPENAI_API_KEY が必要
        wf_toml = _write_workflow_toml(tmp_path / "wf.toml", default_model="openai:gpt-5")
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [wf_toml])

        result = run_preflight_check(config, tmp_path)

        auth_cat = _category(result, "認証")
        assert auth_cat.has_errors
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Invariant: unknown unit が必ず ERROR 化されること
# ---------------------------------------------------------------------------


class TestRunnerInvariant:
    """unknown unit (TOML 解析失敗 / 両セクション同居 / 不在) の ERROR 化を e2e で確認"""

    def test_invariant_invalid_toml_syntax(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TOML 解析失敗 entry → 「チーム」カテゴリで ERROR、`is_valid=False`"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        broken = tmp_path / "broken.toml"
        broken.write_text("[invalid\n")
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [broken])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        assert team_cat.has_errors
        assert not result.is_valid

    def test_invariant_both_sections(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]`+`[workflow]` 両在 → 「チーム」カテゴリで ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        both = tmp_path / "both.toml"
        both.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n[workflow]\nworkflow_id = "wf-1"\nworkflow_name = "WF1"\n'
        )
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [both])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        wf_cat = _category(result, "ワークフロー")
        assert team_cat.has_errors
        # workflow validator 側では skip (重複報告を避ける)
        assert wf_cat.checks == []
        assert not result.is_valid

    def test_invariant_neither_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`[team]`/`[workflow]` どちらも無い TOML → 「チーム」カテゴリで ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        neither = tmp_path / "neither.toml"
        neither.write_text('[other]\nname = "x"\n')
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [neither])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        assert team_cat.has_errors
        assert not result.is_valid

    def test_invariant_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """ファイル不在 entry → 「チーム」カテゴリで ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        missing = tmp_path / "missing.toml"  # 作成しない
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [missing])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        assert team_cat.has_errors
        assert not result.is_valid

    def test_partial_error_aggregated(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """team OK + workflow ERROR 混在 → `is_valid=False`、両カテゴリの check 集計"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team_toml = _write_team_toml(tmp_path / "team.toml")
        bad_wf = tmp_path / "bad_wf.toml"
        bad_wf.write_text(
            "[workflow]\n"
            'workflow_id = ""\n'  # 空 → schema エラー
            'workflow_name = "WF"\n'
            "[[workflow.steps]]\n"
            'id = "s1"\n'
            "[[workflow.steps.executors]]\n"
            'name = "a1"\n'
            'type = "plain"\n'
        )
        config = _write_orchestrator(tmp_path / "orchestrator.toml", [team_toml, bad_wf])

        result = run_preflight_check(config, tmp_path)

        team_cat = _category(result, "チーム")
        wf_cat = _category(result, "ワークフロー")
        assert not team_cat.has_errors
        assert wf_cat.has_errors
        assert not result.is_valid
