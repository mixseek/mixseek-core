"""Workflow function executor サンプル。

入力契約:
    `{"user_prompt": str, "previous_steps": {"<step_id>": [{"executor_name", "status",
    "content", "error_message"}, ...]}}` 形式の JSON 文字列。
    `WorkflowContext.build_task_context` がこの形で渡してくる。

出力:
    Markdown 文字列 (str)。`WorkflowEngine` 側で `ExecutableResult.content` に格納される。

エラー方針:
    `json.loads` 失敗等は `ValueError` を素通しで raise する。
    `FunctionExecutable.run` 内部で捕捉され `ExecutableResult.status="ERROR"` に変換、
    `WorkflowEngine._execute_step` が `WorkflowStepFailedError` に昇格させる。

Note:
    `path` 方式で `_load_module_from_path` から直接読み込まれるため、
    本ファイルは Python package である必要はない (`__init__.py` 不要)。
"""

from __future__ import annotations

import json
from typing import Any


def format_as_markdown(input: str) -> str:
    """`gather` ステップの出力を Markdown セクションに整形する。

    Args:
        input: `WorkflowContext.build_task_context` が生成する JSON 文字列。

    Returns:
        Markdown 文字列。`previous_steps` が空 (Step 1 で呼ばれた等) なら空文字列を返す。
        `user_prompt` は `WorkflowContext.build_task_context` が後段 executor の入力 JSON に
        トップレベルキーとして自動挿入するため、本関数の出力には含めない (二重挿入回避)。
    """
    payload = json.loads(input)
    # `or {}` を付けない: 空辞書 {} は「前段なし」を表す有意味値で、上書きしない。
    previous: dict[str, list[dict[str, Any]]] = payload.get("previous_steps", {})

    gather_outputs = previous.get("gather", [])
    if not gather_outputs:
        # まだ前段が走っていない (Step 1 で呼ばれた等)
        return ""

    lines: list[str] = []
    for output in gather_outputs:
        executor_name = output.get("executor_name", "<unknown>")
        status = output.get("status", "")
        content = output.get("content", "")
        error_message = output.get("error_message")

        lines.append(f"## {executor_name}")
        lines.append("")
        if status == "ERROR":
            lines.append(f"> ⚠ Error: {error_message or 'unknown error'}")
            lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
