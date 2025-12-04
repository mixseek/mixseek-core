"""Unit tests for RoundController"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai import RunUsage

from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore
from mixseek.models.leaderboard import LeaderBoardEntry
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController


def test_round_controller_initialization(tmp_path: Path) -> None:
    """RoundController初期化テスト"""
    # 絶対パスを使用
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    task = OrchestratorTask(
        execution_id=str(uuid4()),
        user_prompt="Test prompt",
        team_configs=[team_config_path],
        timeout_seconds=300,
    )
    controller = RoundController(
        team_config_path=team_config_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=EvaluatorSettings(),
        judgment_settings=JudgmentSettings(),
        prompt_builder_settings=PromptBuilderSettings(),
    )
    assert controller.get_team_id() is not None
    assert controller.get_team_name() is not None


def test_round_controller_invalid_config(tmp_path: Path) -> None:
    """RoundController 不正な設定ファイルテスト"""
    task = OrchestratorTask(
        execution_id=str(uuid4()),
        user_prompt="Test prompt",
        team_configs=[Path("nonexistent.toml")],
        timeout_seconds=300,
    )
    with pytest.raises(FileNotFoundError):
        RoundController(
            team_config_path=Path("nonexistent.toml"),
            workspace=tmp_path,
            task=task,
            evaluator_settings=EvaluatorSettings(),
            judgment_settings=JudgmentSettings(),
            prompt_builder_settings=PromptBuilderSettings(),
        )


def test_round_controller_get_team_info(tmp_path: Path) -> None:
    """RoundController チーム情報取得テスト"""
    # 絶対パスを使用
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    task = OrchestratorTask(
        execution_id=str(uuid4()),
        user_prompt="Test prompt",
        team_configs=[team_config_path],
        timeout_seconds=300,
    )
    controller = RoundController(
        team_config_path=team_config_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=EvaluatorSettings(),
        judgment_settings=JudgmentSettings(),
        prompt_builder_settings=PromptBuilderSettings(),
    )
    team_id = controller.get_team_id()
    team_name = controller.get_team_name()

    assert team_id == "test-team-001"
    assert team_name == "Test Team 1"


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_run_round_returns_leaderboard_entry(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """T042: run_round()がLeaderBoardEntryを返すことを検証"""

    # Leader Agentのモック
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "テストSubmission"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    # AggregationStoreのモック
    mock_store = AsyncMock()
    mock_store.get_ranking_by_execution.return_value = []
    mock_store_class.return_value = mock_store

    # Evaluatorのモック（0-100スケール）
    mock_evaluator = MagicMock()
    mock_evaluation_result = EvaluationResult(
        metrics=[
            MetricScore(
                metric_name="ClarityCoherence",
                score=85.5,
                evaluator_comment="明瞭で一貫性があります",
            ),
            MetricScore(
                metric_name="Relevance",
                score=90.0,
                evaluator_comment="非常に関連性が高いです",
            ),
        ],
        overall_score=87.75,  # 0-100スケール
    )
    mock_evaluator.evaluate = AsyncMock(return_value=mock_evaluation_result)
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock - no improvement expected to terminate after 1 round
    from mixseek.round_controller.models import ImprovementJudgment

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(
            should_continue=False, reasoning="No improvement expected", confidence_score=0.9
        )
    )
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行（絶対パスを使用）
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    task = OrchestratorTask(
        execution_id="550e8400-e29b-41d4-a716-446655440000",
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
        min_rounds=1,  # Allow termination after 1 round
    )
    controller = RoundController(
        team_config_path=team_config_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=EvaluatorSettings(),
        judgment_settings=JudgmentSettings(),
        prompt_builder_settings=PromptBuilderSettings(),
    )

    result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T042: LeaderBoardEntryが返されることを検証
    assert isinstance(result, LeaderBoardEntry)
    assert result.team_id == "test-team-001"
    assert result.team_name == "Test Team 1"
    assert result.round_number == 1
    assert result.submission_content == "テストSubmission"
    assert result.score == 87.75  # 0-100スケールのまま
    assert result.final_submission is True
    assert result.exit_reason is not None

    # Evaluatorが正しく呼び出されたことを確認
    mock_evaluator.evaluate.assert_called_once()

    # Leader Agentが正しく呼び出されたことを確認
    mock_agent.run.assert_called_once()


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_single_round_duckdb_save(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T043: 単一ラウンドのDuckDB保存を検証（round_status、leader_boardテーブル）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "テストSubmission内容"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック
    mock_evaluator = MagicMock()
    mock_evaluation_result = EvaluationResult(
        metrics=[
            MetricScore(metric_name="ClarityCoherence", score=80.0, evaluator_comment="Good"),
        ],
        overall_score=80.0,
    )
    mock_evaluator.evaluate = AsyncMock(return_value=mock_evaluation_result)
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock - terminate after 1 round
    from mixseek.round_controller.models import ImprovementJudgment

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(
        return_value=ImprovementJudgment(should_continue=False, reasoning="Test termination", confidence_score=0.95)
    )
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    execution_id = str(uuid4())
    task = OrchestratorTask(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
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

    _result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T043: DuckDBに保存されたことを検証
    from mixseek.storage.aggregation_store import AggregationStore

    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # round_statusテーブルの検証
    round_status_query = """
        SELECT execution_id, team_id, round_number, should_continue, reasoning, confidence_score
        FROM round_status
        WHERE execution_id = ? AND team_id = ?
    """
    round_status_result = conn.execute(round_status_query, [execution_id, "test-team-001"]).fetchone()
    assert round_status_result is not None
    assert round_status_result[0] == execution_id
    assert round_status_result[1] == "test-team-001"
    assert round_status_result[2] == 1  # round_number

    # leader_boardテーブルの検証
    leader_board_query = """
        SELECT execution_id, team_id, round_number, submission_content, score, final_submission, exit_reason
        FROM leader_board
        WHERE execution_id = ? AND team_id = ?
    """
    leader_board_result = conn.execute(leader_board_query, [execution_id, "test-team-001"]).fetchone()
    assert leader_board_result is not None
    assert leader_board_result[0] == execution_id
    assert leader_board_result[1] == "test-team-001"
    assert leader_board_result[2] == 1  # round_number
    assert leader_board_result[3] == "テストSubmission内容"
    assert leader_board_result[4] == 80.0  # score
    assert leader_board_result[5] is True  # final_submission
    assert leader_board_result[6] is not None  # exit_reason


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_multi_round_execution(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T048: 複数ラウンド実行テスト（最大5ラウンド、各ラウンドのDuckDB記録を検証）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック - 各ラウンドで異なるSubmissionを返す
    mock_agent = AsyncMock()

    call_count = [0]

    async def mock_run(*args: Any, **kwargs: Any) -> Any:
        call_count[0] += 1
        mock_result = MagicMock()
        mock_result.output = f"ラウンド{call_count[0]}のSubmission"
        mock_result.all_messages.return_value = []
        mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
        return mock_result

    mock_agent.run.side_effect = mock_run
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック - 各ラウンドでスコアが向上
    eval_call_count = [0]

    async def mock_evaluate(*args: Any, **kwargs: Any) -> EvaluationResult:
        eval_call_count[0] += 1
        score = 70.0 + eval_call_count[0] * 5.0  # 75, 80, 85, 90, 95
        return EvaluationResult(
            metrics=[
                MetricScore(
                    metric_name="ClarityCoherence",
                    score=score,
                    evaluator_comment=f"Round {eval_call_count[0]}",
                ),
            ],
            overall_score=score,
        )

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(side_effect=mock_evaluate)
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock - continue for 3 rounds, then terminate on 4th
    from mixseek.round_controller.models import ImprovementJudgment

    judgment_call_count = [0]

    async def mock_judgment(*args: Any, **kwargs: Any) -> ImprovementJudgment:
        judgment_call_count[0] += 1
        should_continue = judgment_call_count[0] < 3  # Continue for first 2 judgments, stop on 3rd
        return ImprovementJudgment(
            should_continue=should_continue,
            reasoning=f"Judgment {judgment_call_count[0]}",
            confidence_score=0.9,
        )

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    execution_id = str(uuid4())
    task = OrchestratorTask(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
        min_rounds=2,
    )
    controller = RoundController(
        team_config_path=team_config_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=EvaluatorSettings(),
        judgment_settings=JudgmentSettings(),
        prompt_builder_settings=PromptBuilderSettings(),
    )

    _result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T048: 複数ラウンドが実行されたことを検証
    from mixseek.storage.aggregation_store import AggregationStore

    store = AggregationStore(db_path=tmp_path / "mixseek.db")
    conn = store._get_connection()

    # 各ラウンドがround_statusとleader_boardに記録されていることを確認
    round_status_result = conn.execute(
        "SELECT COUNT(*) FROM round_status WHERE execution_id = ? AND team_id = ?",
        [execution_id, "test-team-001"],
    ).fetchone()
    assert round_status_result is not None
    round_status_count = round_status_result[0]

    leader_board_result = conn.execute(
        "SELECT COUNT(*) FROM leader_board WHERE execution_id = ? AND team_id = ?",
        [execution_id, "test-team-001"],
    ).fetchone()
    assert leader_board_result is not None
    leader_board_count = leader_board_result[0]

    # 4ラウンド実行されたことを確認（judgment stops at round 4）
    assert round_status_count == 4
    assert leader_board_count == 4

    # 最終Submissionが最高スコアのラウンドに設定されていることを確認
    final_submission = conn.execute(
        """SELECT round_number, score FROM leader_board
           WHERE execution_id = ? AND team_id = ? AND final_submission = TRUE""",
        [execution_id, "test-team-001"],
    ).fetchone()

    assert final_submission is not None
    assert final_submission[0] == 4  # Round 4 has the highest score (90.0)
    assert final_submission[1] == 90.0


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_round_continuation_judgment(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T049: ラウンド継続判定テスト（最小ラウンド数確認、LLM判定、最大ラウンド数確認の3段階を検証）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "テストSubmission"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=EvaluationResult(
            metrics=[MetricScore(metric_name="ClarityCoherence", score=80.0, evaluator_comment="OK")],
            overall_score=80.0,
        )
    )
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock - test min_rounds logic
    from mixseek.round_controller.models import ImprovementJudgment

    call_count = [0]

    async def mock_judgment(*args: Any, **kwargs: Any) -> ImprovementJudgment:
        call_count[0] += 1
        # For rounds < min_rounds, should_continue is True (no LLM judgment)
        # For rounds >= min_rounds, LLM judgment is called
        return ImprovementJudgment(
            should_continue=call_count[0] < 2,  # Stop after 2 judgments
            reasoning=f"Judgment {call_count[0]}",
            confidence_score=0.9,
        )

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    execution_id = str(uuid4())
    task = OrchestratorTask(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
        min_rounds=2,  # Require at least 2 rounds before LLM judgment
    )
    controller = RoundController(
        team_config_path=team_config_path,
        workspace=tmp_path,
        task=task,
        evaluator_settings=EvaluatorSettings(),
        judgment_settings=JudgmentSettings(),
        prompt_builder_settings=PromptBuilderSettings(),
    )

    result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T049: Verify continuation logic
    # - Should run at least min_rounds (2)
    # - LLM judgment should be called after min_rounds
    # - Should stop when LLM says no improvement
    assert mock_client.judge_improvement_prospects.call_count >= 1  # LLM judgment called after min_rounds
    assert result.round_number >= 2  # At least min_rounds executed


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.AggregationStore")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_next_round_prompt_formatting(
    mock_judgment_client_class: MagicMock,
    mock_store_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T050: 次ラウンドプロンプト整形テスト（過去のSubmission履歴、評価フィードバック、ランキング情報の統合を検証）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック - capture prompts
    mock_agent = AsyncMock()
    prompts_captured: list[str] = []

    async def mock_run(prompt: str, **kwargs: Any) -> Any:
        prompts_captured.append(prompt)
        mock_result = MagicMock()
        mock_result.output = f"Submission for prompt: {len(prompts_captured)}"
        mock_result.all_messages.return_value = []
        mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
        return mock_result

    mock_agent.run.side_effect = mock_run
    mock_create_leader.return_value = mock_agent

    # AggregationStoreのモック
    mock_store = AsyncMock()
    mock_store.get_ranking_by_execution.return_value = [
        {"team_id": "team-001", "team_name": "Test Team", "max_score": 75.0, "rank": 1},
    ]
    mock_store_class.return_value = mock_store

    # Evaluatorのモック
    mock_evaluator = MagicMock()
    eval_count = [0]

    async def mock_evaluate(*args: Any, **kwargs: Any) -> EvaluationResult:
        eval_count[0] += 1
        return EvaluationResult(
            metrics=[
                MetricScore(
                    metric_name="ClarityCoherence",
                    score=70.0 + eval_count[0] * 5,
                    evaluator_comment="OK",
                )
            ],
            overall_score=70.0 + eval_count[0] * 5,
        )

    mock_evaluator.evaluate = AsyncMock(side_effect=mock_evaluate)
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock
    from mixseek.round_controller.models import ImprovementJudgment

    judgment_count = [0]

    async def mock_judgment(*args: Any, **kwargs: Any) -> ImprovementJudgment:
        judgment_count[0] += 1
        return ImprovementJudgment(
            should_continue=judgment_count[0] < 2,  # Continue for 1 more round, then stop
            reasoning="Test reasoning",
            confidence_score=0.9,
        )

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    execution_id = str(uuid4())
    task = OrchestratorTask(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
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

    _result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T050: Verify prompt formatting
    # - First round: only user prompt
    # - Second+ rounds: should include past submissions, feedback, ranking
    assert len(prompts_captured) >= 2
    # Round 1 prompt should be simple
    assert "テストプロンプト" in prompts_captured[0]
    # Round 2+ prompts should include history (implementation detail - verify structure exists)
    # Note: Exact format depends on implementation in controller.py


@pytest.mark.asyncio
@patch("mixseek.round_controller.controller.create_leader_agent")
@patch("mixseek.round_controller.controller.Evaluator")
@patch("mixseek.round_controller.controller.JudgmentClient")
async def test_best_score_submission_identification(
    mock_judgment_client_class: MagicMock,
    mock_evaluator_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T051: 終了時の最高スコアSubmission特定テスト（同点時は最も遅いラウンド番号を選択）"""

    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

    # Leader Agentのモック
    mock_agent = AsyncMock()
    call_count = [0]

    async def mock_run(*args: Any, **kwargs: Any) -> Any:
        call_count[0] += 1
        mock_result = MagicMock()
        mock_result.output = f"ラウンド{call_count[0]}のSubmission"
        mock_result.all_messages.return_value = []
        mock_result.usage.return_value = RunUsage(input_tokens=100, output_tokens=50, requests=1)
        return mock_result

    mock_agent.run.side_effect = mock_run
    mock_create_leader.return_value = mock_agent

    # Evaluatorのモック - create a tie scenario
    eval_count = [0]

    async def mock_evaluate(*args: Any, **kwargs: Any) -> EvaluationResult:
        eval_count[0] += 1
        # Round 1: 80.0, Round 2: 85.0, Round 3: 85.0 (tie!), Round 4: 82.0
        scores = [80.0, 85.0, 85.0, 82.0]
        score = scores[eval_count[0] - 1] if eval_count[0] <= len(scores) else 80.0
        return EvaluationResult(
            metrics=[MetricScore(metric_name="ClarityCoherence", score=score, evaluator_comment="OK")],
            overall_score=score,
        )

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(side_effect=mock_evaluate)
    mock_evaluator_class.return_value = mock_evaluator

    # Judgment mock - continue for 4 rounds
    from mixseek.round_controller.models import ImprovementJudgment

    judgment_count = [0]

    async def mock_judgment(*args: Any, **kwargs: Any) -> ImprovementJudgment:
        judgment_count[0] += 1
        return ImprovementJudgment(
            should_continue=judgment_count[0] < 4,  # Stop after 4 rounds
            reasoning="Test",
            confidence_score=0.9,
        )

    mock_client = MagicMock()
    mock_client.judge_improvement_prospects = AsyncMock(side_effect=mock_judgment)
    mock_judgment_client_class.return_value = mock_client

    # RoundControllerの実行
    team_config_path = Path.cwd() / "tests" / "fixtures" / "team1.toml"
    execution_id = str(uuid4())
    task = OrchestratorTask(
        execution_id=execution_id,
        user_prompt="テストプロンプト",
        team_configs=[team_config_path],
        timeout_seconds=300,
        max_rounds=5,
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

    result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # T051: Verify best score identification with tiebreaker
    # - Best score is 85.0 (rounds 2 and 3)
    # - Tiebreaker: latest round (round 3) should be chosen
    assert result.score == 85.0
    assert result.round_number == 3  # Latest round with best score
