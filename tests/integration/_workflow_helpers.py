"""Workflow integration test 共通ヘルパー。

`tests/integration/test_workflow_*.py` の 3 テスト (`test_workflow_round_controller.py`,
`test_workflow_orchestrator.py`, `test_workflow_hard_failure.py`) で共通利用する
`FakeExecutable` / `install_fake_builder` / TOML 生成ヘルパーを集約する。

pytest は `_` プレフィックスのファイルを test 収集対象外にするため、本ファイルは
collection されない (`_` 命名規約)。

Note:
    `tests/unit/workflow/_engine_helpers.py` とは API を意図的に分けている。

    - `FakeExecutable.result_factory` は **call_count を受け取る** シグネチャ
      (`Callable[[int], ExecutableResult]`)。Round 別挙動 (Round 1 SUCCESS /
      Round 2 ERROR 等) を仕込むため。unit 版は引数なし (`Callable[[], ...]`) で
      別物。
    - `noop_function` を本ファイル内に置くことで `module = "tests.integration.
      _workflow_helpers"` を TOML に書ける。`build_executable` を patch する
      テストでは実行は呼ばれないため、schema 検証だけパスすれば良い。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import RunUsage

from mixseek.workflow.models import ExecutableResult


@dataclass
class FakeExecutable:
    """integration test 用の `Executable` 実装。

    `mixseek.workflow.engine.build_executable` を fake mapping に差し替えると、
    `WorkflowEngine` が executor 構築時に本クラスのインスタンスを取得する。
    Engine 本体 (`asyncio.gather` / 昇格判定 / submission 配線 / message 連結) は
    実物のまま動かせるので、LLM / 認証情報なしで CI を安定化できる。

    Attributes:
        name: executor 名 (TOML の `[[workflow.steps.executors]] name` と一致させる)
        executor_type: `"plain"` / `"function"` / `"web_search"` 等。
            `"function"` のときに `WorkflowEngine` の昇格判定が動く。
        result_factory: 1-indexed の `call_count` を受け取り `ExecutableResult` を返す
            関数。Round 別挙動を仕込みたい場合に call_count で分岐する。
        call_count: 呼び出し回数 (1 origin, run() 内でインクリメント)
        last_input: 最後に渡された input 文字列 (assert 用)
    """

    name: str
    executor_type: str
    result_factory: Callable[[int], ExecutableResult]
    call_count: int = 0
    last_input: str | None = field(default=None)

    async def run(self, input: str) -> ExecutableResult:
        self.call_count += 1
        self.last_input = input
        return self.result_factory(self.call_count)


def install_fake_builder(
    monkeypatch: pytest.MonkeyPatch,
    fakes: dict[str, FakeExecutable],
) -> None:
    """`mixseek.workflow.engine.build_executable` を fake mapping に差し替える。

    `WorkflowStrategy` → `WorkflowEngine` 経路では必ず `engine.build_executable`
    を経由するため、Python の遅延名前解決 (実行時 attribute lookup) によって
    monkeypatch 後でも fake が呼ばれる。

    Args:
        monkeypatch: pytest 標準の MonkeyPatch fixture
        fakes: executor 名 → `FakeExecutable` のマッピング。
            `cfg.name` で lookup されるため、TOML の executor 名と一致させる。
    """
    from mixseek.workflow import engine as engine_module

    def _fake_builder(cfg: Any, deps: Any, *, workspace: Any, default_model: str) -> Any:
        return fakes[cfg.name]

    monkeypatch.setattr(engine_module, "build_executable", _fake_builder)


def success(content: str = "ok", usage: RunUsage | None = None) -> ExecutableResult:
    """SUCCESS の `ExecutableResult` を生成する short-hand。"""
    return ExecutableResult(
        content=content,
        execution_time_ms=1.0,
        status="SUCCESS",
        usage=usage or RunUsage(input_tokens=10, output_tokens=5, requests=1),
    )


def error(msg: str = "boom") -> ExecutableResult:
    """ERROR の `ExecutableResult` を生成する short-hand。"""
    return ExecutableResult(
        content="",
        execution_time_ms=1.0,
        status="ERROR",
        error_message=msg,
    )


_DEFAULT_STEPS_TEXT = (
    "[[workflow.steps]]\n"
    'id = "s1"\n\n'
    "[[workflow.steps.executors]]\n"
    'name = "agent-a"\n'
    'type = "plain"\n\n'
    "[[workflow.steps.executors]]\n"
    'name = "agent-b"\n'
    'type = "plain"\n\n'
    "[[workflow.steps]]\n"
    'id = "s2"\n\n'
    "[[workflow.steps.executors]]\n"
    'name = "fn-formatter"\n'
    'type = "function"\n\n'
    "[workflow.steps.executors.plugin]\n"
    'module = "tests.integration._workflow_helpers"\n'
    'function = "noop_function"\n\n'
    "[[workflow.steps]]\n"
    'id = "s3"\n\n'
    "[[workflow.steps.executors]]\n"
    'name = "agent-c"\n'
    'type = "plain"\n'
)


def write_workflow_toml(
    path: Path,
    *,
    workflow_id: str = "test-workflow-001",
    workflow_name: str = "Test Workflow",
    steps_text: str | None = None,
) -> None:
    """`tmp_path` 配下に workflow TOML を書き出す。

    デフォルトの `steps_text` は 3 ステップ構成 (s1: agent-a + agent-b 並列,
    s2: function fn-formatter, s3: agent-c) で、
    `test_workflow_round_controller.py` の標準形に揃えてある。

    Args:
        path: 出力先 TOML パス
        workflow_id: TOML `[workflow] workflow_id`
        workflow_name: TOML `[workflow] workflow_name`
        steps_text: ステップ定義部分 (`[[workflow.steps]]` 以降) を完全置換したい
            ときに渡す。`None` のときはデフォルト 3 ステップ構成を使う。
    """
    body = _DEFAULT_STEPS_TEXT if steps_text is None else steps_text
    text = (
        "[workflow]\n"
        f'workflow_id = "{workflow_id}"\n'
        f'workflow_name = "{workflow_name}"\n'
        'default_model = "google-gla:gemini-2.5-flash"\n'
        "include_all_context = true\n"
        'final_output_format = "json"\n\n' + body
    )
    path.write_text(text, encoding="utf-8")


def noop_function(input: str) -> str:
    """`_load_function` 経路の動的 import target。

    `module = "tests.integration._workflow_helpers"` を TOML に書く必要があるが、
    integration テストでは `build_executable` を `install_fake_builder` で
    完全 bypass するため、本関数は実行されない。schema 検証 (preflight 含む) を
    通すための placeholder。
    """
    return f"noop: {input}"


_ORCHESTRATOR_ENV_VARS: tuple[str, ...] = (
    "MIXSEEK_MAX_ROUNDS",
    "MIXSEEK_MIN_ROUNDS",
    "MIXSEEK_TIMEOUT_PER_TEAM_SECONDS",
    "MIXSEEK_MAX_RETRIES_PER_TEAM",
    "MIXSEEK_SUBMISSION_TIMEOUT_SECONDS",
    "MIXSEEK_JUDGMENT_TIMEOUT_SECONDS",
)


def clear_orchestrator_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`OrchestratorSettings` 関連の環境変数を削除する。

    `tests/config/test_orchestrator_settings.py:223` 等が `MIXSEEK_MIN_ROUNDS=3`
    を直接 ``os.environ`` に設定して teardown しないため、test 順序によっては
    `OrchestratorTomlSource` の TOML 値 (`min_rounds=1`) が環境変数で上書きされ、
    judgment が呼ばれない経路 (Stage (a) の min_rounds 早期リターン) に入って
    本テストが flaky になる。

    `monkeypatch.delenv` は teardown 時に元の値を復元するので、本関数を呼ぶこと
    自体に副作用はない (削除した環境変数は teardown 時に復元される)。
    """
    for var in _ORCHESTRATOR_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
