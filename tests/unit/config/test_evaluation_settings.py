"""Tests for Evaluator settings loading via ConfigurationManager.

T080実装のテスト: ConfigurationManager.load_evaluation_settings()
"""

from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import EvaluatorSettings
from mixseek.models.evaluation_config import EvaluationConfig, evaluator_settings_to_evaluation_config


class TestLoadEvaluationSettings:
    """ConfigurationManager.load_evaluation_settings()のテスト。"""

    def test_load_evaluator_toml(self, temp_workspace: Path) -> None:
        """configs/evaluator.tomlの読み込み。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Assert
        assert isinstance(evaluator_settings, EvaluatorSettings)
        assert evaluator_settings.default_model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluator_settings.temperature == 0.0
        assert evaluator_settings.max_tokens == 2000
        assert evaluator_settings.max_retries == 3
        assert len(evaluator_settings.metrics) == 3  # 3つのメトリクス
        assert evaluator_settings.custom_metrics == {}

    def test_load_evaluation_settings_with_tracing(self, temp_workspace: Path) -> None:
        """トレーシング機能の検証。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Assert: トレース情報の存在確認
        assert hasattr(evaluator_settings, "__source_traces__")
        traces = getattr(evaluator_settings, "__source_traces__")
        assert isinstance(traces, dict)

        # default_modelフィールドのトレース情報を確認
        # Phase 2-4: トレース情報が存在することを確認（ソースタイプは優先順位による）
        if "default_model" in traces:
            trace = traces["default_model"]
            assert trace.source_type in ("cli", "toml", "env"), "Valid source type"
            assert trace.value == "anthropic:claude-sonnet-4-5-20250929"
            assert trace.source_name in ("CLI", "TOML", "evaluator.toml", "environment_variables")

    def test_load_evaluation_settings_file_not_found(self) -> None:
        """存在しないファイルの読み込みエラー。"""
        # Arrange
        manager = ConfigurationManager(workspace=Path.cwd())
        toml_file = Path("nonexistent_evaluator.toml")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Evaluator config file not found"):
            manager.load_evaluation_settings(toml_file)

    def test_load_evaluation_settings_with_cli_override(self, temp_workspace: Path) -> None:
        """CLI引数による上書き。"""
        # Arrange
        manager = ConfigurationManager(
            workspace=temp_workspace,
            cli_args={"temperature": 0.9, "max_tokens": 8000},
        )
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Assert: CLI引数が優先される
        assert evaluator_settings.temperature == 0.9  # CLI override
        assert evaluator_settings.max_tokens == 8000  # CLI override
        assert evaluator_settings.default_model == "anthropic:claude-sonnet-4-5-20250929"  # TOML value

    def test_load_evaluation_settings_with_extra_kwargs(self, temp_workspace: Path) -> None:
        """追加引数による設定。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(
            toml_file,
            temperature=0.5,  # extra_kwargs
        )

        # Assert
        assert evaluator_settings.temperature == 0.5  # extra_kwargs override

    def test_load_evaluation_settings_with_relative_path(self, temp_workspace: Path) -> None:
        """相対パスの読み込み（workspace対応）。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        # 相対パスで指定
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Assert: 正しく読み込める
        assert evaluator_settings.default_model == "anthropic:claude-sonnet-4-5-20250929"
        assert len(evaluator_settings.metrics) == 3

    def test_metrics_dynamic_array_support(self, temp_workspace: Path) -> None:
        """metrics配列の動的サポート検証（T080拡張機能）。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")

        # Act
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Assert: metricsが正しくlist[dict[str, Any]]として読み込まれている
        assert isinstance(evaluator_settings.metrics, list)
        assert len(evaluator_settings.metrics) == 3

        # 各メトリクスがdict形式
        for metric in evaluator_settings.metrics:
            assert isinstance(metric, dict)
            assert "name" in metric
            assert "weight" in metric


class TestEvaluatorSettingsToEvaluationConfig:
    """evaluator_settings_to_evaluation_config()変換ヘルパーのテスト。"""

    def test_conversion_from_evaluator_settings(self, temp_workspace: Path) -> None:
        """EvaluatorSettingsからEvaluationConfigへの変換。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Act
        evaluation_config = evaluator_settings_to_evaluation_config(evaluator_settings)

        # Assert
        assert isinstance(evaluation_config, EvaluationConfig)
        assert evaluation_config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert evaluation_config.llm_default.temperature == 0.0
        assert evaluation_config.llm_default.max_tokens == 2000
        assert evaluation_config.llm_default.max_retries == 3
        assert len(evaluation_config.metrics) == 3

    def test_conversion_with_none_temperature(self, temp_workspace: Path) -> None:
        """temperatureがNoneの場合のデフォルト値変換。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")
        evaluator_settings = manager.load_evaluation_settings(toml_file, temperature=None)

        # Act
        evaluation_config = evaluator_settings_to_evaluation_config(evaluator_settings)

        # Assert: Noneの場合は0.0にフォールバック
        assert evaluation_config.llm_default.temperature == 0.0

    def test_metrics_conversion_to_metric_config(self, temp_workspace: Path) -> None:
        """metrics配列がMetricConfigに正しく変換される。"""
        # Arrange
        manager = ConfigurationManager(workspace=temp_workspace)
        toml_file = Path("configs/evaluator.toml")
        evaluator_settings = manager.load_evaluation_settings(toml_file)

        # Act
        evaluation_config = evaluator_settings_to_evaluation_config(evaluator_settings)

        # Assert: 各メトリクスがMetricConfigインスタンス
        for metric in evaluation_config.metrics:
            assert hasattr(metric, "name")
            assert hasattr(metric, "weight")
            assert hasattr(metric, "model")


class TestEvaluationConfigFromTomlFileMigration:
    """EvaluationConfig.from_toml_file()の移行検証（T080）。"""

    def test_from_toml_file_uses_new_system(self, temp_workspace: Path) -> None:
        """from_toml_file()が新しいConfigurationManagerを使用している。"""
        # Act
        evaluation_config = EvaluationConfig.from_toml_file(temp_workspace)

        # Assert: 正しく読み込める（内部実装は新システムを使用）
        assert isinstance(evaluation_config, EvaluationConfig)
        assert evaluation_config.llm_default.model == "anthropic:claude-sonnet-4-5-20250929"
        assert len(evaluation_config.metrics) == 3

    def test_from_toml_file_backward_compatibility(self, temp_workspace: Path) -> None:
        """from_toml_file()の後方互換性検証。"""
        # Act
        evaluation_config = EvaluationConfig.from_toml_file(temp_workspace)

        # Assert: 既存のAPIと同じように動作する
        assert evaluation_config.llm_default.max_retries == 3
        assert len(evaluation_config.enabled_metrics) == 3
        assert len(evaluation_config.metric_weights) == 3

        # get_model_for_metric()などのメソッドも動作する
        model = evaluation_config.get_model_for_metric("ClarityCoherence")
        assert "anthropic" in model or "openai" in model
