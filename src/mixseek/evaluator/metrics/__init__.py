"""組み込み評価メトリクス。

このモジュールは組み込み評価メトリクスの実装を含みます：
    - ClarityCoherence: Submissionの明瞭性/一貫性を評価
    - Coverage: Submissionの包括性を評価
    - Relevance: ユーザークエリに対するSubmissionの関連性を評価
    - LLMPlain: system_instruction上書き可能な汎用LLM-as-a-Judge評価

すべてのメトリクスはBaseMetricインターフェースを実装します。
"""

from mixseek.evaluator.metrics.base import BaseMetric
from mixseek.evaluator.metrics.clarity_coherence import ClarityCoherence
from mixseek.evaluator.metrics.coverage import Coverage
from mixseek.evaluator.metrics.llm_plain import LLMPlain
from mixseek.evaluator.metrics.relevance import Relevance

__all__ = [
    "BaseMetric",
    "ClarityCoherence",
    "Coverage",
    "LLMPlain",
    "Relevance",
]
