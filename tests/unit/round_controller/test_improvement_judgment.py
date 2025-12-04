"""Unit tests for Improvement Judgment Client

Feature: 012-round-controller (User Story 2), 021-user-prompt-builder-evaluator-judgement
Tests LLM-based improvement judgment logic with formatted prompts from RoundController.

Note:
    These tests focus on JudgmentClient's core responsibility: Agent invocation.
    Prompt formatting is tested via RoundController integration tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mixseek.config.schema import JudgmentSettings
from mixseek.round_controller.judgment_client import JudgmentClient
from mixseek.round_controller.models import ImprovementJudgment


@pytest.mark.asyncio
@patch("mixseek.round_controller.judgment_client.Agent")
async def test_judge_improvement_prospects_should_continue(mock_agent_class: MagicMock) -> None:
    """T047: LLMによる改善見込み判定 - 継続すべき場合"""

    # Mock Pydantic AI Agent
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = ImprovementJudgment(
        should_continue=True,
        reasoning="スコアは向上傾向にあり、さらなる改善が期待できます。",
        confidence_score=0.85,
    )
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_agent_class.return_value = mock_agent

    # Sample formatted prompt (from RoundController)
    formatted_prompt = """# タスク
以下のラウンド履歴に基づいて、チームは次のラウンドに進むべきでしょうか？

# ユーザクエリ
テストプロンプト

# ラウンド履歴
## ラウンド 1
**提出内容:** 初回Submission
**スコア:** 70.00/100

## ラウンド 2
**提出内容:** 2回目Submission
**スコア:** 75.00/100
"""

    # Execute judgment with formatted prompt
    client = JudgmentClient(settings=JudgmentSettings())
    result = await client.judge_improvement_prospects(formatted_prompt=formatted_prompt)

    # Verify result
    assert isinstance(result, ImprovementJudgment)
    assert result.should_continue is True
    assert result.confidence_score == 0.85
    assert "改善" in result.reasoning

    # Verify Agent was called with formatted prompt
    mock_agent.run.assert_called_once_with(formatted_prompt)


@pytest.mark.asyncio
@patch("mixseek.round_controller.judgment_client.Agent")
async def test_judge_improvement_prospects_should_not_continue(mock_agent_class: MagicMock) -> None:
    """T047: LLMによる改善見込み判定 - 終了すべき場合"""

    # Mock Pydantic AI Agent
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = ImprovementJudgment(
        should_continue=False,
        reasoning="スコアが横ばいで、改善見込みは低いと判断します。",
        confidence_score=0.90,
    )
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_agent_class.return_value = mock_agent

    # Sample formatted prompt with plateauing scores
    formatted_prompt = """# タスク
以下のラウンド履歴に基づいて、チームは次のラウンドに進むべきでしょうか？

# ユーザクエリ
テストプロンプト

# ラウンド履歴
## ラウンド 1
**提出内容:** 初回Submission
**スコア:** 80.00/100

## ラウンド 2
**提出内容:** 2回目Submission
**スコア:** 81.00/100

## ラウンド 3
**提出内容:** 3回目Submission
**スコア:** 80.50/100
"""

    # Execute judgment
    client = JudgmentClient(settings=JudgmentSettings())
    result = await client.judge_improvement_prospects(formatted_prompt=formatted_prompt)

    # Verify result
    assert isinstance(result, ImprovementJudgment)
    assert result.should_continue is False
    assert result.confidence_score == 0.90


@pytest.mark.asyncio
@patch("mixseek.round_controller.judgment_client.Agent")
async def test_judge_improvement_prospects_retry_on_failure(mock_agent_class: MagicMock) -> None:
    """T047: 判定失敗時のリトライポリシー（3回リトライ）

    Note: Agent handles retries internally, so we can only verify that
    the Agent is configured with the correct retry count. The actual
    retry behavior is tested in integration tests with real Agent.
    """

    # Mock Agent - simulate successful retry (Agent handles retries internally)
    mock_agent = MagicMock()
    mock_success_result = MagicMock()
    mock_success_result.output = ImprovementJudgment(
        should_continue=True,
        reasoning="リトライ後成功",
        confidence_score=0.8,
    )
    mock_agent.run = AsyncMock(return_value=mock_success_result)
    mock_agent_class.return_value = mock_agent

    # Sample formatted prompt
    formatted_prompt = """# タスク
以下のラウンド履歴に基づいて、チームは次のラウンドに進むべきでしょうか？

# ユーザクエリ
テストプロンプト

# ラウンド履歴
## ラウンド 1
**提出内容:** Submission
**スコア:** 70.00/100
"""

    # Execute judgment (Agent handles retries internally)
    client = JudgmentClient(settings=JudgmentSettings())
    result = await client.judge_improvement_prospects(formatted_prompt=formatted_prompt)

    # Verify result
    assert isinstance(result, ImprovementJudgment)
    assert result.should_continue is True
    assert result.reasoning == "リトライ後成功"

    # Verify Agent was created with correct retry count
    assert mock_agent_class.call_count == 1
    call_kwargs = mock_agent_class.call_args.kwargs
    assert call_kwargs["retries"] == 3


@pytest.mark.asyncio
@patch("mixseek.round_controller.judgment_client.Agent")
async def test_judge_improvement_prospects_all_retries_failed_raises_exception(mock_agent_class: MagicMock) -> None:
    """T047: 全リトライ失敗時は例外を投げる（フォールバックはcontroller側で処理）"""

    # Mock Agent - always fail
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=Exception("Persistent failure"))
    mock_agent_class.return_value = mock_agent

    # Sample formatted prompt
    formatted_prompt = """# タスク
以下のラウンド履歴に基づいて、チームは次のラウンドに進むべきでしょうか？

# ユーザクエリ
テストプロンプト

# ラウンド履歴
## ラウンド 1
**提出内容:** Submission
**スコア:** 70.00/100
"""

    # Execute judgment (should raise exception after all retries fail)
    client = JudgmentClient(settings=JudgmentSettings())
    with pytest.raises(Exception, match="Failed to judge improvement prospects after 3 retries"):
        await client.judge_improvement_prospects(formatted_prompt=formatted_prompt)

    # Note: Agent handles retries internally, so mock_agent_class is called once
    # The actual retry logic is tested in integration tests with real Agent behavior
    assert mock_agent_class.call_count == 1
