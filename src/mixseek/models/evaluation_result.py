"""評価結果モデル。"""

from pydantic import BaseModel, Field, field_validator


class MetricScore(BaseModel):
    """単一メトリクスの評価スコア。

    このモデルは、1つの特定のメトリクス（例：明瞭性/一貫性、包括性、または関連性）を
    評価した結果を表します。量的スコアと評価を説明する質的コメントの両方が含まれます。

    Attributes:
        metric_name: メトリクスの名前（例："clarity_coherence"、"coverage"、"relevance"）
        score: 数値スコア（任意の実数値）。組み込みLLMJudgeMetricsは0-100を返しますが、
            カスタムメトリクスでは負の値や100を超える値も許容されます
        evaluator_comment: スコアの詳細な説明（FR-012）

    Example:
        ```python
        from mixseek.models.evaluation_result import MetricScore

        # LLMJudgeMetricの例（通常0-100）
        metric = MetricScore(
            metric_name="clarity_coherence",
            score=85.5,
            evaluator_comment="The response is well-structured and easy to understand..."
        )

        # カスタムメトリクスの例（任意の値）
        custom_metric = MetricScore(
            metric_name="performance_delta",
            score=-15.2,
            evaluator_comment="Performance degraded by 15.2%"
        )
        ```

    Validation Rules:
        - metric_name: 空でない文字列でなければならない
        - score: 任意の実数値（制約なし）
        - evaluator_comment: 文字列（空文字列も許容される）
    """

    metric_name: str = Field(
        ..., description="評価メトリクスの名前", examples=["clarity_coherence", "coverage", "relevance"]
    )

    score: float = Field(
        ...,
        description="数値スコア（任意の実数値、カスタムメトリクスでは負の値や100超も許容）",
        examples=[85.5, 72.3, 91.0, -10.5, 150.0],
    )

    evaluator_comment: str = Field(
        ...,
        description="スコアの詳細な説明（FR-012）。空文字列も許容される。",
        examples=[
            "The response is well-structured and easy to understand. "
            "Technical terms are explained clearly. Minor improvements possible in conclusion.",
            "",
        ],
    )

    @field_validator("metric_name")
    @classmethod
    def validate_metric_name(cls, v: str) -> str:
        """メトリクス名が空でないことを検証します。"""
        if not v or not v.strip():
            raise ValueError("Metric name cannot be empty")
        return v.strip()

    @field_validator("score")
    @classmethod
    def round_score_to_two_decimals(cls, v: float) -> float:
        """一貫性のためにスコアを小数点以下2桁に丸めます。"""
        return round(v, 2)

    @field_validator("evaluator_comment")
    @classmethod
    def normalize_comment(cls, v: str) -> str:
        """コメントを正規化します。空文字列も許容されます。"""
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "metric_name": "clarity_coherence",
                    "score": 85.5,
                    "evaluator_comment": "The response is well-structured with clear language. "
                    "Technical terms are explained adequately. "
                    "Minor improvements possible in the conclusion section.",
                }
            ]
        }
    }


class EvaluationResult(BaseModel):
    """すべてのメトリクススコアと総合スコアを含む完全な評価結果。

    このモデルは、評価システムの最終出力を表し、
    個別のメトリクススコアと重み付き平均として計算された
    集約された総合スコアを含みます（FR-004、FR-012）。

    Attributes:
        metrics: 個別のメトリクススコアのリスト
        overall_score: すべてのメトリクススコアの重み付き平均（任意の実数値）。
            組み込みLLMJudgeMetricsのみを使用する場合は通常0-100ですが、
            カスタムメトリクスを含む場合は負の値や100を超える値も許容されます

    Example:
        ```python
        from mixseek.models.evaluation_result import EvaluationResult, MetricScore

        # LLMJudgeMetricsのみの例（通常0-100）
        result = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=85.5, evaluator_comment="Clear..."),
                MetricScore(metric_name="relevance", score=90.0, evaluator_comment="Highly relevant..."),
            ],
            overall_score=87.2
        )

        # カスタムメトリクスを含む例（任意の値）
        result_with_custom = EvaluationResult(
            metrics=[
                MetricScore(metric_name="clarity_coherence", score=85.5, evaluator_comment="Clear..."),
                MetricScore(metric_name="performance_delta", score=-20.0, evaluator_comment="Degraded..."),
            ],
            overall_score=32.75  # 重み付き平均
        )
        ```

    Validation Rules:
        - metrics: 少なくとも1つのメトリクスを含む必要がある（FR-001は3つの組み込みメトリクスを要求）
        - overall_score: 任意の実数値（制約なし）
        - overall_score: メトリクススコアの重み付き平均と一致する必要がある
    """

    metrics: list[MetricScore] = Field(..., description="個別のメトリクススコアのリスト（FR-012）", min_length=1)

    overall_score: float = Field(
        ...,
        description="すべてのメトリクススコアの重み付き平均（任意の実数値、負の値や100超も許容）",
        examples=[87.2, 75.5, 92.3, -5.3, 120.0],
    )

    @field_validator("overall_score")
    @classmethod
    def round_overall_score(cls, v: float) -> float:
        """総合スコアを小数点以下2桁に丸めます。"""
        return round(v, 2)

    @field_validator("metrics")
    @classmethod
    def validate_unique_metric_names(cls, v: list[MetricScore]) -> list[MetricScore]:
        """各メトリクスが一度だけ現れることを検証します。"""
        metric_names = [m.metric_name for m in v]
        duplicates = [name for name in metric_names if metric_names.count(name) > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate metric names found: {', '.join(set(duplicates))}. "
                "Each metric should appear only once in the result."
            )

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "metrics": [
                        {
                            "metric_name": "clarity_coherence",
                            "score": 85.5,
                            "evaluator_comment": "Well-structured and clear.",
                        },
                        {
                            "metric_name": "coverage",
                            "score": 78.0,
                            "evaluator_comment": "Covers main points, some depth missing.",
                        },
                        {
                            "metric_name": "relevance",
                            "score": 92.0,
                            "evaluator_comment": "Highly relevant to the query.",
                        },
                    ],
                    "overall_score": 85.2,
                }
            ]
        }
    }
