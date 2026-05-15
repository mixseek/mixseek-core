"""`mixseek.config.sources.workflow_toml_source.WorkflowTomlSource` の単体テスト。

Invariant 対応（PR2 計画 §Invariants 対応表）:
    #14 default_model 未指定時に Pydantic default を保持
    #16 `StepExecutorConfig` discriminator が `type` キー欠如 dict でエラーを出す
"""

from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError

from mixseek.config.schema import WorkflowSettings
from mixseek.config.sources.workflow_toml_source import WorkflowTomlSource


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """テスト用 workspace（TOML ファイル書き込み先）。"""
    return tmp_path


def _write_toml(workspace: Path, name: str, content: str) -> Path:
    """`workspace` 配下に TOML を書き込みパスを返す。相対パスとして source に渡せる。"""
    path = workspace / name
    path.write_text(dedent(content).lstrip())
    return path


# ---- 正常ケース ----


class TestValidWorkflowToml:
    def test_loads_minimal_workflow(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "wf-1"
            workflow_name = "My Workflow"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        data = source()
        assert data["workflow_id"] == "wf-1"
        assert data["workflow_name"] == "My Workflow"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["id"] == "s1"

    def test_absolute_path_also_works(self, workspace: Path) -> None:
        path = _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "x"
            workflow_name = "X"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, path, workspace=workspace)
        data = source()
        assert data["workflow_id"] == "x"

    def test_end_to_end_with_pydantic(self, workspace: Path) -> None:
        """`WorkflowSettings.model_validate` まで通すエンドツーエンド確認。"""
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "wf-e2e"
            workflow_name = "E2E"
            default_model = "openai:gpt-4o-mini"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "agent-1"
            type = "plain"

            [[workflow.steps.executors]]
            name = "fn-1"
            type = "function"

            [workflow.steps.executors.plugin]
            module = "mypkg.mod"
            function = "my_fn"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        settings = WorkflowSettings.model_validate(source())
        assert settings.workflow_id == "wf-e2e"
        assert settings.default_model == "openai:gpt-4o-mini"
        assert len(settings.steps[0].executors) == 2


# ---- default_model フォールバック（invariant #14）----


class TestDefaultModelFallback:
    def test_default_model_key_absent_when_toml_omits_it(self, workspace: Path) -> None:
        """TOML に default_model を書かないと、source 辞書に key が含まれない。"""
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "x"
            workflow_name = "X"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        data = source()
        assert "default_model" not in data
        # Pydantic が default を使う
        settings = WorkflowSettings.model_validate(data)
        assert settings.default_model == "google-gla:gemini-2.5-flash"

    def test_default_model_reflected_when_specified(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "x"
            workflow_name = "X"
            default_model = "anthropic:claude-sonnet-4-5"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        data = source()
        assert data["default_model"] == "anthropic:claude-sonnet-4-5"

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("include_all_context", False),
            ("final_output_format", "text"),
        ],
    )
    def test_optional_fields_absent_when_omitted(self, workspace: Path, key: str, value: object) -> None:
        """include_all_context / final_output_format も TOML 省略時に key ごと落ちる。"""
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "x"
            workflow_name = "X"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        data = source()
        assert key not in data

    def test_optional_fields_reflected_when_specified(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "wf.toml",
            """
            [workflow]
            workflow_id = "x"
            workflow_name = "X"
            include_all_context = false
            final_output_format = "text"

            [[workflow.steps]]
            id = "s1"

            [[workflow.steps.executors]]
            name = "e1"
            type = "plain"
            """,
        )
        source = WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)
        data = source()
        assert data["include_all_context"] is False
        assert data["final_output_format"] == "text"


# ---- エラーケース ----


class TestInvalidWorkflowToml:
    def test_missing_workflow_section(self, workspace: Path) -> None:
        _write_toml(
            workspace,
            "wf.toml",
            """
            [team]
            team_id = "t1"
            team_name = "T"
            """,
        )
        with pytest.raises(ValueError, match="missing 'workflow' section"):
            WorkflowTomlSource(WorkflowSettings, Path("wf.toml"), workspace=workspace)

    def test_file_not_found(self, workspace: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Workflow config file not found"):
            WorkflowTomlSource(WorkflowSettings, Path("no_such.toml"), workspace=workspace)

    def test_invalid_toml_syntax(self, workspace: Path) -> None:
        path = workspace / "broken.toml"
        path.write_text("this is not = valid = toml = at all [[")
        with pytest.raises(ValueError, match="Invalid TOML syntax"):
            WorkflowTomlSource(WorkflowSettings, Path("broken.toml"), workspace=workspace)


# ---- discriminator エラーメッセージ（invariant #16）----


class TestDiscriminatorErrorMessage:
    """`StepExecutorConfig` discriminator の挙動をテストで固定。

    `type` キー欠如の dict を渡した場合、Pydantic v2 のエラーメッセージは
    `Unable to extract tag using discriminator 'type'` を含む。実装者が
    デバッグ時にこのメッセージを手がかりにできるよう、回帰検出用に固定する。
    """

    def test_missing_type_key_has_discriminator_hint(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            WorkflowSettings.model_validate(
                {
                    "workflow_id": "x",
                    "workflow_name": "X",
                    "steps": [
                        {
                            "id": "s1",
                            "executors": [{"name": "missing-type"}],
                        }
                    ],
                }
            )
        msg = str(exc_info.value)
        # Pydantic v2 のエラーメッセージに含まれるキーワードを検証
        assert "discriminator" in msg
        assert "type" in msg
