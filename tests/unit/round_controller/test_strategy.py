"""Unit tests for ExecutionStrategy / LeaderStrategy / WorkflowStrategy.

PR3 carve-out 対応: team mode の Member 生成 + Leader 実行を `LeaderStrategy` に、
workflow mode の `WorkflowEngine` を `WorkflowStrategy` に分離した実装の挙動を担保する。
"""

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import RunUsage
from pydantic_ai.messages import ModelMessage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.config.schema import (
    AgentExecutorSettings,
    MemberAgentSettings,
    TeamSettings,
    WorkflowSettings,
    WorkflowStepSettings,
)
from mixseek.round_controller.strategy import LeaderStrategy, WorkflowStrategy
from mixseek.workflow.models import StrategyResult, WorkflowResult


def _build_team_settings(members: list[MemberAgentSettings] | None = None) -> TeamSettings:
    """テスト用に最小の TeamSettings を Python から直接構築する。"""
    return TeamSettings(
        team_id="strategy-team",
        team_name="Strategy Team",
        leader={
            "system_instruction": "You are a helpful assistant",
            "model": "google-gla:gemini-2.5-flash-lite",
        },
        members=members or [],
    )


def _build_member_settings(name: str) -> MemberAgentSettings:
    """bundled instruction lookup を回避するため system_instruction を明示する。"""
    return MemberAgentSettings(
        agent_name=name,
        agent_type="plain",
        tool_description=f"tool description for {name}",
        model="google-gla:gemini-2.5-flash-lite",
        system_instruction="custom system instruction",
    )


def _build_team_deps() -> TeamDependencies:
    return TeamDependencies(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        team_id="strategy-team",
        team_name="Strategy Team",
        round_number=1,
    )


def _build_workflow_settings() -> WorkflowSettings:
    """WorkflowEngine は patch されるため、最小 WorkflowSettings で十分。"""
    return WorkflowSettings(
        workflow_id="wf1",
        workflow_name="WF",
        steps=[
            WorkflowStepSettings(
                id="s1",
                executors=[
                    AgentExecutorSettings(name="agent-1", type="plain"),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
@patch("mixseek.round_controller.strategy.create_leader_agent")
async def test_leader_strategy_execute_runs_leader_agent(
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """LeaderStrategy.execute が Leader Agent を起動して StrategyResult を返すこと。"""
    sentinel_messages = cast(list[ModelMessage], ["msg-1", "msg-2"])
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "leader submission"
    mock_result.all_messages.return_value = sentinel_messages
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    strategy = LeaderStrategy(_build_team_settings(), tmp_path)
    deps = _build_team_deps()
    result = await strategy.execute("user prompt", deps)

    assert isinstance(result, StrategyResult)
    assert result.submission_content == "leader submission"
    assert result.all_messages is sentinel_messages

    # create_leader_agent には team_config と member_agents が渡される
    mock_create_leader.assert_called_once()
    team_config_arg, member_agents_arg = mock_create_leader.call_args.args
    assert team_config_arg.team_id == "strategy-team"
    assert team_config_arg.team_name == "Strategy Team"
    # members 0 件の TeamSettings なので member_agents は空 dict
    assert member_agents_arg == {}

    # leader_agent.run には user_prompt と deps が渡される
    mock_agent.run.assert_awaited_once_with("user prompt", deps=deps)


@pytest.mark.asyncio
@patch("mixseek.round_controller.strategy.MemberAgentFactory")
@patch("mixseek.round_controller.strategy.create_leader_agent")
async def test_leader_strategy_uses_team_settings_members(
    mock_create_leader: MagicMock,
    mock_factory: MagicMock,
    tmp_path: Path,
) -> None:
    """TeamSettings.members 件数分だけ MemberAgentFactory.create_agent が呼ばれ、
    生成された agent が agent_name キーで Leader に渡されること。
    """
    members = [_build_member_settings("member-a"), _build_member_settings("member-b")]
    mock_create_leader.return_value = AsyncMock()
    mock_create_leader.return_value.run.return_value = MagicMock(output="ignored", all_messages=lambda: [])

    # create_agent ごとに識別可能な sentinel を返す（member_agents 配線検証用）
    sentinel_agents = {"member-a": object(), "member-b": object()}
    mock_factory.create_agent.side_effect = lambda config: sentinel_agents[config.name]

    strategy = LeaderStrategy(_build_team_settings(members=members), tmp_path)
    await strategy.execute("user prompt", _build_team_deps())

    # MemberAgentFactory.create_agent は member 数分だけ TOML 定義順に呼ばれる
    assert mock_factory.create_agent.call_count == 2
    created_names = [call.args[0].name for call in mock_factory.create_agent.call_args_list]
    assert created_names == ["member-a", "member-b"]

    # create_leader_agent には agent_name をキーとする member_agents 辞書が渡る
    _team_config_arg, member_agents_arg = mock_create_leader.call_args.args
    assert set(member_agents_arg.keys()) == {"member-a", "member-b"}
    assert member_agents_arg["member-a"] is sentinel_agents["member-a"]
    assert member_agents_arg["member-b"] is sentinel_agents["member-b"]


@pytest.mark.asyncio
@patch("mixseek.round_controller.strategy.WorkflowEngine")
async def test_workflow_strategy_calls_engine(
    mock_engine_class: MagicMock,
    tmp_path: Path,
) -> None:
    """WorkflowStrategy.execute が WorkflowEngine.run を 1 回呼んで StrategyResult を返すこと。"""
    sentinel_messages = cast(list[ModelMessage], ["wf-msg"])
    mock_engine = MagicMock()
    mock_engine.run = AsyncMock(
        return_value=WorkflowResult(
            submission_content="workflow output",
            all_messages=sentinel_messages,
            total_usage=RunUsage(input_tokens=10, output_tokens=5, requests=1),
        )
    )
    mock_engine_class.return_value = mock_engine

    settings = _build_workflow_settings()
    strategy = WorkflowStrategy(settings, tmp_path)
    deps = _build_team_deps()
    result = await strategy.execute("user prompt", deps)

    # WorkflowEngine(settings, workspace=workspace) で初期化されている
    mock_engine_class.assert_called_once_with(settings, workspace=tmp_path)
    mock_engine.run.assert_awaited_once_with("user prompt", deps)

    assert isinstance(result, StrategyResult)
    assert result.submission_content == "workflow output"
    assert result.all_messages is sentinel_messages
    # total_usage は StrategyResult に伝搬しない（観測は workflow パッケージ内部のみ）
    assert not hasattr(result, "total_usage")


def test_strategy_result_structure() -> None:
    """StrategyResult は team mode の result.output / result.all_messages() と互換のシェイプを返す。"""
    msgs = cast(list[ModelMessage], ["m1", "m2"])
    result = StrategyResult(submission_content="content", all_messages=msgs)

    assert result.submission_content == "content"
    assert result.all_messages is msgs
    # team mode 既存 controller の `submission_content: str = result.output`
    # `message_history = result.all_messages()` と完全に同じシェイプ
    assert isinstance(result.submission_content, str)
    assert isinstance(result.all_messages, list)
