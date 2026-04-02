"""プリフライトチェック ユニットテスト

TDD: Red-Green-Refactor サイクルの Red フェーズ。
データモデル、各検証関数、統合フローをテストする。
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mixseek.config.preflight import (
    CategoryResult,
    CheckResult,
    CheckStatus,
    PreflightResult,
    run_preflight_check,
)

# ---------------------------------------------------------------------------
# データモデルテスト
# ---------------------------------------------------------------------------


class TestCheckResultModel:
    """CheckResult モデルの基本動作テスト"""

    def test_ok_status(self) -> None:
        r = CheckResult(name="test", status=CheckStatus.OK)
        assert r.status == CheckStatus.OK
        assert r.message == ""

    def test_error_status_with_message(self) -> None:
        r = CheckResult(name="test", status=CheckStatus.ERROR, message="fail reason")
        assert r.status == CheckStatus.ERROR
        assert r.message == "fail reason"

    def test_json_serialization(self) -> None:
        r = CheckResult(name="test", status=CheckStatus.WARN, source_file="/tmp/x.toml")
        data = r.model_dump()
        assert data["status"] == "warn"
        assert data["source_file"] == "/tmp/x.toml"


class TestCategoryResult:
    """CategoryResult モデルの has_errors プロパティテスト"""

    def test_has_errors_true_when_error_present(self) -> None:
        cat = CategoryResult(
            category="test",
            checks=[
                CheckResult(name="a", status=CheckStatus.OK),
                CheckResult(name="b", status=CheckStatus.ERROR, message="bad"),
            ],
        )
        assert cat.has_errors is True

    def test_has_errors_false_when_ok_and_warn_only(self) -> None:
        cat = CategoryResult(
            category="test",
            checks=[
                CheckResult(name="a", status=CheckStatus.OK),
                CheckResult(name="b", status=CheckStatus.WARN, message="note"),
            ],
        )
        assert cat.has_errors is False


class TestPreflightResult:
    """PreflightResult モデルの集計プロパティテスト"""

    def test_is_valid_when_all_ok(self) -> None:
        result = PreflightResult(
            categories=[
                CategoryResult(
                    category="c1",
                    checks=[CheckResult(name="a", status=CheckStatus.OK)],
                ),
                CategoryResult(
                    category="c2",
                    checks=[CheckResult(name="b", status=CheckStatus.WARN)],
                ),
            ]
        )
        assert result.is_valid is True

    def test_is_valid_false_when_error(self) -> None:
        result = PreflightResult(
            categories=[
                CategoryResult(
                    category="c1",
                    checks=[CheckResult(name="a", status=CheckStatus.ERROR)],
                ),
            ]
        )
        assert result.is_valid is False

    def test_error_and_warn_counts(self) -> None:
        result = PreflightResult(
            categories=[
                CategoryResult(
                    category="c1",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.ERROR),
                        CheckResult(name="b", status=CheckStatus.WARN),
                    ],
                ),
                CategoryResult(
                    category="c2",
                    checks=[
                        CheckResult(name="c", status=CheckStatus.ERROR),
                        CheckResult(name="d", status=CheckStatus.OK),
                    ],
                ),
            ]
        )
        assert result.error_count == 2
        assert result.warn_count == 1


# ---------------------------------------------------------------------------
# _validate_orchestrator テスト
# ---------------------------------------------------------------------------

# テスト用モジュールパス
_PREFLIGHT = "mixseek.config.preflight"


class TestValidateOrchestrator:
    """オーケストレータ設定検証テスト"""

    def test_valid_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """正常なオーケストレータ設定 → OK"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        team_toml = tmp_path / "team.toml"
        team_toml.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
            "[[team.members]]\n"
            'agent_name = "a1"\nagent_type = "plain"\n'
            'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
            'system_instruction = "x"\n'
        )
        config = tmp_path / "orchestrator.toml"
        config.write_text(f'[orchestrator]\n[[orchestrator.teams]]\nconfig = "{team_toml}"\n')

        from mixseek.config.preflight import _validate_orchestrator

        cat, settings = _validate_orchestrator(config, tmp_path)
        assert not cat.has_errors
        assert settings is not None

    def test_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """設定ファイル不在 → ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        from mixseek.config.preflight import _validate_orchestrator

        cat, settings = _validate_orchestrator(tmp_path / "nonexistent.toml", tmp_path)
        assert cat.has_errors
        assert settings is None

    def test_invalid_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TOML構文エラー → ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        config = tmp_path / "bad.toml"
        config.write_text("[orchestrator\n")  # 不正TOML

        from mixseek.config.preflight import _validate_orchestrator

        cat, settings = _validate_orchestrator(config, tmp_path)
        assert cat.has_errors
        assert settings is None


# ---------------------------------------------------------------------------
# _validate_teams テスト
# ---------------------------------------------------------------------------


class TestValidateTeams:
    """チーム設定検証テスト"""

    def test_valid_teams(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """正常チーム設定 → 各チームOK"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        team_toml = tmp_path / "team.toml"
        team_toml.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
            "[[team.members]]\n"
            'agent_name = "a1"\nagent_type = "plain"\n'
            'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
            'system_instruction = "x"\n'
        )
        # OrchestratorSettingsのteamsフィールド形式をシミュレート
        mock_settings = MagicMock()
        mock_settings.teams = [{"config": str(team_toml)}]

        from mixseek.config.preflight import _validate_teams

        cat, team_list = _validate_teams(mock_settings, tmp_path)
        assert not cat.has_errors
        assert len(team_list) == 1

    def test_one_team_fails_others_continue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """1チーム失敗でも他チームは検証継続"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        good_toml = tmp_path / "good.toml"
        good_toml.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
            "[[team.members]]\n"
            'agent_name = "a1"\nagent_type = "plain"\n'
            'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
            'system_instruction = "x"\n'
        )

        mock_settings = MagicMock()
        mock_settings.teams = [
            {"config": str(tmp_path / "missing.toml")},
            {"config": str(good_toml)},
        ]

        from mixseek.config.preflight import _validate_teams

        cat, team_list = _validate_teams(mock_settings, tmp_path)
        # 1チーム失敗 + 1チーム成功
        assert cat.has_errors
        assert len(team_list) == 1  # 成功チームのみ

    def test_empty_teams_warn(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """チームリスト空 → WARN"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        mock_settings = MagicMock()
        mock_settings.teams = []

        from mixseek.config.preflight import _validate_teams

        cat, team_list = _validate_teams(mock_settings, tmp_path)
        assert not cat.has_errors
        assert any(c.status == CheckStatus.WARN for c in cat.checks)


# ---------------------------------------------------------------------------
# _validate_evaluator テスト
# ---------------------------------------------------------------------------


class TestValidateEvaluator:
    """Evaluator設定検証テスト"""

    def test_explicit_config_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """明示設定あり → OK"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        evaluator_toml = config_dir / "evaluator.toml"
        evaluator_toml.write_text(
            "[llm_default]\n"
            'model = "google-gla:gemini-2.5-flash"\n'
            "[[metrics]]\n"
            'name = "ClarityCoherence"\nweight = 1.0\n'
        )

        mock_settings = MagicMock()
        mock_settings.evaluator_config = str(evaluator_toml)

        from mixseek.config.preflight import _validate_evaluator

        cat, eval_settings = _validate_evaluator(mock_settings, tmp_path)
        assert not cat.has_errors
        assert eval_settings is not None

    def test_default_config_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """デフォルト使用（ファイル不在）→ OK + メッセージ"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        mock_settings = MagicMock()
        mock_settings.evaluator_config = None

        from mixseek.config.preflight import _validate_evaluator

        cat, eval_settings = _validate_evaluator(mock_settings, tmp_path)
        assert not cat.has_errors
        assert eval_settings is not None

    def test_invalid_config_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """不正設定 → ERROR"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        bad_toml = tmp_path / "bad_eval.toml"
        bad_toml.write_text("[invalid\n")  # 構文エラー

        mock_settings = MagicMock()
        mock_settings.evaluator_config = str(bad_toml)

        from mixseek.config.preflight import _validate_evaluator

        cat, eval_settings = _validate_evaluator(mock_settings, tmp_path)
        assert cat.has_errors
        assert eval_settings is None


# ---------------------------------------------------------------------------
# _validate_judgment テスト
# ---------------------------------------------------------------------------


class TestValidateJudgment:
    """Judgment設定検証テスト"""

    def test_default_config_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """デフォルト使用 → OK + メッセージ"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        mock_settings = MagicMock()
        mock_settings.judgment_config = None

        from mixseek.config.preflight import _validate_judgment

        cat, judg_settings = _validate_judgment(mock_settings, tmp_path)
        assert not cat.has_errors
        assert judg_settings is not None


# ---------------------------------------------------------------------------
# _validate_prompt_builder テスト
# ---------------------------------------------------------------------------


class TestValidatePromptBuilder:
    """PromptBuilder設定検証テスト"""

    def test_default_config_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """デフォルト使用 → OK + メッセージ"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        mock_settings = MagicMock()
        mock_settings.prompt_builder_config = None

        from mixseek.config.preflight import _validate_prompt_builder

        cat = _validate_prompt_builder(mock_settings, tmp_path)
        assert not cat.has_errors


# ---------------------------------------------------------------------------
# _validate_auth テスト
# ---------------------------------------------------------------------------


class TestValidateAuth:
    """認証検証テスト"""

    def test_all_providers_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """全プロバイダのキーあり → OK"""
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        from mixseek.config.preflight import _validate_auth
        from mixseek.config.schema import TeamSettings

        # Google AIモデルのみ使用するチーム設定をモック
        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "google-gla:gemini-2.5-flash-lite"}
        team.members = []

        cat = _validate_auth([team], None, None)
        assert not cat.has_errors

    def test_missing_provider_key_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """一部プロバイダのキー不在 → ERROR"""
        # OPENAI_API_KEYを削除
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from mixseek.config.preflight import _validate_auth
        from mixseek.config.schema import TeamSettings

        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "openai:gpt-4o"}
        team.members = []

        cat = _validate_auth([team], None, None)
        assert cat.has_errors

    def test_same_provider_validated_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """同一プロバイダ複数モデル → 1回のみ検証"""
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        from mixseek.config.preflight import _validate_auth
        from mixseek.config.schema import MemberAgentSettings, TeamSettings

        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "google-gla:gemini-2.5-flash-lite"}
        member = MagicMock(spec=MemberAgentSettings)
        member.model = "google-gla:gemini-2.5-flash"
        team.members = [member]

        cat = _validate_auth([team], None, None)
        # Google AIの検証が1回だけ行われる（チェック結果は1つ）
        google_checks = [c for c in cat.checks if "google" in c.name.lower()]
        assert len(google_checks) == 1

    def test_test_model_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """テスト用モデル(test_model) → SKIPPED"""
        from mixseek.config.preflight import _validate_auth
        from mixseek.config.schema import TeamSettings

        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "test_model"}
        team.members = []

        cat = _validate_auth([team], None, None)
        # テストモデルはスキップされるのでエラーにならない
        assert not cat.has_errors


# ---------------------------------------------------------------------------
# _validate_custom_metrics テスト
# ---------------------------------------------------------------------------


class TestValidateCustomMetrics:
    """カスタムメトリクス検証テスト"""

    def test_no_custom_metrics_skipped(self) -> None:
        """カスタムメトリクスなし → SKIPPED"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        eval_settings.custom_metrics = {}

        cat = _validate_custom_metrics(eval_settings)
        assert any(c.status == CheckStatus.SKIPPED for c in cat.checks)

    def test_valid_custom_metric_ok(self) -> None:
        """正常メトリクス → OK"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        eval_settings.custom_metrics = {
            "test_metric": {
                "module": "mixseek.evaluator.metrics.clarity_coherence",
                "class": "ClarityCoherence",
            }
        }

        cat = _validate_custom_metrics(eval_settings)
        assert not cat.has_errors

    def test_module_not_found_error(self) -> None:
        """モジュール不在 → ERROR"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        eval_settings.custom_metrics = {
            "bad_metric": {
                "module": "nonexistent.module.path",
                "class": "SomeMetric",
            }
        }

        cat = _validate_custom_metrics(eval_settings)
        assert cat.has_errors

    def test_class_not_found_error(self) -> None:
        """クラス不在 → ERROR"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        eval_settings.custom_metrics = {
            "bad_metric": {
                "module": "mixseek.evaluator.metrics.clarity_coherence",
                "class": "NonexistentClass",
            }
        }

        cat = _validate_custom_metrics(eval_settings)
        assert cat.has_errors

    def test_not_base_metric_error(self) -> None:
        """BaseMetric非継承 → ERROR"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        # os.path は BaseMetric を継承していないクラスを持つモジュール
        eval_settings.custom_metrics = {
            "bad_metric": {
                "module": "os.path",
                "class": "PurePath",
            }
        }

        # pathlib.PurePath をインポートできるが BaseMetric ではない
        eval_settings.custom_metrics = {
            "bad_metric": {
                "module": "pathlib",
                "class": "PurePath",
            }
        }

        cat = _validate_custom_metrics(eval_settings)
        assert cat.has_errors

    def test_missing_module_field_error(self) -> None:
        """module/classフィールド不在 → ERROR"""
        from mixseek.config.preflight import _validate_custom_metrics

        eval_settings = MagicMock()
        eval_settings.custom_metrics = {
            "bad_metric": {"class": "SomeMetric"}  # module なし
        }

        cat = _validate_custom_metrics(eval_settings)
        assert cat.has_errors


# ---------------------------------------------------------------------------
# _validate_metric_names テスト
# ---------------------------------------------------------------------------


class TestValidateMetricNames:
    """メトリクス名検証テスト"""

    def test_builtin_metric_ok(self) -> None:
        """ビルトインメトリクス名 → OK"""
        from mixseek.config.preflight import _validate_metric_names

        eval_settings = MagicMock()
        eval_settings.metrics = [
            {"name": "ClarityCoherence", "weight": 0.5},
            {"name": "Coverage", "weight": 0.5},
        ]
        eval_settings.custom_metrics = {}

        cat = _validate_metric_names(eval_settings)
        assert not cat.has_errors

    def test_custom_metric_name_ok(self) -> None:
        """カスタムメトリクスとして登録済みの名前 → OK"""
        from mixseek.config.preflight import _validate_metric_names

        eval_settings = MagicMock()
        eval_settings.metrics = [{"name": "my_custom", "weight": 1.0}]
        eval_settings.custom_metrics = {"my_custom": {"module": "some.module", "class": "SomeClass"}}

        cat = _validate_metric_names(eval_settings)
        assert not cat.has_errors

    def test_nonexistent_metric_error(self) -> None:
        """存在しないメトリクス名 → ERROR"""
        from mixseek.config.preflight import _validate_metric_names

        eval_settings = MagicMock()
        eval_settings.metrics = [{"name": "TotallyFakeMetric", "weight": 1.0}]
        eval_settings.custom_metrics = {}

        cat = _validate_metric_names(eval_settings)
        assert cat.has_errors


# ---------------------------------------------------------------------------
# _validate_workspace_writable テスト
# ---------------------------------------------------------------------------


class TestValidateWorkspaceWritable:
    """ワークスペース書き込み権限テスト"""

    def test_writable_workspace_ok(self, tmp_path: Path) -> None:
        """書き込み可能なワークスペース → OK"""
        from mixseek.config.preflight import _validate_workspace_writable

        cat = _validate_workspace_writable(tmp_path)
        assert not cat.has_errors

    def test_nonexistent_workspace_error(self, tmp_path: Path) -> None:
        """存在しないワークスペース → ERROR"""
        from mixseek.config.preflight import _validate_workspace_writable

        cat = _validate_workspace_writable(tmp_path / "nonexistent")
        assert cat.has_errors


# ---------------------------------------------------------------------------
# run_preflight_check 統合テスト
# ---------------------------------------------------------------------------


class TestRunPreflightCheck:
    """run_preflight_check 統合テスト"""

    def test_all_valid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """全正常 → is_valid=True"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team_toml = tmp_path / "team.toml"
        team_toml.write_text(
            '[team]\nteam_id = "t1"\nteam_name = "T1"\n'
            "[[team.members]]\n"
            'agent_name = "a1"\nagent_type = "plain"\n'
            'tool_description = "d"\nmodel = "google-gla:gemini-2.5-flash-lite"\n'
            'system_instruction = "x"\n'
        )
        config = tmp_path / "orchestrator.toml"
        config.write_text(f'[orchestrator]\n[[orchestrator.teams]]\nconfig = "{team_toml}"\n')

        result = run_preflight_check(config, tmp_path)
        assert result.is_valid

    def test_orchestrator_error_skips_rest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """orchestratorエラー → 後続スキップ、is_valid=False"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        result = run_preflight_check(tmp_path / "nonexistent.toml", tmp_path)
        assert not result.is_valid
        # orchestratorカテゴリのみ存在
        assert len(result.categories) == 1

    def test_partial_errors_aggregated(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """チーム1件エラー+evaluatorエラー → 両方のエラーが収集される"""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        # 正常なオーケストレータ設定（チーム参照が不正ファイルを含む）
        bad_eval = tmp_path / "bad_eval.toml"
        bad_eval.write_text("[invalid\n")

        config = tmp_path / "orchestrator.toml"
        config.write_text(
            "[orchestrator]\n"
            f'evaluator_config = "{bad_eval}"\n'
            "[[orchestrator.teams]]\n"
            f'config = "{tmp_path / "missing_team.toml"}"\n'
        )

        result = run_preflight_check(config, tmp_path)
        assert not result.is_valid
        assert result.error_count >= 2  # チームエラー + evaluatorエラー
