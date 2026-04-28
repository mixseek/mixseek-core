"""Workflow function plugin の `path` 方式を `WorkflowEngine` 全体で通す E2E。

PR4.5 で追加された `FunctionPluginMetadata.path` の引き継ぎ要件:
    既存 `tests/integration/test_workflow_function_path.py` は `build_executable`
    までの配線を確認するが、`WorkflowEngine._execute_step` 経由の実行は通していない。
    本テストは `build_executable` を patch せず、実 loader (`_load_module_from_path`)
    を engine 経由で呼ぶことで以下の 3 不変式を CI で担保する:

    1. 絶対 path 正常系: path 経由 plugin が `WorkflowEngine` 全体で動き、
       `submissions` / `WorkflowResult.submission_content` に正しく反映される
    2. 絶対 path 不在: path file 不在エラーが `WorkflowStepFailedError` に昇格する
    3. 相対 path × cwd 起点解決: sample TOML (`examples/workflow-sample/...`) の
       `path = "mypackage/formatters.py"` 表記が `monkeypatch.chdir` 環境で動く

`§3〜§5` の他 integration test は `build_executable` を patch するため、本ファイルだけが
PR4.5 の実 loader を engine 経由で通す唯一の保険となる。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.config import ConfigurationManager
from mixseek.workflow.engine import WorkflowEngine
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.models import WorkflowResult


@pytest.fixture
def team_deps() -> TeamDependencies:
    """integration test ローカルの `TeamDependencies`。

    `submissions` は default_factory で空 list 初期化される (`agents/leader/
    dependencies.py`)。`WorkflowEngine` が実行中に `MemberSubmission` を append する。
    """
    return TeamDependencies(
        execution_id="exec-pr5-engine",
        team_id="fn-path-engine",
        team_name="Function Path Engine Test",
        round_number=1,
    )


def _write_minimal_workflow_toml(toml_path: Path, *, plugin_path: str) -> None:
    """1 ステップ・1 function executor のミニ workflow TOML を書き出す。

    Args:
        toml_path: 出力先 TOML パス
        plugin_path: `[workflow.steps.executors.plugin] path` に書く文字列
            (絶対 path / 相対 path どちらでも可)
    """
    toml_path.write_text(
        "[workflow]\n"
        'workflow_id = "fn-path-engine"\n'
        'workflow_name = "Function Path Engine Test"\n'
        'default_model = "google-gla:gemini-2.5-flash"\n'
        "include_all_context = true\n"
        'final_output_format = "json"\n\n'
        "[[workflow.steps]]\n"
        'id = "s1"\n\n'
        "[[workflow.steps.executors]]\n"
        'name = "fn-prefix"\n'
        'type = "function"\n\n'
        "[workflow.steps.executors.plugin]\n"
        f'path = "{plugin_path}"\n'
        'function = "add_prefix"\n',
        encoding="utf-8",
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_workflow_engine_runs_function_plugin_loaded_from_absolute_path(
    tmp_path: Path,
    team_deps: TeamDependencies,
) -> None:
    """絶対 path で指定した function plugin が `WorkflowEngine.run` 全体で動く。"""
    # plugin file (絶対 path で参照)
    fn_file = tmp_path / "fmt.py"
    # WorkflowContext.build_task_context は JSON 文字列を渡してくるため、
    # `json.loads(input)["user_prompt"]` で user prompt を取り出してから整形する。
    fn_file.write_text(
        "import json\n\ndef add_prefix(input: str) -> str:\n    return f\"E2E:{json.loads(input)['user_prompt']}\"\n",
        encoding="utf-8",
    )

    toml_path = tmp_path / "workflow.toml"
    _write_minimal_workflow_toml(toml_path, plugin_path=str(fn_file))

    cm = ConfigurationManager(workspace=tmp_path)
    wf_settings = cm.load_workflow_settings(toml_path)

    engine = WorkflowEngine(settings=wf_settings, workspace=tmp_path)
    result = await engine.run(user_prompt="hello", deps=team_deps)

    # WorkflowResult 型と submission_content の構造
    assert isinstance(result, WorkflowResult)
    payload = json.loads(result.submission_content)
    assert payload == {
        "steps": {
            "s1": [
                {
                    "executor_name": "fn-prefix",
                    "status": "SUCCESS",
                    "content": "E2E:hello",
                    "error_message": None,
                }
            ]
        }
    }

    # team_deps.submissions に MemberSubmission が積まれている
    assert len(team_deps.submissions) == 1
    sub = team_deps.submissions[0]
    assert sub.agent_name == "fn-prefix"
    assert sub.agent_type == "function"
    assert sub.status == "SUCCESS"
    assert sub.content == "E2E:hello"

    # function executor は all_messages を発行しない
    assert result.all_messages == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_workflow_engine_raises_workflow_step_failed_when_path_missing(
    tmp_path: Path,
    team_deps: TeamDependencies,
) -> None:
    """path 不在エラーが `WorkflowEngine._execute_step` で `WorkflowStepFailedError` に昇格する。"""
    missing_path = tmp_path / "does_not_exist.py"
    # ファイルは作らない (`is_file()` で弾かれる経路を踏む)
    assert not missing_path.exists()

    toml_path = tmp_path / "missing_workflow.toml"
    _write_minimal_workflow_toml(toml_path, plugin_path=str(missing_path))

    cm = ConfigurationManager(workspace=tmp_path)
    wf_settings = cm.load_workflow_settings(toml_path)

    engine = WorkflowEngine(settings=wf_settings, workspace=tmp_path)

    with pytest.raises(WorkflowStepFailedError) as exc_info:
        await engine.run(user_prompt="hello", deps=team_deps)

    err = exc_info.value
    assert err.executor_name == "fn-prefix"
    # `_load_module_from_path` の文言を `_execute_step` が "failed to build executable: ..." で
    # ラップしている。prefix だけマッチさせて文言の細かい変更には強くする。
    assert err.error_message is not None
    assert "Failed to load function from path" in err.error_message

    # build_executable 失敗のため、submission は積まれる前に raise される
    assert team_deps.submissions == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_workflow_engine_resolves_relative_path_against_cwd(
    tmp_path: Path,
    team_deps: TeamDependencies,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """相対 path が **cwd 起点** で解決されることを、cwd と workspace を分離して実証する。

    `examples/workflow-sample/configs/workflows/workflow_research.toml` は
    `path = "mypackage/formatters.py"` という相対 path を採用しており、
    `cd $MIXSEEK_WORKSPACE` してから実行する前提 (README §path 方式)。

    回帰防止強度を上げるため、本テストでは cwd と workspace を **別ディレクトリ** にし、
    plugin file を **cwd 側のみ** に配置する。仮に将来実装が `workspace / path` 解決に
    変わった場合、`workspace_dir / "mypackage" / "formatters.py"` は存在しないため
    テストが落ちて回帰を検出できる (cwd と workspace を同じにしていた以前の構成では
    どちらの解決方式でも通ってしまっていた)。
    """
    # cwd 用と workspace 用のディレクトリを分離
    cwd_dir = tmp_path / "cwd_root"
    cwd_dir.mkdir()
    workspace_dir = tmp_path / "workspace_root"
    workspace_dir.mkdir()

    # plugin file は **cwd 側のみ** に配置 (workspace 側には作らない)
    package_dir = cwd_dir / "mypackage"
    package_dir.mkdir()
    fn_file = package_dir / "formatters.py"
    # WorkflowContext.build_task_context は JSON 文字列を渡してくるため、
    # `json.loads(input)["user_prompt"]` で user prompt を取り出してから整形する。
    fn_file.write_text(
        "import json\n\ndef add_prefix(input: str) -> str:\n    return f\"E2E:{json.loads(input)['user_prompt']}\"\n",
        encoding="utf-8",
    )

    # `workspace_dir` 配下に同名 plugin が無いことを明示確認 (回帰防止意図の表明)
    assert not (workspace_dir / "mypackage" / "formatters.py").exists()

    # TOML は workspace 側に配置 (`ConfigurationManager(workspace=workspace_dir)` 経由で読む)
    toml_path = workspace_dir / "workflow.toml"
    _write_minimal_workflow_toml(toml_path, plugin_path="mypackage/formatters.py")

    cm = ConfigurationManager(workspace=workspace_dir)
    wf_settings = cm.load_workflow_settings(toml_path)

    # cwd を **cwd_dir** に切り替えて相対 path を cwd 起点で解決させる。
    # monkeypatch.chdir は teardown 時に自動復帰するため他テストへの副作用なし。
    monkeypatch.chdir(cwd_dir)

    # workspace は cwd_dir と別。実装が cwd 起点でなければ
    # `workspace_dir/mypackage/formatters.py` が無いため `WorkflowStepFailedError` で落ちる。
    engine = WorkflowEngine(settings=wf_settings, workspace=workspace_dir)
    result = await engine.run(user_prompt="hello", deps=team_deps)

    # submission_content / team_deps.submissions に function 出力が反映される
    payload = json.loads(result.submission_content)
    assert payload["steps"]["s1"][0]["content"] == "E2E:hello"
    assert team_deps.submissions[0].content == "E2E:hello"
