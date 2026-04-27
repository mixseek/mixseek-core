"""Workflow mode - 固定ステップで agent/function を順次・並列実行するモード。

チームモード（Leader が LLM 推論で member を動的選択）とは別モードで、TOML の
`[workflow]` セクションで宣言された固定ステップを順に実行する。各ステップ内では
複数 executor を並列実行（1 個なら直列）する。

ストレージ層（DuckDB）・Evaluator・PromptBuilder はチームモードと同じ API を使い、
`StrategyResult` でチームモードの Leader 出力と互換性を保つ。
"""

from mixseek.workflow.engine import WorkflowEngine
from mixseek.workflow.exceptions import WorkflowStepFailedError
from mixseek.workflow.executable import (
    AgentExecutable,
    Executable,
    FunctionExecutable,
    build_executable,
)
from mixseek.workflow.models import (
    ExecutableOutput,
    ExecutableResult,
    StepResult,
    StrategyResult,
    WorkflowContext,
    WorkflowResult,
)

__all__ = [
    "AgentExecutable",
    "Executable",
    "ExecutableOutput",
    "ExecutableResult",
    "FunctionExecutable",
    "StepResult",
    "StrategyResult",
    "WorkflowContext",
    "WorkflowEngine",
    "WorkflowResult",
    "WorkflowStepFailedError",
    "build_executable",
]
