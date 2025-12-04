"""評価器コンポーネントのカスタム例外。"""


class EvaluatorConfigError(ValueError):
    """評価器設定エラーの基底例外。

    無効なTOMLファイル、必須フィールドの欠落、検証の失敗など、
    評価器設定に問題がある場合に発生します。

    Example:
        ```python
        raise EvaluatorConfigError("Invalid configuration: weights must sum to 1.0")
        ```
    """

    pass


class WeightValidationError(EvaluatorConfigError):
    """メトリクスの重みの合計が1.0にならない場合に発生します。

    メトリクスの重みの合計が1.0と等しくない場合（±0.001の許容範囲内）、
    設定の検証時にこの例外が発生します。

    Example:
        ```python
        raise WeightValidationError(
            "Metric weights must sum to 1.0, got 0.8. "
            "Current weights: clarity_coherence=0.4, relevance=0.4"
        )
        ```
    """

    pass


class ModelFormatError(EvaluatorConfigError):
    """LLMモデルフォーマットが無効な場合に発生します。

    モデル識別子が期待される"provider:model-name"フォーマットに
    従っていない場合にこの例外が発生します。

    Example:
        ```python
        raise ModelFormatError(
            "Invalid model format: 'gpt-4'. "
            "Expected format: 'provider:model-name' (e.g., 'openai:gpt-5')"
        )
        ```
    """

    pass


class EvaluatorAPIError(Exception):
    """評価中のLLM APIエラーの基底例外。

    すべてのリトライが試行された後、LLM API呼び出しが失敗した場合に発生します。
    プロバイダー、メトリクス、リトライ試行回数の情報を含みます。

    Attributes:
        message: 失敗を説明するエラーメッセージ
        provider: 失敗したLLMプロバイダー（例：「anthropic」、「openai」）
        metric_name: エラー発生時に評価されていたメトリクスの名前
        retry_count: 実行されたリトライ試行回数

    Example:
        ```python
        raise EvaluatorAPIError(
            "Failed to evaluate clarity_coherence metric after 3 retries: API key invalid",
            provider="anthropic",
            metric_name="clarity_coherence",
            retry_count=3
        )
        ```
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        metric_name: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        """EvaluatorAPIErrorを初期化します。

        Args:
            message: 失敗を説明するエラーメッセージ
            provider: 失敗したLLMプロバイダー（例：「anthropic」、「openai」）
            metric_name: 評価されていたメトリクスの名前
            retry_count: 実行されたリトライ試行回数
        """
        super().__init__(message)
        self.provider = provider
        self.metric_name = metric_name
        self.retry_count = retry_count

    def __str__(self) -> str:
        """コンテキストを含むフォーマット済みエラーメッセージを返します。"""
        parts = [super().__str__()]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.metric_name:
            parts.append(f"Metric: {self.metric_name}")
        if self.retry_count is not None:
            parts.append(f"Retries: {self.retry_count}")
        return " | ".join(parts)
