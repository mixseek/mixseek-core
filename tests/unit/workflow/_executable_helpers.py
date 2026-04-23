"""`test_executable_*` 共通ヘルパー。

`_sample_function` / `_sample_non_callable` は `_load_function` の動的 import 先として
`test_executable_builder.py` から `tests.unit.workflow._executable_helpers.<name>` の形で参照される。

pytest は `test_*.py` のみ collection するため、本ファイル（`_executable_helpers.py`）は
テスト収集対象外。
"""

from unittest.mock import AsyncMock, MagicMock


def make_agent_mock(
    name: str = "agent-a",
    agent_type: str = "plain",
) -> MagicMock:
    """`BaseMemberAgent` の MagicMock を作成。`execute` は AsyncMock。"""
    agent = MagicMock()
    agent.agent_name = name
    agent.agent_type = agent_type
    agent.execute = AsyncMock()
    return agent


def sample_function(input: str) -> str:
    """`_load_function` 動的 import テスト用の callable。"""
    return f"sample: {input}"


sample_non_callable = 42
