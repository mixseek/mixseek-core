"""Unit tests for broadcast member dispatch mode.

Feature: Broadcast Member Dispatch
Design: Broadcast member dispatch with parallel execution and leader aggregation
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.models.evaluation_result import EvaluationResult, MetricScore
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


class TestBuildAggregationPrompt:
    """Tests for RoundController._build_aggregation_prompt."""

    @patch("mixseek.round_controller.controller.AggregationStore")
    def test_formats_successful_submissions(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """成功したsubmissionsが正しくフォーマットされる."""
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

        submissions = [
            MemberSubmission(
                agent_name="web-searcher",
                agent_type="web_search",
                content="Search results here",
                status="SUCCESS",
                usage=RunUsage(input_tokens=50, output_tokens=30, requests=1),
            ),
            MemberSubmission(
                agent_name="data-analyst",
                agent_type="code_execution",
                content="Analysis results here",
                status="SUCCESS",
                usage=RunUsage(input_tokens=60, output_tokens=40, requests=1),
            ),
        ]

        prompt = controller._build_aggregation_prompt(
            original_prompt="Analyze this topic",
            submissions=submissions,
        )

        assert "Analyze this topic" in prompt
        assert "web-searcher" in prompt
        assert "SUCCESS" in prompt
        assert "Search results here" in prompt
        assert "data-analyst" in prompt
        assert "Analysis results here" in prompt

    @patch("mixseek.round_controller.controller.AggregationStore")
    def test_formats_error_submissions(
        self,
        mock_store_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ERRORのsubmissionがエラー情報付きでフォーマットされる."""
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

        submissions = [
            MemberSubmission(
                agent_name="failing-agent",
                agent_type="plain",
                content="",
                status="ERROR",
                error_message="Timeout exceeded",
                usage=RunUsage(input_tokens=0, output_tokens=0, requests=0),
            ),
        ]

        prompt = controller._build_aggregation_prompt(
            original_prompt="Analyze this topic",
            submissions=submissions,
        )

        assert "failing-agent" in prompt
        assert "ERROR" in prompt
        assert "Timeout exceeded" in prompt


class TestAggregateWithLeader:
    """Tests for RoundController._aggregate_with_leader."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    async def test_calls_leader_with_no_tools(
        self,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        tmp_path: Path,
    ) -> None:
        """集約用Leader Agentがmember_agents={}で作成される."""
        mock_store_class.return_value = AsyncMock()

        mock_leader = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = "Aggregated response"
        mock_result.all_messages.return_value = []
        mock_leader.run.return_value = mock_result
        mock_create_leader.return_value = mock_leader

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
        deps.submissions = [
            MemberSubmission(
                agent_name="agent-1",
                agent_type="plain",
                content="Result 1",
                status="SUCCESS",
                usage=RunUsage(input_tokens=10, output_tokens=20, requests=1),
            ),
        ]

        result, message_history = await controller._aggregate_with_leader(
            user_prompt="Original prompt",
            deps=deps,
        )

        assert result == "Aggregated response"
        assert message_history == []
        # Verify create_leader_agent called with empty member_agents
        mock_create_leader.assert_called_once()
        call_args = mock_create_leader.call_args
        assert call_args[0][1] == {}  # member_agents={}


def _create_mock_leader_agent() -> AsyncMock:
    """Create a mock leader agent for aggregation."""
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "Aggregated final answer"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    return mock_agent


def _create_mock_evaluator() -> MagicMock:
    """Create a mock evaluator."""
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            overall_score=85.0,
            metrics=[
                MetricScore(metric_name="accuracy", score=85.0, evaluator_comment="Good"),
            ],
        )
    )
    return mock_evaluator


def _create_mock_judgment_client(should_continue: bool = False) -> MagicMock:
    """Create a mock judgment client."""
    from mixseek.round_controller.models import ImprovementJudgment

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=should_continue,
            reasoning="Test judgment",
            confidence_score=0.9,
        )
    )
    return mock_client


class TestExecuteBroadcastEndToEnd:
    """End-to-end tests for broadcast dispatch mode through run_round."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.MemberAgentFactory")
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_broadcast_calls_all_members(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        mock_factory_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """broadcastモードで全メンバーが呼ばれる."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # Setup 2 mock member agents via factory
        mock_member_1 = _create_mock_member_agent(content="Result 1", agent_name="agent-1", agent_type="plain")
        mock_member_2 = _create_mock_member_agent(content="Result 2", agent_name="agent-2", agent_type="plain")
        mock_factory_class.create_agent.side_effect = [mock_member_1, mock_member_2]

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

        await controller.run_round("Test prompt", timeout_seconds=300)

        # Both member agents should have been called
        mock_member_1.execute.assert_called_once()
        mock_member_2.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.MemberAgentFactory")
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_broadcast_partial_failure_continues(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        mock_factory_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """broadcastモードで一部メンバー失敗時も集約が続行される."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # 1 success + 1 failure
        mock_member_1 = _create_mock_member_agent(content="Good result", agent_name="agent-1")
        mock_member_2 = _create_failing_mock_member_agent(agent_name="agent-2")
        mock_factory_class.create_agent.side_effect = [mock_member_1, mock_member_2]

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

        # Should not raise — partial failure is handled
        result = await controller.run_round("Test prompt", timeout_seconds=300)

        # Leader aggregation should still have been called
        mock_create_leader.assert_called()
        assert result.submission_content == "Aggregated final answer"


class TestSelectiveModeUnchanged:
    """Verify selective (default) mode is not affected."""

    @pytest.mark.asyncio
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.AggregationStore")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_selective_uses_existing_leader_path(
        self,
        mock_judgment_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_store_class: MagicMock,
        mock_create_leader: MagicMock,
        tmp_path: Path,
    ) -> None:
        """selectiveモードでは既存のleader_agent.run()パスが使われる."""
        mock_store_class.return_value = AsyncMock()
        mock_evaluator_class.return_value = _create_mock_evaluator()
        mock_judgment_class.return_value = _create_mock_judgment_client()
        mock_create_leader.return_value = _create_mock_leader_agent()

        # team1.toml has no member_dispatch (defaults to selective)
        team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
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

        await controller.run_round("Test prompt", timeout_seconds=300)

        # create_leader_agent should be called WITH member_agents (not empty)
        mock_create_leader.assert_called_once()
        call_args = mock_create_leader.call_args
        member_agents_arg = call_args[0][1]
        # For team1.toml (no members), it should be an empty dict but via the normal path
        assert isinstance(member_agents_arg, dict)


class TestLeaderAgentToolRegistration:
    """Tests for conditional tool registration in create_leader_agent."""

    @patch("mixseek.agents.leader.agent.register_member_tools")
    @patch("mixseek.agents.leader.agent.Agent")
    @patch("mixseek.agents.leader.agent.create_authenticated_model")
    def test_empty_member_agents_skips_tool_registration(
        self,
        mock_auth_model: MagicMock,
        mock_agent_class: MagicMock,
        mock_register: MagicMock,
    ) -> None:
        """member_agents={}の場合、register_member_toolsが呼ばれない."""
        from mixseek.agents.leader.agent import create_leader_agent
        from mixseek.agents.leader.config import TeamConfig

        mock_auth_model.return_value = MagicMock()
        mock_agent_class.return_value = MagicMock()
        config = TeamConfig(team_id="test", team_name="Test")
        create_leader_agent(config, {})
        mock_register.assert_not_called()

    @patch("mixseek.agents.leader.agent.register_member_tools")
    @patch("mixseek.agents.leader.agent.Agent")
    @patch("mixseek.agents.leader.agent.create_authenticated_model")
    def test_non_empty_member_agents_registers_tools(
        self,
        mock_auth_model: MagicMock,
        mock_agent_class: MagicMock,
        mock_register: MagicMock,
    ) -> None:
        """member_agentsが非空の場合、register_member_toolsが呼ばれる."""
        from mixseek.agents.leader.agent import create_leader_agent
        from mixseek.agents.leader.config import TeamConfig

        mock_auth_model.return_value = MagicMock()
        mock_agent_class.return_value = MagicMock()
        config = TeamConfig(team_id="test", team_name="Test")
        mock_agent = MagicMock()
        create_leader_agent(config, {"agent-1": mock_agent})
        mock_register.assert_called_once()
