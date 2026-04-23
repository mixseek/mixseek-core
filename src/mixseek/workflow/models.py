"""Workflow mode の実行データモデル。

Workflow mode は固定ステップで agent/function を順次・並列実行する mixseek の
実行モード。本モジュールは `WorkflowEngine` から利用される:

- `ExecutableResult`: 各 executor の実行結果（agent/function 共通）
- `ExecutableOutput`: 1 executor の結果をラップ
- `StepResult`: 1 ステップ内の全 executor 結果
- `WorkflowContext`: ステップ間のデータ伝搬コンテナ
- `WorkflowResult`: Engine.run() 返り値
- `StrategyResult`: RoundController 統一戻り値（team/workflow 両モード共通）

team mode との互換性:
    `StrategyResult(submission_content, all_messages)` は現行 `RoundController`
    (controller.py L309-310) が Leader Agent result から使う `result.output` /
    `result.all_messages()` の 2 フィールドと 1:1 対応する。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage


@dataclass
class ExecutableResult:
    """Executable.run() 返り値。

    status は `MemberAgentResult.status` (ResultStatus enum, 小文字) を `.value.upper()`
    で大文字化したもの。`DuckDB` 側の `MemberSubmissionsRecord.successful_submissions`
    が `"SUCCESS"` 比較を使うため（leader/models.py L43）、大文字統一で team mode と
    一致させる。

    WARNING は successful/failed どちらの集計にも入らないが submission 保存は行う
    （既存 team と同じ）。`FunctionExecutable` は SUCCESS / ERROR のみ発行する。
    """

    content: str
    execution_time_ms: float
    status: Literal["SUCCESS", "ERROR", "WARNING"] = "SUCCESS"
    error_message: str | None = None
    usage: RunUsage = field(default_factory=RunUsage)
    all_messages: list[ModelMessage] = field(default_factory=list)


@dataclass
class ExecutableOutput:
    """1 executor の実行結果を name / executor_type と共にラップする。"""

    name: str
    executor_type: str
    result: ExecutableResult


@dataclass
class StepResult:
    """1 ステップ内の全 executor 結果（並列なら複数、単一なら 1 要素）。"""

    step_id: str
    outputs: list[ExecutableOutput]


class WorkflowContext:
    """ステップ間のデータ伝搬コンテナ。

    `step_results` は挿入順保持 dict（Python 3.7+ 保証）。Engine は各ステップ完了後に
    `add_step_result()` で結果を蓄積し、後続ステップの executor に `build_task_context`
    で JSON として渡す。
    """

    def __init__(self, user_prompt: str) -> None:
        self.user_prompt = user_prompt
        self.step_results: dict[str, StepResult] = {}

    def add_step_result(self, step_id: str, result: StepResult) -> None:
        """ステップ結果を挿入順に記録する。"""
        self.step_results[step_id] = result

    def build_task_context(self, *, include_all: bool) -> str:
        """executor (agent/function 双方) に渡す JSON 入力を組み立てる。

        トップレベルキーは常に `{"user_prompt", "previous_steps"}` の 2 つ。
        agent の system_instruction で「入力は JSON 文字列、json.loads して参照」を
        明示する責務は TOML 設計者側にある。function は自身で `json.loads(input)` する。

        Args:
            include_all: True なら全過去ステップを、False なら直前 1 ステップのみ
                `previous_steps` に含める（`WorkflowSettings.include_all_context`）。
        """
        previous = self._all_previous_steps() if include_all else self._last_previous_step()
        payload = {"user_prompt": self.user_prompt, "previous_steps": previous}
        return json.dumps(payload, ensure_ascii=False)

    def _all_previous_steps(self) -> dict[str, list[dict[str, Any]]]:
        return {
            step_id: [self._serialize(out) for out in result.outputs] for step_id, result in self.step_results.items()
        }

    def _last_previous_step(self) -> dict[str, list[dict[str, Any]]]:
        """直前 1 ステップのみ。Step 1 実行時（`step_results` 空）は `{}` を返す。"""
        if not self.step_results:
            return {}
        last_id, last_result = next(reversed(self.step_results.items()))
        return {last_id: [self._serialize(out) for out in last_result.outputs]}

    @staticmethod
    def _serialize(out: ExecutableOutput) -> dict[str, Any]:
        """4 フィールド固定のシリアライズ形式: executor_name / status / content / error_message。

        agent executor は system_instruction でこのスキーマを読み取るよう指示される。
        function executor は json.loads して dict として参照する。
        """
        return {
            "executor_name": out.name,
            "status": out.result.status,
            "content": out.result.content,
            "error_message": out.result.error_message,
        }


@dataclass
class WorkflowResult:
    """WorkflowEngine.run の返り値（workflow パッケージ内部用）。

    team mode との互換性:
        現行 `RoundController._execute_single_round` (controller.py L308-310) が
        Leader Agent の `result.output` (str) と `result.all_messages()` (list) のみ
        を使うため、`WorkflowResult` の先頭 2 フィールドと完全互換。`total_usage` は
        workflow パッケージ内の観測用で、`StrategyResult` には伝搬せず RoundController
        からは参照されない。
    """

    submission_content: str
    all_messages: list[ModelMessage]
    total_usage: RunUsage


@dataclass
class StrategyResult:
    """RoundController 統一戻り値。

    team mode との互換性:
        現行 `controller.py` L309-310 の
            submission_content: str = result.output
            message_history = result.all_messages()
        と 1:1 対応する 2 フィールドを包む。team mode の Leader Agent result から
        `StrategyResult` への移行時にデータ損失なし。
    """

    submission_content: str
    all_messages: list[ModelMessage]
