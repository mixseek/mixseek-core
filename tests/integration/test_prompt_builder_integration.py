"""Integration tests for UserPromptBuilder and RoundController.

Feature: 092-user-prompt-builder-team
Test Coverage:
    - RoundController integration with UserPromptBuilder
    - Leader Board data flow (DuckDB → UserPromptBuilder → formatted prompt)
    - End-to-end prompt formatting with real components

References:
    - Spec: specs/092-user-prompt-builder-team/spec.md
    - Contract: specs/092-user-prompt-builder-team/contracts/prompt-builder-api.md
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage

from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.models.evaluation_result import EvaluationResult, MetricScore
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.prompt_builder import RoundPromptContext, UserPromptBuilder
from mixseek.round_controller.controller import RoundController
from mixseek.round_controller.models import ImprovementJudgment
from mixseek.storage.aggregation_store import AggregationStore


class TestPromptBuilderIntegration:
    """Integration tests for UserPromptBuilder with real components."""

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """Create test workspace directory."""
        workspace = tmp_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        configs_dir = workspace / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        return workspace

    @pytest.fixture
    def store(self, workspace: Path, monkeypatch: pytest.MonkeyPatch) -> AggregationStore:
        """Create test AggregationStore with DuckDB."""
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))
        return AggregationStore()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prompt_builder_with_real_store(self, workspace: Path, store: AggregationStore) -> None:
        """T016: UserPromptBuilder統合テスト（実際のDuckDBストア使用）

        Test flow:
        1. Create execution_id and save round history to DuckDB
        2. Create UserPromptBuilder with real store
        3. Call build_team_prompt() and verify Leader Board data is included
        """
        # Given: execution_id for this test run
        execution_id = str(uuid4())

        # Given: Save round 1 data to DuckDB for team1
        submissions = [
            MemberSubmission(
                agent_name="analyst",
                agent_type="code_execution",
                content="Round 1 analysis",
                status="SUCCESS",
                usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
            )
        ]
        aggregated = MemberSubmissionsRecord(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Test Team Alpha",
            round_number=1,
            submissions=submissions,
        )

        from typing import cast

        from pydantic_ai import ModelMessage
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        messages = cast(list[ModelMessage], [ModelRequest(parts=[UserPromptPart(content="Test prompt")])])
        await store.save_aggregation(execution_id, aggregated, messages)

        # Given: Save to leader board for team1 round 1
        await store.save_to_leader_board(
            execution_id=execution_id,
            team_id="team-001",
            team_name="Test Team Alpha",
            round_number=1,
            submission_content="Round 1 analysis",
            submission_format="md",
            score=85.5,
            score_details={"ClarityCoherence": 85.5},
        )

        # Given: Create UserPromptBuilder with real store
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=store)

        # Given: Create round history (simulating past rounds)
        from mixseek.round_controller.models import RoundState

        now = datetime.now(UTC)
        round_history = [
            RoundState(
                round_number=1,
                submission_content="Round 1 analysis",
                evaluation_score=85.5,
                score_details={},
                round_started_at=now,
                round_ended_at=now,
            )
        ]

        # When: Build prompt for round 2 with Leader Board integration
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=2,
            round_history=round_history,
            team_id="team-001",
            team_name="Test Team Alpha",
            execution_id=execution_id,
            store=store,
        )
        formatted_prompt = await builder.build_team_prompt(context)

        # Then: Verify prompt contains expected sections
        assert "データ分析タスク" in formatted_prompt
        assert "過去の提出履歴" in formatted_prompt
        assert "ラウンド 1" in formatted_prompt
        assert "85.50/100" in formatted_prompt
        assert "Round 1 analysis" in formatted_prompt

        # Then: Verify Leader Board ranking is included
        assert "現在のリーダーボード" in formatted_prompt or "ランキング情報がありません" in formatted_prompt

        # Then: Verify current datetime is included
        assert "現在日時:" in formatted_prompt

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("mixseek.round_controller.controller.create_leader_agent")
    @patch("mixseek.round_controller.controller.Evaluator")
    @patch("mixseek.round_controller.controller.JudgmentClient")
    async def test_round_controller_with_prompt_builder(
        self,
        mock_judgment_client_class: MagicMock,
        mock_evaluator_class: MagicMock,
        mock_create_leader: MagicMock,
        workspace: Path,
        store: AggregationStore,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """T016: RoundController統合テスト（UserPromptBuilder使用）

        Test flow:
        1. Set up RoundController with UserPromptBuilder
        2. Run multiple rounds
        3. Verify prompts are formatted correctly in each round
        """
        # Given: Set MIXSEEK_WORKSPACE
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(workspace))

        # Given: Leader Agent mock
        mock_agent = AsyncMock()
        prompts_captured: list[str] = []

        async def mock_run(prompt: str, **kwargs):  # type: ignore[no-untyped-def]
            prompts_captured.append(prompt)
            mock_result = MagicMock()
            mock_result.output = f"Submission for round {len(prompts_captured)}"
            mock_result.all_messages.return_value = []
            mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
            return mock_result

        mock_agent.run.side_effect = mock_run
        mock_create_leader.return_value = mock_agent

        # Given: Evaluator mock
        mock_evaluator = MagicMock()
        eval_count = [0]

        async def mock_evaluate(*args, **kwargs):
            eval_count[0] += 1
            return EvaluationResult(
                metrics=[
                    MetricScore(
                        metric_name="ClarityCoherence",
                        score=70.0 + eval_count[0] * 5,
                        evaluator_comment=f"Round {eval_count[0]} feedback",
                    )
                ],
                overall_score=70.0 + eval_count[0] * 5,
            )

        mock_evaluator.evaluate = AsyncMock(side_effect=mock_evaluate)
        mock_evaluator_class.return_value = mock_evaluator

        # Given: JudgmentClient mock
        judgment_count = [0]

        async def mock_judgment(*args, **kwargs):
            judgment_count[0] += 1
            return ImprovementJudgment(
                should_continue=judgment_count[0] < 2,  # Stop after 2 rounds
                reasoning="Test reasoning",
                confidence_score=0.9,
            )

        mock_client = MagicMock()
        mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
        mock_judgment_client_class.return_value = mock_client

        # Given: RoundController setup
        team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
        execution_id = str(uuid4())
        task = OrchestratorTask(
            execution_id=execution_id,
            user_prompt="データ分析タスク",
            team_configs=[team_config_path],
            timeout_seconds=300,
            max_rounds=5,
            min_rounds=1,
        )
        evaluator_settings = EvaluatorSettings()
        judgment_settings = JudgmentSettings()
        prompt_builder_settings = PromptBuilderSettings()
        controller = RoundController(
            team_config_path=team_config_path,
            workspace=workspace,
            task=task,
            evaluator_settings=evaluator_settings,
            judgment_settings=judgment_settings,
            prompt_builder_settings=prompt_builder_settings,
        )

        # When: Run first round
        result1 = await controller.run_round(
            user_prompt="データ分析タスク",
            timeout_seconds=60,
        )

        # Then: First round prompt should indicate no history
        assert len(prompts_captured) >= 1
        round1_prompt = prompts_captured[0]
        assert "データ分析タスク" in round1_prompt
        assert "過去の提出履歴" in round1_prompt
        assert "まだ過去のSubmissionはありません。" in round1_prompt
        assert "まだランキング情報がありません。" in round1_prompt  # No ranking in round 1
        assert result1.team_id == "test-team-001"  # fixture team1.toml has test-team-001

        # When: Run second round
        result2 = await controller.run_round(
            user_prompt="データ分析タスク",
            timeout_seconds=60,
        )

        # Then: Second round prompt should include history
        assert len(prompts_captured) >= 2
        # Find the first prompt with history (may not be at index 1 if controller ran multiple rounds)
        round2_prompt = next((p for p in prompts_captured[1:] if "過去の提出履歴" in p), prompts_captured[-1])
        assert "データ分析タスク" in round2_prompt
        assert "過去の提出履歴" in round2_prompt
        assert "ラウンド 1" in round2_prompt
        assert result2.team_id == "test-team-001"  # fixture team1.toml has test-team-001

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prompt_builder_round1_no_history(self, workspace: Path, store: AggregationStore) -> None:
        """T016: Round 1プロンプト（履歴なし）統合テスト"""
        # Given: UserPromptBuilder
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=store)

        # Given: Round 1 context (no history)
        context = RoundPromptContext(
            user_prompt="データ分析タスク",
            round_number=1,
            round_history=[],
            team_id="team-001",
            team_name="Test Team",
            execution_id=str(uuid4()),
            store=store,
        )

        # When: Build round 1 prompt
        formatted_prompt = await builder.build_team_prompt(context)

        # Then: Verify round 1 specific content
        assert "データ分析タスク" in formatted_prompt
        assert "まだ過去のSubmissionはありません。" in formatted_prompt
        assert "現在日時:" in formatted_prompt

        # Then: Verify history section is present but empty
        assert "過去の提出履歴" in formatted_prompt  # Header is always present

        # Then: Verify no ranking sections in round 1
        assert "まだランキング情報がありません。" in formatted_prompt

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_prompt_builder_with_multiple_teams_ranking(self, workspace: Path, store: AggregationStore) -> None:
        """T016: 複数チームランキング統合テスト"""
        # Given: execution_id
        execution_id = str(uuid4())

        # Given: Save data for 3 teams
        teams_data = [
            ("team-A", "Team Alpha", 95.0),
            ("team-B", "Team Beta", 85.0),
            ("team-C", "Team Gamma", 75.0),
        ]

        for team_id, team_name, score in teams_data:
            submissions = [
                MemberSubmission(
                    agent_name="analyst",
                    agent_type="code_execution",
                    content=f"{team_name} submission",
                    status="SUCCESS",
                    usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
                )
            ]
            aggregated = MemberSubmissionsRecord(
                execution_id=execution_id,
                team_id=team_id,
                team_name=team_name,
                round_number=1,
                submissions=submissions,
            )

            from typing import cast

            from pydantic_ai import ModelMessage
            from pydantic_ai.messages import ModelRequest, UserPromptPart

            messages = cast(
                list[ModelMessage],
                [ModelRequest(parts=[UserPromptPart(content="Test prompt")])],
            )
            await store.save_aggregation(execution_id, aggregated, messages)
            await store.save_to_leader_board(
                execution_id=execution_id,
                team_id=team_id,
                team_name=team_name,
                round_number=1,
                submission_content=f"{team_name} submission",
                submission_format="md",
                score=score,
                score_details={"Overall": score},
            )

        # Given: UserPromptBuilder with store
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=store)

        # Given: Round 2 context for Team Beta (should be ranked #2)
        from mixseek.round_controller.models import RoundState

        now = datetime.now(UTC)
        context = RoundPromptContext(
            user_prompt="テストタスク",
            round_number=2,
            round_history=[
                RoundState(
                    round_number=1,
                    submission_content="Team Beta submission",
                    evaluation_score=85.0,
                    score_details={},
                    round_started_at=now,
                    round_ended_at=now,
                )
            ],
            team_id="team-B",
            team_name="Team Beta",
            execution_id=execution_id,
            store=store,
        )

        # When: Build prompt
        formatted_prompt = await builder.build_team_prompt(context)

        # Then: Verify ranking table includes all teams
        assert "現在のリーダーボード" in formatted_prompt
        assert "Team Alpha" in formatted_prompt
        assert "Team Beta (あなたのチーム)" in formatted_prompt
        assert "Team Gamma" in formatted_prompt

        # Then: Verify ranking order (Team Beta should be #2)
        assert "95.00/100" in formatted_prompt  # Team Alpha score
        assert "85.00/100" in formatted_prompt  # Team Beta score
        assert "75.00/100" in formatted_prompt  # Team Gamma score

        # Then: Verify position message (2nd place should get "素晴らしい成績です！")
        assert "3チーム中2位です。素晴らしい成績です！" in formatted_prompt
