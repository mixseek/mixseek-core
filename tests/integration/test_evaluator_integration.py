"""既存Evaluatorの統合テスト

このテストは、既存のmixseek.evaluator.Evaluatorが
orchestratorコンテキストで正しく動作することを確認します。

注意: これらのテストは実際のLLM APIを使用するため、
ANTHROPIC_API_KEYが必要です。ユニットテストとしては実行されません。
"""

from pathlib import Path

import pytest

from mixseek.config.schema import EvaluatorSettings, PromptBuilderSettings
from mixseek.evaluator import EvaluationResult, Evaluator
from mixseek.models.evaluation_config import EvaluationConfig  # noqa: F401
from mixseek.models.evaluation_request import EvaluationRequest

# Pydantic循環参照を解決
EvaluationRequest.model_rebuild()


def _get_default_evaluator_settings() -> EvaluatorSettings:
    """Get EvaluatorSettings with default metrics for testing."""
    return EvaluatorSettings(
        metrics=[
            {"name": "ClarityCoherence", "weight": 0.4},
            {"name": "Coverage", "weight": 0.3},
            {"name": "Relevance", "weight": 0.3},
        ]
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_evaluator_basic_usage(tmp_path: Path) -> None:
    """既存Evaluatorの基本的な使用方法をテスト"""
    prompt_builder_settings = PromptBuilderSettings()
    evaluator = Evaluator(
        settings=_get_default_evaluator_settings(),
        prompt_builder_settings=prompt_builder_settings,
    )

    request = EvaluationRequest(
        user_query="Pythonとは何ですか？",
        submission="Pythonは高水準プログラミング言語です。",
        team_id="test-team-001",
    )

    result: EvaluationResult = await evaluator.evaluate(request)

    # EvaluationResultの検証
    assert isinstance(result, EvaluationResult)
    assert 0.0 <= result.overall_score <= 100.0
    assert len(result.metrics) >= 1

    # MetricScoreの検証
    for metric in result.metrics:
        assert 0.0 <= metric.score <= 100.0
        assert isinstance(metric.metric_name, str)
        assert isinstance(metric.evaluator_comment, str)


@pytest.mark.integration
def test_evaluator_empty_query_raises_error() -> None:
    """空のクエリでValidationErrorが発生することを確認"""
    from pydantic_core import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EvaluationRequest(
            user_query="",
            submission="テストSubmission",
        )
    # Verify error is about user_query field
    error_msg = str(exc_info.value)
    assert "user_query" in error_msg


@pytest.mark.integration
def test_evaluator_empty_submission_raises_error() -> None:
    """空のSubmissionでValidationErrorが発生することを確認"""
    from pydantic_core import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EvaluationRequest(
            user_query="テストクエリ",
            submission="",
        )
    # Verify error is about submission field
    error_msg = str(exc_info.value)
    assert "submission" in error_msg


@pytest.mark.asyncio
@pytest.mark.integration
async def test_evaluator_result_structure() -> None:
    """EvaluationResultの構造が期待通りであることを確認"""
    prompt_builder_settings = PromptBuilderSettings()
    evaluator = Evaluator(
        settings=_get_default_evaluator_settings(),
        prompt_builder_settings=prompt_builder_settings,
    )

    request = EvaluationRequest(
        user_query="Pythonの利点は何ですか？",
        submission="Pythonは読みやすく、豊富なライブラリがあり、コミュニティが活発です。",
        team_id="team-alpha-001",
    )

    result = await evaluator.evaluate(request)

    # EvaluationResult構造の検証
    assert hasattr(result, "metrics")
    assert hasattr(result, "overall_score")
    assert isinstance(result.metrics, list)
    assert isinstance(result.overall_score, float)

    # MetricScoreの構造検証
    if len(result.metrics) > 0:
        metric = result.metrics[0]
        assert hasattr(metric, "metric_name")
        assert hasattr(metric, "score")
        assert hasattr(metric, "evaluator_comment")
