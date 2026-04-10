"""Unit tests for broadcast member dispatch mode.

Feature: Broadcast Member Dispatch
Design: docs/superpowers/specs/2026-04-10-broadcast-member-dispatch-design.md
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.models.member_agent import MemberAgentResult, ResultStatus
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController


def _create_mock_member_agent(
    content: str = "mock result",
    agent_name: str = "mock-agent",
    agent_type: str = "plain",
) -> AsyncMock:
    """Create a mock BaseMemberAgent with standard response."""
    mock = AsyncMock(spec=BaseMemberAgent)
    mock.execute.return_value = MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content=content,
        agent_name=agent_name,
        agent_type=agent_type,
        timestamp=datetime.now(UTC),
        execution_time_ms=100,
        usage_info={"input_tokens": 50, "output_tokens": 30},
        error_message=None,
        error_code=None,
        retry_count=0,
        max_retries_exceeded=False,
        metadata={},
        all_messages=None,
    )
    mock.config = MagicMock()
    mock.config.name = agent_name
    mock.config.type = agent_type
    return mock


def _create_failing_mock_member_agent(
    agent_name: str = "failing-agent",
    agent_type: str = "plain",
) -> AsyncMock:
    """Create a mock BaseMemberAgent that raises an exception."""
    mock = AsyncMock(spec=BaseMemberAgent)
    mock.execute.side_effect = RuntimeError("Agent execution failed")
    mock.config = MagicMock()
    mock.config.name = agent_name
    mock.config.type = agent_type
    return mock


def _create_deps() -> TeamDependencies:
    """Create standard TeamDependencies for testing."""
    return TeamDependencies(
        execution_id=str(uuid4()),
        team_id="test-team",
        team_name="Test Team",
        round_number=1,
    )


class TestRunSingleMember:
    """Tests for RoundController._run_single_member."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_success_records_submission(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """成功したメンバー実行がMemberSubmissionとして記録される."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        deps = _create_deps()
        mock_agent = _create_mock_member_agent(
            content="search result",
            agent_name="web-searcher",
            agent_type="web_search",
        )

        await controller._run_single_member(
            agent_name="web-searcher",
            agent_type="web_search",
            member_agent=mock_agent,
            user_prompt="Analyze this topic",
            deps=deps,
        )

        assert len(deps.submissions) == 1
        sub = deps.submissions[0]
        assert sub.agent_name == "web-searcher"
        assert sub.agent_type == "web_search"
        assert sub.content == "search result"
        assert sub.status == "SUCCESS"
        assert sub.error_message is None
        assert sub.execution_time_ms is not None

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_error_records_error_submission(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """例外を送出したメンバーがERROR状態のMemberSubmissionとして記録される."""
        mock_store_class.return_value = AsyncMock()

        team_config_path = Path.cwd() / "tests" / "fixtures" / "team_broadcast.toml"
        task = OrchestratorTask(
            execution_id=str(uuid4()),
            user_prompt="Test prompt",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=1,
            min_rounds=1,
        )
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        deps = _create_deps()
        mock_agent = _create_failing_mock_member_agent(
            agent_name="failing-agent",
            agent_type="plain",
        )

        await controller._run_single_member(
            agent_name="failing-agent",
            agent_type="plain",
            member_agent=mock_agent,
            user_prompt="Analyze this topic",
            deps=deps,
        )

        assert len(deps.submissions) == 1
        sub = deps.submissions[0]
        assert sub.agent_name == "failing-agent"
        assert sub.status == "ERROR"
        assert "Agent execution failed" in (sub.error_message or "")
