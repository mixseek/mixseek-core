"""`_validate_auth` に追加された `workflow_settings_list` 引数のテスト。

`workflow.default_model` および各 agent executor の `model` が認証検証対象として
収集されることを検証する。`workflow_settings_list` は必須引数なので、workflow が
存在しないケースでは空リストを渡す。
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from mixseek.config.preflight import _validate_auth
from mixseek.config.preflight.validators.auth import _collect_model_ids
from mixseek.config.schema import TeamSettings, WorkflowSettings


def _make_workflow(**overrides: Any) -> WorkflowSettings:
    """テスト用 WorkflowSettings を dict 経由で生成する。

    既存 `tests/unit/config/test_workflow_settings.py::_minimum_workflow_dict` と
    同じ最小構成を踏襲する。
    """
    payload: dict[str, Any] = {
        "workflow_id": "wf-1",
        "workflow_name": "Workflow 1",
        "default_model": overrides.pop("default_model", "google-gla:gemini-2.5-flash"),
        "steps": overrides.pop(
            "steps",
            [
                {
                    "id": "s1",
                    "executors": [
                        {"name": "a1", "type": "plain"},
                    ],
                }
            ],
        ),
    }
    payload.update(overrides)
    return WorkflowSettings.model_validate(payload)


class TestCollectModelIdsWorkflow:
    """`_collect_model_ids` の workflow 由来モデル収集ロジック"""

    def test_workflow_default_model_collected(self) -> None:
        """`default_model` が収集対象に入る"""
        wf = _make_workflow(default_model="anthropic:claude-sonnet-4-5")

        ids = _collect_model_ids([], None, None, [wf])

        assert "anthropic:claude-sonnet-4-5" in ids

    def test_agent_executor_model_collected(self) -> None:
        """agent executor が `model` を持つ場合のみ収集される"""
        wf = _make_workflow(
            default_model="google-gla:gemini-2.5-flash",
            steps=[
                {
                    "id": "s1",
                    "executors": [
                        {"name": "a1", "type": "plain", "model": "openai:gpt-5"},
                        {"name": "a2", "type": "plain"},  # model 省略
                    ],
                }
            ],
        )

        ids = _collect_model_ids([], None, None, [wf])

        assert "openai:gpt-5" in ids
        assert "google-gla:gemini-2.5-flash" in ids
        # model 省略 executor は default_model にフォールバックされるため
        # 個別収集はされない（default 経由でカバー済）
        assert len(ids) == 2

    def test_function_executor_ignored(self) -> None:
        """function executor は model を持たないため収集されない"""
        wf = _make_workflow(
            default_model="google-gla:gemini-2.5-flash",
            steps=[
                {
                    "id": "s1",
                    "executors": [
                        {
                            "name": "f1",
                            "type": "function",
                            "plugin": {"module": "mypkg.tools", "function": "fn"},
                        }
                    ],
                }
            ],
        )

        ids = _collect_model_ids([], None, None, [wf])

        # function executor 由来は model なしで無視、default_model のみ収集される
        assert ids == {"google-gla:gemini-2.5-flash"}

    def test_empty_workflow_settings_list(self) -> None:
        """`workflow_settings_list=[]` → workflow 由来モデルなし (team/eval/judg のみ)"""
        ids = _collect_model_ids([], None, None, [])

        assert ids == set()

    def test_team_and_workflow_dedup_by_set(self) -> None:
        """同一 model が team / workflow 両方に存在 → set で deduplicate"""
        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "google-gla:gemini-2.5-flash"}
        team.members = []

        wf = _make_workflow(default_model="google-gla:gemini-2.5-flash")

        ids = _collect_model_ids([team], None, None, [wf])

        assert ids == {"google-gla:gemini-2.5-flash"}


class TestValidateAuthWorkflow:
    """`_validate_auth` の workflow 統合"""

    def test_workflow_default_model_validated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`workflow_settings_list=[wf]` で `default_model` の provider が検証される"""
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        wf = _make_workflow(default_model="google-gla:gemini-2.5-flash")

        cat = _validate_auth([], None, None, [wf])

        # GOOGLE_API_KEY あり → エラーなし
        assert not cat.has_errors

    def test_workflow_provider_key_missing_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """workflow の provider key が不在 → ERROR (workflow 由来モデルで認証失敗)"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        wf = _make_workflow(
            default_model="google-gla:gemini-2.5-flash",
            steps=[
                {
                    "id": "s1",
                    "executors": [
                        {"name": "a1", "type": "plain", "model": "openai:gpt-5"},
                    ],
                }
            ],
        )
        # GOOGLE_API_KEY だけ設定（default_model 用）
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        cat = _validate_auth([], None, None, [wf])

        assert cat.has_errors

    def test_empty_workflow_settings_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`workflow_settings_list=[]` → team モデルのみ検証 (workflow 由来モデルなし)"""
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "google-gla:gemini-2.5-flash"}
        team.members = []

        cat = _validate_auth([team], None, None, [])

        assert not cat.has_errors

    def test_team_and_workflow_same_provider_validated_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """team と workflow が同一プロバイダ → 検証は 1 回のみ"""
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza" + "x" * 30)

        team = MagicMock(spec=TeamSettings)
        team.leader = {"model": "google-gla:gemini-2.5-flash-lite"}
        team.members = []

        wf = _make_workflow(default_model="google-gla:gemini-2.5-flash")

        cat = _validate_auth([team], None, None, [wf])

        google_checks = [c for c in cat.checks if "google" in c.name.lower()]
        assert len(google_checks) == 1
