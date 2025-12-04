"""Unit tests for MetricConfig and EvaluationConfig models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from mixseek.models.evaluation_config import EvaluationConfig, LLMDefaultConfig, MetricConfig


class TestMetricConfigValidation:
    """Test MetricConfig validation rules."""

    def test_valid_metric_config_with_model(self) -> None:
        """Test creating valid MetricConfig with model override."""
        metric = MetricConfig(
            name="clarity_coherence",
            weight=0.4,
            model="anthropic:claude-sonnet-4-5-20250929",
        )

        assert metric.name == "clarity_coherence"
        assert metric.weight == 0.4
        assert metric.model == "anthropic:claude-sonnet-4-5-20250929"

    def test_valid_metric_config_without_model(self) -> None:
        """Test creating valid MetricConfig without model (uses default)."""
        metric = MetricConfig(name="coverage", weight=0.3)

        assert metric.name == "coverage"
        assert metric.weight == 0.3
        assert metric.model is None

    def test_weight_within_0_to_1_range(self) -> None:
        """Test that weight must be within 0-1 range (FR-003)."""
        # Minimum
        metric_min = MetricConfig(name="test_metric", weight=0.0)
        assert metric_min.weight == 0.0

        # Maximum
        metric_max = MetricConfig(name="test_metric", weight=1.0)
        assert metric_max.weight == 1.0

        # Mid-range
        metric_mid = MetricConfig(name="test_metric", weight=0.5)
        assert metric_mid.weight == 0.5

    def test_weight_below_zero_raises_error(self) -> None:
        """Test that weight below 0 raises ValidationError (FR-003)."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="test_metric", weight=-0.1)

        error = exc_info.value
        assert "weight" in str(error)

    def test_weight_above_one_raises_error(self) -> None:
        """Test that weight above 1.0 raises ValidationError (FR-003)."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="test_metric", weight=1.1)

        error = exc_info.value
        assert "weight" in str(error)

    def test_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="", weight=0.5)

        error = exc_info.value
        assert "name" in str(error).lower()

    def test_whitespace_only_name_raises_error(self) -> None:
        """Test that whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="   \n\t  ", weight=0.5)

        error = exc_info.value
        assert "name" in str(error).lower()

    def test_invalid_model_format_missing_colon(self) -> None:
        """Test that model format without colon raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="test_metric", weight=0.5, model="invalid-model-format")

        error = exc_info.value
        assert "model" in str(error).lower() or "format" in str(error).lower()

    def test_invalid_model_format_empty_provider(self) -> None:
        """Test that model format with empty provider raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="test_metric", weight=0.5, model=":model-name")

        error = exc_info.value
        assert "provider" in str(error).lower() or "format" in str(error).lower()

    def test_invalid_model_format_empty_model_name(self) -> None:
        """Test that model format with empty model name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MetricConfig(name="test_metric", weight=0.5, model="anthropic:")

        error = exc_info.value
        assert "model" in str(error).lower() or "format" in str(error).lower()

    def test_valid_model_formats(self) -> None:
        """Test various valid model formats."""
        valid_formats = [
            "anthropic:claude-sonnet-4-5-20250929",
            "openai:gpt-5",
            "openai:gpt-4-turbo",
            "custom:my-model-v1",
        ]

        for model_format in valid_formats:
            metric = MetricConfig(name="test_metric", weight=0.5, model=model_format)
            assert metric.model == model_format

    def test_name_normalization(self) -> None:
        """Test that name whitespace is normalized."""
        metric = MetricConfig(name="  clarity_coherence  ", weight=0.4)
        assert metric.name == "clarity_coherence"

    def test_optional_weight_allowed(self) -> None:
        """Test that weight can be None (for equal weight distribution)."""
        metric = MetricConfig(name="test_metric", weight=None)
        assert metric.weight is None


class TestEvaluationConfigValidation:
    """Test EvaluationConfig validation rules."""

    def test_valid_config_with_three_metrics(self) -> None:
        """Test creating valid EvaluationConfig with three metrics."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="clarity_coherence", weight=0.4),
                MetricConfig(name="coverage", weight=0.3),
                MetricConfig(name="relevance", weight=0.3),
            ],
        )

        assert config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert config.llm_default.max_retries == 3
        assert len(config.metrics) == 3
        assert len(config.metric_weights) == 3
        assert len(config.enabled_metrics) == 3

    def test_weights_sum_to_one_validation(self) -> None:
        """Test that weights must sum to 1.0 (±0.001 tolerance) (FR-009)."""
        # Valid: Exactly 1.0
        config_exact = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="metric1", weight=0.5),
                MetricConfig(name="metric2", weight=0.5),
            ],
        )
        assert config_exact is not None

        # Valid: Within tolerance (0.9995)
        config_low = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="metric1", weight=0.4995),
                MetricConfig(name="metric2", weight=0.5),
            ],
        )
        assert config_low is not None

        # Valid: Within tolerance (1.0005)
        config_high = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="metric1", weight=0.5005),
                MetricConfig(name="metric2", weight=0.5),
            ],
        )
        assert config_high is not None

    def test_weights_not_summing_to_one_raises_error(self) -> None:
        """Test that weights not summing to 1.0 raises ValidationError (FR-009)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
                metrics=[
                    MetricConfig(name="metric1", weight=0.5),
                    MetricConfig(name="metric2", weight=0.3),
                ],
            )

        error = exc_info.value
        assert "weight" in str(error).lower()
        assert "sum" in str(error).lower() or "0.8" in str(error)

    def test_duplicate_metric_names_raises_error(self) -> None:
        """Test that duplicate metric names raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
                metrics=[
                    MetricConfig(name="clarity_coherence", weight=0.5),
                    MetricConfig(name="clarity_coherence", weight=0.5),
                ],
            )

        error = exc_info.value
        assert "duplicate" in str(error).lower()
        assert "clarity_coherence" in str(error)

    def test_empty_metrics_list_raises_error(self) -> None:
        """Test that empty metrics list raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
                metrics=[],
            )

        error = exc_info.value
        assert "metrics" in str(error).lower()

    def test_invalid_default_model_format_raises_error(self) -> None:
        """Test that invalid default_model format raises ValidationError (FR-016)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="invalid-format", max_retries=3),
                metrics=[MetricConfig(name="test_metric", weight=1.0)],
            )

        error = exc_info.value
        assert "model" in str(error).lower() or "format" in str(error).lower()

    def test_negative_max_retries_raises_error(self) -> None:
        """Test that negative max_retries raises ValidationError (FR-010)."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=-1),
                metrics=[MetricConfig(name="test_metric", weight=1.0)],
            )

        error = exc_info.value
        assert "max_retries" in str(error).lower()

    def test_equal_weights_when_all_none(self) -> None:
        """Test that equal weights are applied when all weights are None (FR-008)."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="metric1", weight=None),
                MetricConfig(name="metric2", weight=None),
                MetricConfig(name="metric3", weight=None),
            ],
        )

        # Each should have weight of 1/3
        expected_weight = 1.0 / 3
        for metric in config.metrics:
            assert metric.weight is not None
            assert abs(metric.weight - expected_weight) < 0.001

    def test_mixed_none_and_set_weights_raises_error(self) -> None:
        """Test that mixing None and set weights raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig(
                llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
                metrics=[
                    MetricConfig(name="metric1", weight=0.5),
                    MetricConfig(name="metric2", weight=None),
                ],
            )

        error = exc_info.value
        # Error message contains "weight" or Japanese "重み"
        error_str = str(error).lower()
        assert "weight" in error_str or "重み" in str(error)

    def test_metric_weights_dict_populated(self) -> None:
        """Test that metric_weights dictionary is correctly populated."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="clarity_coherence", weight=0.4),
                MetricConfig(name="coverage", weight=0.3),
                MetricConfig(name="relevance", weight=0.3),
            ],
        )

        assert "clarity_coherence" in config.metric_weights
        assert "coverage" in config.metric_weights
        assert "relevance" in config.metric_weights
        assert config.metric_weights["clarity_coherence"] == 0.4
        assert config.metric_weights["coverage"] == 0.3
        assert config.metric_weights["relevance"] == 0.3

    def test_enabled_metrics_list_populated(self) -> None:
        """Test that enabled_metrics list is correctly populated."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="clarity_coherence", weight=0.5),
                MetricConfig(name="relevance", weight=0.5),
            ],
        )

        assert len(config.enabled_metrics) == 2
        assert "clarity_coherence" in config.enabled_metrics
        assert "relevance" in config.enabled_metrics

    def test_get_model_for_metric_with_override(self) -> None:
        """Test get_model_for_metric returns metric-specific model (FR-015)."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="clarity_coherence", weight=0.5, model="openai:gpt-5"),
                MetricConfig(name="relevance", weight=0.5),
            ],
        )

        # Metric with override
        model = config.get_model_for_metric("clarity_coherence")
        assert model == "openai:gpt-5"

    def test_get_model_for_metric_with_default(self) -> None:
        """Test get_model_for_metric returns default when no override (FR-016)."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[
                MetricConfig(name="clarity_coherence", weight=0.5),
                MetricConfig(name="relevance", weight=0.5),
            ],
        )

        # Metric without override
        model = config.get_model_for_metric("relevance")
        assert model == "anthropic:claude-sonnet-4-5-20250929"

    def test_get_model_for_nonexistent_metric_raises_error(self) -> None:
        """Test get_model_for_metric raises error for unknown metric."""
        config = EvaluationConfig(
            llm_default=LLMDefaultConfig(model="anthropic:claude-sonnet-4-5-20250929", max_retries=3),
            metrics=[MetricConfig(name="clarity_coherence", weight=1.0)],
        )

        with pytest.raises(ValueError) as exc_info:
            config.get_model_for_metric("nonexistent_metric")

        error = exc_info.value
        assert "not found" in str(error).lower()
        assert "nonexistent_metric" in str(error)


class TestEvaluationConfigTOMLLoading:
    """Test EvaluationConfig TOML file loading."""

    def test_load_valid_config_from_toml(self, temp_workspace: Path, valid_config_toml_content: str) -> None:
        """Test loading valid configuration from TOML file."""
        config = EvaluationConfig.from_toml_file(temp_workspace)

        assert config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert config.llm_default.max_retries == 3
        assert len(config.metrics) == 3

    def test_load_config_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Test that missing config file raises FileNotFoundError."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            EvaluationConfig.from_toml_file(workspace)

        error = exc_info.value
        assert "not found" in str(error).lower()
        assert "evaluator.toml" in str(error)

    def test_load_config_invalid_toml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid TOML syntax raises ValueError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"

        # Write invalid TOML
        config_file.write_text("invalid toml content [[[")

        with pytest.raises(ValueError) as exc_info:
            EvaluationConfig.from_toml_file(workspace)

        error = exc_info.value
        error_str = str(error).lower()
        # TOMLDecodeErrorのメッセージには"toml"、"syntax"、または"expected"が含まれる
        assert "toml" in error_str or "syntax" in error_str or "expected" in error_str

    def test_load_config_with_invalid_weights(self, tmp_path: Path, invalid_weights_config_toml: str) -> None:
        """Test loading config with invalid weights raises ValidationError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(invalid_weights_config_toml)

        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig.from_toml_file(workspace)

        error = exc_info.value
        assert "weight" in str(error).lower()

    def test_load_config_with_invalid_model_format(
        self, tmp_path: Path, invalid_model_format_config_toml: str
    ) -> None:
        """Test loading config with invalid model format raises ValidationError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(invalid_model_format_config_toml)

        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig.from_toml_file(workspace)

        error = exc_info.value
        assert "model" in str(error).lower() or "format" in str(error).lower()

    def test_load_config_with_no_metrics(self, tmp_path: Path, missing_metrics_config_toml: str) -> None:
        """Test loading config with no metrics raises ValidationError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        config_dir = workspace / "configs"
        config_dir.mkdir()
        config_file = config_dir / "evaluator.toml"
        config_file.write_text(missing_metrics_config_toml)

        with pytest.raises(ValidationError) as exc_info:
            EvaluationConfig.from_toml_file(workspace)

        error = exc_info.value
        assert "metrics" in str(error).lower()
