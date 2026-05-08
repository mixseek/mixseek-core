"""Workflow Function Plugin の `path` ロード方式 配線確認 integration test。

PR4.5 で追加された `FunctionPluginMetadata.path` 経由での function executor 構築・実行を、
TOML → `ConfigurationManager.load_workflow_settings` → `build_executable` → `Executable.run`
の end-to-end で 1 本のみ確認する。

`WorkflowEngine` 全体は本ファイルでは扱わない（PR5 で別途 end-to-end をカバーする）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.config import ConfigurationManager
from mixseek.config.schema import FunctionExecutorSettings
from mixseek.workflow.executable import FunctionExecutable, build_executable


@pytest.fixture
def team_deps() -> TeamDependencies:
    """integration テストローカルの `TeamDependencies`（unit 側 conftest は参照不可）。"""
    return TeamDependencies(
        execution_id="exec-pr4-5",
        team_id="fn-path-integration",
        team_name="Integration Test",
        round_number=1,
    )


@pytest.mark.integration
def test_workflow_function_path_loading_end_to_end(
    tmp_path: Path,
    team_deps: TeamDependencies,
) -> None:
    """workflow TOML（`path` 指定）→ load → build_executable → run の配線確認。

    `path` は **絶対 path** で TOML に書き込む（member 流の挙動踏襲のため、
    workspace 起点解決はしない）。`tmp_path` 経由で再現性を担保する。
    """
    # 1. function file を配置（絶対 path で参照される）
    fn_file = tmp_path / "formatters.py"
    fn_file.write_text(
        "def to_upper(x: str) -> str:\n    return x.upper()\n",
        encoding="utf-8",
    )

    # 2. workflow TOML を書き出し（path には絶対 path を埋め込む）
    toml_path = tmp_path / "workflow.toml"
    toml_path.write_text(
        "[workflow]\n"
        'workflow_id = "fn-path-integration"\n'
        'workflow_name = "fn-path-integration"\n'
        'default_model = "google-gla:gemini-2.5-flash"\n'
        "[[workflow.steps]]\n"
        'id = "s1"\n'
        "[[workflow.steps.executors]]\n"
        'name = "upper"\n'
        'type = "function"\n'
        "[workflow.steps.executors.plugin]\n"
        f'path = "{fn_file}"\n'
        'function = "to_upper"\n',
        encoding="utf-8",
    )

    # 3. ConfigurationManager で読み込み
    cm = ConfigurationManager(workspace=tmp_path)
    wf_settings = cm.load_workflow_settings(toml_path)
    fn_cfg = wf_settings.steps[0].executors[0]
    assert isinstance(fn_cfg, FunctionExecutorSettings)
    assert fn_cfg.plugin.path == str(fn_file)
    assert fn_cfg.plugin.module is None

    # 4. build_executable で executable 生成
    executable = build_executable(fn_cfg, team_deps, default_model=wf_settings.default_model)
    assert isinstance(executable, FunctionExecutable)

    # 5. 実行（function 単体の async 経路を確認）
    result = asyncio.run(executable.run("hello"))
    assert result.status == "SUCCESS"
    assert result.content == "HELLO"
