"""Workflow mode の実行エンジン。

`WorkflowEngine` は `WorkflowSettings` に従い:
    1. ステップを定義順に実行（ステップ間は直列）
    2. ステップ内は `asyncio.gather` で並列実行（`executor` が 1 件なら直列）
    3. 各 executor 結果を `TeamDependencies.submissions` に蓄積（team mode と同形式）
    4. 全ステップ完了後に `WorkflowResult` を構築（submission_content 整形 + all_messages
       連結 + total_usage 加算）

設計書の不変条件（参考: `workflow-mode-plan.md` §5.2.4 / §10）:
    D3: `all_messages` は **step 順 × executor 定義順** で連結する
    D4: function executor の `status="ERROR"` は `WorkflowStepFailedError` に即昇格し、
        後続ステップは実行しない（agent の ERROR は step 継続）
    submission_content: `user_prompt` を**絶対に含めない**
        （`UserPromptBuilder` 経由で submission_content が次ラウンド prompt に埋め込まれるため、
         含めると Round 再帰膨張を起こす）
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission
from mixseek.config.schema import WorkflowSettings, WorkflowStepSettings
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.executable import Executable, _logfire_span, build_executable
from mixseek.workflow.models import (
    ExecutableOutput,
    StepResult,
    WorkflowContext,
    WorkflowResult,
)

logger = logging.getLogger("mixseek.workflow.engine")


class WorkflowEngine:
    """固定ステップの workflow 実行エンジン。

    Attributes:
        settings: workflow 設定（ステップ・executor 定義）
        workspace: `AgentExecutorSettings` の bundled `system_instruction` 解決に使用
    """

    def __init__(
        self,
        settings: WorkflowSettings,
        workspace: Path | None = None,
    ) -> None:
        self.settings = settings
        self.workspace = workspace

    async def run(
        self,
        user_prompt: str,
        deps: TeamDependencies,
    ) -> WorkflowResult:
        """workflow 全体を実行し `WorkflowResult` を返す。

        team mode の Leader span 階層に相当する `workflow.engine.run` span を張る
        （logfire 非導入環境では `nullcontext`）。
        """
        with _logfire_span(
            "workflow.engine.run",
            workflow_id=deps.team_id,
            workflow_name=deps.team_name,
            round_number=deps.round_number,
            step_count=len(self.settings.steps),
        ):
            context = WorkflowContext(user_prompt=user_prompt)
            for step in self.settings.steps:
                step_result = await self._execute_step(step, context, deps)
                context.add_step_result(step.id, step_result)

            submission_content = self._build_submission_content(
                context,
                include_all=self.settings.include_all_context,
                fmt=self.settings.final_output_format,
            )
            # D3: step 順 × executor 定義順で all_messages を連結
            merged_messages: list[ModelMessage] = []
            total_usage = RunUsage()
            for r in context.step_results.values():
                for out in r.outputs:
                    merged_messages.extend(out.result.all_messages)
                    total_usage = _add_usage(total_usage, out.result.usage)
            return WorkflowResult(
                submission_content=submission_content,
                all_messages=merged_messages,
                total_usage=total_usage,
            )

    async def _execute_step(
        self,
        step: WorkflowStepSettings,
        context: WorkflowContext,
        deps: TeamDependencies,
    ) -> StepResult:
        """1 ステップを実行。`build_executable` 例外と function ERROR は
        `WorkflowStepFailedError` に昇格させ、後続ステップを中断する。
        """
        executables: list[Executable] = []
        for cfg in step.executors:
            try:
                executables.append(
                    build_executable(
                        cfg,
                        deps,
                        workspace=self.workspace,
                        default_model=self.settings.default_model,
                    )
                )
            except Exception as e:
                raise WorkflowStepFailedError(
                    step_id=step.id,
                    executor_name=getattr(cfg, "name", "<unknown>"),
                    error_message=f"failed to build executable: {e}",
                ) from e

        task_context = context.build_task_context(include_all=self.settings.include_all_context)
        # Executable.run は例外を漏らさない契約のため return_exceptions=False で安全
        results = await asyncio.gather(
            *[exe.run(task_context) for exe in executables],
            return_exceptions=False,
        )

        # gather 完了後に executor 定義順で deps.submissions を一括追加する。
        # _run_one 内で append すると並列時に完了順になり、定義順保証が崩れる。
        for exe, result in zip(executables, results, strict=True):
            deps.submissions.append(
                MemberSubmission(
                    agent_name=exe.name,
                    agent_type=exe.executor_type,
                    content=result.content,
                    status=result.status,
                    error_message=result.error_message,
                    usage=result.usage,
                    execution_time_ms=result.execution_time_ms,
                    timestamp=datetime.now(UTC),
                    # 空リストは None に戻す（既存 team mode の custom agent と同じ表現）
                    all_messages=result.all_messages or None,
                )
            )

        # D4: function ERROR は即昇格（WARNING は対象外、agent ERROR も対象外）
        for exe, result in zip(executables, results, strict=True):
            if exe.executor_type == "function" and result.status == "ERROR":
                raise WorkflowStepFailedError(
                    step_id=step.id,
                    executor_name=exe.name,
                    error_message=result.error_message,
                )

        return StepResult(
            step_id=step.id,
            outputs=[
                ExecutableOutput(name=e.name, executor_type=e.executor_type, result=r)
                for e, r in zip(executables, results, strict=True)
            ],
        )

    def _build_submission_content(
        self,
        context: WorkflowContext,
        *,
        include_all: bool,
        fmt: Literal["json", "text"],
    ) -> str:
        """submission_content を 4 ケース (include_all × fmt) で整形。

        invariant:
            返値文字列に `user_prompt` を一切含めない（Round 再帰膨張回避、§10）。
            `UserPromptBuilder.format_submission_history` が次ラウンド以降の prompt に
            `submission_content` を埋め込むため、含めると指数膨張する。
        """
        final_step_id = self.settings.steps[-1].id
        final_outputs = context.step_results[final_step_id].outputs

        if fmt == "json":
            if include_all:
                steps = {
                    sid: [WorkflowContext._serialize(o) for o in r.outputs] for sid, r in context.step_results.items()
                }
            else:
                steps = {final_step_id: [WorkflowContext._serialize(o) for o in final_outputs]}
            return json.dumps({"steps": steps}, ensure_ascii=False)

        # fmt == "text"
        if include_all:
            sections = [
                f"## {sid}\n\n" + "\n\n".join(_format_executor_text(o, heading="###") for o in r.outputs)
                for sid, r in context.step_results.items()
            ]
            return "\n\n".join(sections)
        return "\n\n".join(_format_executor_text(o, heading="##") for o in final_outputs)


def _format_executor_text(out: ExecutableOutput, *, heading: str) -> str:
    """text 整形用の見出し + 本文。ERROR 時は見出しに `(ERROR: <msg>)` 併記する。"""
    if out.result.status == "ERROR":
        header = f"{heading} {out.name} (ERROR: {out.result.error_message})"
    else:
        header = f"{heading} {out.name}"
    return f"{header}\n\n{out.result.content}"


def _add_usage(a: RunUsage, b: RunUsage) -> RunUsage:
    """`input_tokens` / `output_tokens` / `requests` を加算した `RunUsage` を返す。"""
    return RunUsage(
        input_tokens=(a.input_tokens or 0) + (b.input_tokens or 0),
        output_tokens=(a.output_tokens or 0) + (b.output_tokens or 0),
        requests=(a.requests or 0) + (b.requests or 0),
    )
