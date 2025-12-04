"""Unit tests for RoundController.run_round()"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_ai import RunUsage

from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController


@pytest.mark.asyncio
async def test_round_controller_run_round(tmp_path: Path) -> None:
    """RoundController.run_round()テスト（既存Evaluatorを使用）"""
    # 絶対パスを使用
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    task = OrchestratorTask(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
        min_rounds=1,
    )

    # モックでLeader AgentとEvaluatorを差し替え
    with (
        patch("mixseek.round_controller.controller.create_leader_agent") as mock_leader,
        patch("mixseek.round_controller.controller.Evaluator") as mock_eval_class,
        patch("mixseek.round_controller.controller.AggregationStore") as mock_store,
        patch("mixseek.round_controller.controller.JudgmentClient") as mock_judgment_client_class,
    ):
        # モック設定
        mock_leader_result = Mock()
        mock_leader_result.output = "テストSubmission"
        mock_leader_result.all_messages = Mock(return_value=[])
        mock_leader_result.usage = Mock(return_value=RunUsage(input_tokens=100, output_tokens=200, requests=1))

        mock_leader.return_value.run = AsyncMock(return_value=mock_leader_result)

        # Evaluatorのモック（既存Evaluator - 0-100スケール）
        mock_evaluator = MagicMock()
        mock_evaluation_result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="ClarityCoherence", score=85.0, evaluator_comment="明瞭です"),
                MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="関連性が高い"),
            ],
            overall_score=87.5,  # 0-100スケール
        )
        mock_evaluator.evaluate = AsyncMock(return_value=mock_evaluation_result)
        mock_eval_class.return_value = mock_evaluator

        # Mock store
        mock_store_instance = AsyncMock()
        mock_store_instance.get_ranking_by_execution.return_value = []
        mock_store.return_value = mock_store_instance

        # Mock judgment - terminate immediately
        from mixseek.round_controller.models import ImprovementJudgment

        mock_client = MagicMock()
        mock_client.judge_improvement_prospects = AsyncMock(
            return_value=ImprovementJudgment(should_continue=False, reasoning="Test termination", confidence_score=0.9)
        )
        mock_judgment_client_class.return_value = mock_client

        # RoundController生成（patchブロック内で生成してモックを適用）
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )

        # 実行
        result = await controller.run_round(
            user_prompt="テストプロンプト",
            timeout_seconds=600,
        )

        # 検証（LeaderBoardEntry with 0-100 scale）
        assert isinstance(result, LeaderBoardEntry)
        assert result.team_id == controller.get_team_id()
        assert result.submission_content == "テストSubmission"
        assert result.score == 87.5  # 0-100スケールのまま
        assert result.final_submission is True
