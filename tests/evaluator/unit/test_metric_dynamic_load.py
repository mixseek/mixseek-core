"""_load_metric_from_directory の動的ロードパステスト

metricsディレクトリに配置されたメトリクスをクラス名から
snake_case変換→importlib で動的ロードする経路を検証する。
特にアクロニム含みの名前（LLMPlain → llm_plain）での変換を重点的にテスト。
"""

from pathlib import Path

import pytest

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import PromptBuilderSettings
from mixseek.evaluator.evaluator import Evaluator
from mixseek.evaluator.metrics.base import BaseMetric


@pytest.fixture
def evaluator(temp_workspace: Path) -> Evaluator:
    """テスト用Evaluatorインスタンス"""
    manager = ConfigurationManager(workspace=temp_workspace)
    settings = manager.get_evaluator_settings()
    return Evaluator(settings=settings, prompt_builder_settings=PromptBuilderSettings())


class TestLoadMetricFromDirectory:
    """_load_metric_from_directory のユニットテスト"""

    def test_standard_pascal_case(self, evaluator: Evaluator) -> None:
        """ClarityCoherence → clarity_coherence.py から動的ロード"""
        metric = evaluator._load_metric_from_directory("ClarityCoherence")
        assert isinstance(metric, BaseMetric)

    def test_acronym_containing_name(self, evaluator: Evaluator) -> None:
        """LLMPlain → llm_plain.py から動的ロード（アクロニム対応regex検証）"""
        metric = evaluator._load_metric_from_directory("LLMPlain")
        assert isinstance(metric, BaseMetric)

    def test_single_word_name(self, evaluator: Evaluator) -> None:
        """Coverage → coverage.py から動的ロード"""
        metric = evaluator._load_metric_from_directory("Coverage")
        assert isinstance(metric, BaseMetric)

    def test_all_builtin_metrics_loadable(self, evaluator: Evaluator) -> None:
        """全ビルトインメトリクスがディレクトリからも動的ロード可能"""
        for name in ("ClarityCoherence", "Coverage", "LLMPlain", "Relevance"):
            metric = evaluator._load_metric_from_directory(name)
            assert isinstance(metric, BaseMetric), f"{name} の動的ロードに失敗"

    def test_nonexistent_metric_raises_import_error(self, evaluator: Evaluator) -> None:
        """存在しないメトリクス名で ImportError"""
        with pytest.raises(ImportError):
            evaluator._load_metric_from_directory("NonExistentMetric")
