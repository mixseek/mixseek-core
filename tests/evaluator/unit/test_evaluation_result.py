"""Unit tests for MetricScore and EvaluationResult models."""

import pytest
from pydantic import ValidationError

from mixseek.models.evaluation_result import EvaluationResult, MetricScore


class TestMetricScoreValidation:
    """Test MetricScore validation rules."""

    def test_valid_metric_score(self) -> None:
        """Test creating a valid MetricScore."""
        metric = MetricScore(
            metric_name="clarity_coherence",
            score=85.5,
            evaluator_comment="Well-structured response.",
        )

        assert metric.metric_name == "clarity_coherence"
        assert metric.score == 85.5
        assert metric.evaluator_comment == "Well-structured response."

    def test_score_accepts_any_real_value(self) -> None:
        """Test that score accepts any real value (no constraints)."""
        # Test typical LLMJudgeMetric range (0-100)
        metric_zero = MetricScore(metric_name="test_metric", score=0.0, evaluator_comment="Zero score")
        assert metric_zero.score == 0.0

        metric_hundred = MetricScore(metric_name="test_metric", score=100.0, evaluator_comment="Max score")
        assert metric_hundred.score == 100.0

        metric_mid = MetricScore(metric_name="test_metric", score=50.5, evaluator_comment="Mid-range score")
        assert metric_mid.score == 50.5

        # Test negative values (custom metrics)
        metric_negative = MetricScore(
            metric_name="performance_delta",
            score=-15.5,
            evaluator_comment="Performance degraded by 15.5%",
        )
        assert metric_negative.score == -15.5

        # Test values above 100 (custom metrics)
        metric_above = MetricScore(
            metric_name="improvement_ratio",
            score=250.0,
            evaluator_comment="Performance improved by 250%",
        )
        assert metric_above.score == 250.0

        # Test large negative value
        metric_large_negative = MetricScore(
            metric_name="loss_metric",
            score=-1000.0,
            evaluator_comment="Large loss",
        )
        assert metric_large_negative.score == -1000.0

    def test_empty_metric_name_raises_error(self) -> None:
        """Test that empty metric_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricScore(metric_name="", score=80.0, evaluator_comment="Test comment")

        error = exc_info.value
        assert "metric_name" in str(error).lower()

    def test_whitespace_only_metric_name_raises_error(self) -> None:
        """Test that whitespace-only metric_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricScore(metric_name="   \n\t  ", score=80.0, evaluator_comment="Test comment")

        error = exc_info.value
        assert "metric_name" in str(error).lower()

    def test_empty_comment_allowed(self) -> None:
        """Test that empty evaluator_comment is allowed."""
        metric = MetricScore(metric_name="test_metric", score=80.0, evaluator_comment="")

        assert metric.evaluator_comment == ""

    def test_comment_whitespace_normalization(self) -> None:
        """Test that evaluator_comment whitespace is normalized."""
        metric = MetricScore(
            metric_name="test_metric",
            score=80.0,
            evaluator_comment="  Leading and trailing spaces  ",
        )

        # Check if whitespace is stripped
        assert metric.evaluator_comment.strip() == "Leading and trailing spaces"

    def test_score_rounding_to_two_decimals(self) -> None:
        """Test that score is rounded to 2 decimal places."""
        metric = MetricScore(
            metric_name="test_metric",
            score=85.12345,
            evaluator_comment="Test rounding",
        )

        assert metric.score == 85.12

    def test_metric_name_normalization(self) -> None:
        """Test that metric_name whitespace is normalized."""
        metric = MetricScore(
            metric_name="  clarity_coherence  ",
            score=80.0,
            evaluator_comment="Test",
        )

        assert metric.metric_name == "clarity_coherence"


class TestEvaluationResultValidation:
    """Test EvaluationResult validation rules."""

    def test_valid_evaluation_result(self) -> None:
        """Test creating a valid EvaluationResult."""
        metrics = [
            MetricScore(metric_name="clarity_coherence", score=85.0, evaluator_comment="Clear"),
            MetricScore(metric_name="coverage", score=80.0, evaluator_comment="Good coverage"),
            MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Highly relevant"),
        ]

        result = EvaluationResult(metrics=metrics, overall_score=85.0)

        assert len(result.metrics) == 3
        assert result.overall_score == 85.0

    def test_empty_metrics_list_raises_error(self) -> None:
        """Test that empty metrics list raises ValidationError (FR-001)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationResult(metrics=[], overall_score=0.0)

        error = exc_info.value
        assert "metrics" in str(error)

    def test_duplicate_metric_names_raises_error(self) -> None:
        """Test that duplicate metric names raise ValidationError."""
        metrics = [
            MetricScore(metric_name="clarity_coherence", score=85.0, evaluator_comment="Clear"),
            MetricScore(
                metric_name="clarity_coherence",
                score=80.0,
                evaluator_comment="Duplicate",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            EvaluationResult(metrics=metrics, overall_score=82.5)

        error = exc_info.value
        assert "duplicate" in str(error).lower()
        assert "clarity_coherence" in str(error)

    def test_overall_score_accepts_any_real_value(self) -> None:
        """Test that overall_score accepts any real value (no constraints)."""
        metric = MetricScore(metric_name="test_metric", score=50.0, evaluator_comment="Test")

        # Test typical LLMJudgeMetric range (0-100)
        result_zero = EvaluationResult(metrics=[metric], overall_score=0.0)
        assert result_zero.overall_score == 0.0

        result_hundred = EvaluationResult(metrics=[metric], overall_score=100.0)
        assert result_hundred.overall_score == 100.0

        result_mid = EvaluationResult(metrics=[metric], overall_score=50.5)
        assert result_mid.overall_score == 50.5

        # Test negative values (with custom metrics)
        metric_negative = MetricScore(metric_name="custom", score=-20.0, evaluator_comment="Negative")
        result_negative = EvaluationResult(metrics=[metric_negative], overall_score=-20.0)
        assert result_negative.overall_score == -20.0

        # Test values above 100 (with custom metrics)
        metric_high = MetricScore(metric_name="custom", score=150.0, evaluator_comment="High")
        result_above = EvaluationResult(metrics=[metric_high], overall_score=150.0)
        assert result_above.overall_score == 150.0

        # Test mixed positive and negative (weighted average can be anywhere)
        metrics_mixed = [
            MetricScore(metric_name="positive", score=100.0, evaluator_comment="Good"),
            MetricScore(metric_name="negative", score=-50.0, evaluator_comment="Bad"),
        ]
        result_mixed = EvaluationResult(metrics=metrics_mixed, overall_score=25.0)
        assert result_mixed.overall_score == 25.0

    def test_overall_score_rounding(self) -> None:
        """Test that overall_score is rounded to 2 decimal places."""
        metric = MetricScore(metric_name="test_metric", score=50.0, evaluator_comment="Test")

        result = EvaluationResult(metrics=[metric], overall_score=87.12345)

        assert result.overall_score == 87.12

    def test_single_metric_result(self) -> None:
        """Test EvaluationResult with single metric."""
        metric = MetricScore(metric_name="clarity_coherence", score=85.5, evaluator_comment="Good")

        result = EvaluationResult(metrics=[metric], overall_score=85.5)

        assert len(result.metrics) == 1
        assert result.metrics[0].metric_name == "clarity_coherence"
        assert result.overall_score == 85.5

    def test_multiple_metrics_result(self) -> None:
        """Test EvaluationResult with multiple metrics."""
        metrics = [
            MetricScore(metric_name="clarity_coherence", score=85.0, evaluator_comment="Clear"),
            MetricScore(metric_name="coverage", score=80.0, evaluator_comment="Good coverage"),
            MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
            MetricScore(metric_name="custom_metric", score=75.0, evaluator_comment="Custom"),
        ]

        result = EvaluationResult(metrics=metrics, overall_score=82.5)

        assert len(result.metrics) == 4
        metric_names = [m.metric_name for m in result.metrics]
        assert "clarity_coherence" in metric_names
        assert "coverage" in metric_names
        assert "relevance" in metric_names
        assert "custom_metric" in metric_names


class TestEvaluationResultSerialization:
    """Test EvaluationResult serialization/deserialization."""

    def test_evaluation_result_to_dict(self) -> None:
        """Test converting EvaluationResult to dictionary."""
        metrics = [
            MetricScore(metric_name="clarity_coherence", score=85.0, evaluator_comment="Clear"),
            MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Relevant"),
        ]

        result = EvaluationResult(metrics=metrics, overall_score=87.5)
        data = result.model_dump()

        assert "metrics" in data
        assert "overall_score" in data
        assert len(data["metrics"]) == 2
        assert data["overall_score"] == 87.5

    def test_evaluation_result_to_json(self) -> None:
        """Test converting EvaluationResult to JSON."""
        metrics = [
            MetricScore(metric_name="clarity_coherence", score=85.0, evaluator_comment="Clear"),
        ]

        result = EvaluationResult(metrics=metrics, overall_score=85.0)
        json_str = result.model_dump_json()

        assert "clarity_coherence" in json_str
        assert "85" in json_str

    def test_evaluation_result_from_dict(self) -> None:
        """Test creating EvaluationResult from dictionary."""
        data = {
            "metrics": [
                {
                    "metric_name": "clarity_coherence",
                    "score": 85.0,
                    "evaluator_comment": "Clear",
                },
                {
                    "metric_name": "relevance",
                    "score": 90.0,
                    "evaluator_comment": "Relevant",
                },
            ],
            "overall_score": 87.5,
        }

        result = EvaluationResult.model_validate(data)

        assert len(result.metrics) == 2
        assert result.overall_score == 87.5
        assert result.metrics[0].metric_name == "clarity_coherence"
