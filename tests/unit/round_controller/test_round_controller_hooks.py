"""Unit tests for RoundController on_round_complete hook

Feature: Issue #225 - RoundControllerにラウンド完了時のフック機構を追加
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.models import MemberSubmission
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController, RoundState


def _create_mock_leader_agent() -> AsyncMock:
    """Create a mock leader agent with standard responses."""
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "Test Submission Content"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    return mock_agent


def _create_mock_evaluator() -> MagicMock:
    """Create a mock evaluator with standard responses."""
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            overall_score=85.0,
            metrics=[
                MetricScore(
                    metric_name="accuracy",
                    score=85.0,
                    evaluator_comment="Good accuracy",
                )
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


def _create_mock_store() -> AsyncMock:
    """Create a mock aggregation store with async methods.

    Uses AsyncMock to automatically handle await expressions for all methods.
    """
    return AsyncMock()


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_on_round_complete_called_after_each_round(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that on_round_complete hook is called after each round."""
    # Setup mocks
    mock_create_leader.return_value = _create_mock_leader_agent()
    mock_evaluator_class.return_value = _create_mock_evaluator()
    mock_judgment_client_class.return_value = _create_mock_judgment_client(should_continue=False)
    mock_store_class.return_value = _create_mock_store()

    # Create hook mock
    hook_mock = AsyncMock()

    # Create controller with hook
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
        on_round_complete=hook_mock,
    )

    # Execute
    await controller.run_round("Test prompt", timeout_seconds=300)

    # Verify hook was called
    assert hook_mock.call_count == 1


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_on_round_complete_receives_correct_args(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that on_round_complete receives RoundState and list[MemberSubmission]."""
    # Setup mocks
    mock_create_leader.return_value = _create_mock_leader_agent()
    mock_evaluator_class.return_value = _create_mock_evaluator()
    mock_judgment_client_class.return_value = _create_mock_judgment_client(should_continue=False)
    mock_store_class.return_value = _create_mock_store()

    # Create hook mock that captures arguments
    captured_args: list[tuple[Any, Any]] = []

    async def capture_hook(round_state: RoundState, member_submissions: list[MemberSubmission]) -> None:
        captured_args.append((round_state, member_submissions))

    # Create controller with hook
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
        on_round_complete=capture_hook,
    )

    # Execute
    await controller.run_round("Test prompt", timeout_seconds=300)

    # Verify arguments
    assert len(captured_args) == 1
    round_state, member_submissions = captured_args[0]

    # Check RoundState
    assert isinstance(round_state, RoundState)
    assert round_state.round_number == 1
    assert round_state.submission_content == "Test Submission Content"
    assert round_state.evaluation_score == 85.0

    # Check member_submissions is a list
    assert isinstance(member_submissions, list)


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_on_round_complete_exception_does_not_stop_execution(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that hook exception doesn't stop round execution."""
    # Setup mocks
    mock_create_leader.return_value = _create_mock_leader_agent()
    mock_evaluator_class.return_value = _create_mock_evaluator()
    mock_judgment_client_class.return_value = _create_mock_judgment_client(should_continue=False)
    mock_store_class.return_value = _create_mock_store()

    # Create hook that raises exception
    async def failing_hook(round_state: RoundState, member_submissions: list[MemberSubmission]) -> None:
        raise ValueError("Hook error for testing")

    # Create controller with failing hook
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
        on_round_complete=failing_hook,
    )

    # Execute - should not raise exception
    result = await controller.run_round("Test prompt", timeout_seconds=300)

    # Verify execution completed successfully despite hook failure
    assert result is not None
    assert result.score == 85.0

    # Verify warning was logged
    assert "on_round_complete hook failed" in caplog.text
    assert "Hook error for testing" in caplog.text


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_on_round_complete_none_does_not_cause_error(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that on_round_complete=None (default) doesn't cause error."""
    # Setup mocks
    mock_create_leader.return_value = _create_mock_leader_agent()
    mock_evaluator_class.return_value = _create_mock_evaluator()
    mock_judgment_client_class.return_value = _create_mock_judgment_client(should_continue=False)
    mock_store_class.return_value = _create_mock_store()

    # Create controller WITHOUT hook (default)
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
        # on_round_complete not specified - should default to None
    )

    # Execute - should not raise exception
    result = await controller.run_round("Test prompt", timeout_seconds=300)

    # Verify execution completed successfully
    assert result is not None
    assert result.score == 85.0


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_on_round_complete_receives_latest_member_submissions(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that member_submissions contain the latest round results."""

    # Setup mocks
    mock_agent = _create_mock_leader_agent()
    mock_create_leader.return_value = mock_agent
    mock_evaluator_class.return_value = _create_mock_evaluator()
    mock_judgment_client_class.return_value = _create_mock_judgment_client(should_continue=False)
    mock_store_class.return_value = _create_mock_store()

    # Create hook mock that captures member_submissions
    captured_member_submissions: list[list[MemberSubmission]] = []

    async def capture_hook(round_state: RoundState, member_submissions: list[MemberSubmission]) -> None:
        captured_member_submissions.append(member_submissions)

    # Create controller with hook
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
        on_round_complete=capture_hook,
    )

    # Execute
    await controller.run_round("Test prompt", timeout_seconds=300)

    # Verify member_submissions were captured
    assert len(captured_member_submissions) == 1
    # member_submissions list should exist (may be empty if no member agents in test fixture)
    assert isinstance(captured_member_submissions[0], list)
