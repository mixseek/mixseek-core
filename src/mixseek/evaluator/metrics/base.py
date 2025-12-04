"""評価メトリクスの基底メトリクスインターフェース。"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from mixseek.evaluator.llm_client import evaluate_with_llm
from mixseek.models.evaluation_result import MetricScore

if TYPE_CHECKING:
    from mixseek.config.schema import PromptBuilderSettings


class BaseLLMEvaluation(BaseModel):
    """LLM-as-a-Judgeの評価結果のための共通の構造化出力モデル。

    すべての組み込みメトリクスとカスタムメトリクスは、llm-as-a-judgeの応答形式として
    このモデルを使用できます。

    Example:
        ```python
        from mixseek.evaluator.metrics.base import BaseEvaluation

        class CustomEvaluation(BaseEvaluation):
            pass  # 基底クラスのフィールドをそのまま使用
        ```
    """

    score: float = Field(ge=0.0, le=100.0, description="0から100の間の評価スコア")
    evaluator_comment: str = Field(description="スコアの連鎖思考推論とフィードバック")


class BaseMetric(ABC):
    """評価メトリクスの抽象基底クラス。

    すべての評価メトリクス（組み込みおよびカスタム）は、このクラスを継承し、
    `evaluate`メソッドを実装する必要があります。これにより、システム全体で
    メトリクス評価の一貫したインターフェースが保証されます。

    LLM-as-a-Judgeを使用する場合は、LLMJudgeMetricクラスを継承してください。
    LLMJudgeMetricは追加のLLMパラメータ（model、temperature等）を受け取ります。

    Example:
        ```python
        from mixseek.evaluator.metrics.base import BaseMetric
        from mixseek.models.evaluation_result import MetricScore

        class CustomStatisticalMetric(BaseMetric):
            def evaluate(
                self,
                user_query: str,
                submission: str,
            ) -> MetricScore:
                # 統計ベースの評価ロジック（LLMを使用しない例）
                word_count = len(submission.split())
                score = min(100.0, word_count * 2)
                return MetricScore(
                    metric_name="WordCountMetric",
                    score=score,
                    evaluator_comment=f"Submission contains {word_count} words"
                )
        ```
    """

    @abstractmethod
    async def evaluate(self, user_query: str, submission: str, **kwargs: object) -> MetricScore:
        """このメトリクスを使用してSubmissionを評価します（非同期）。

        このメソッドはすべてのメトリクスクラスで実装する必要があります。
        ユーザーのクエリとAIのSubmissionを受け取り、メトリクスの基準に従って
        それらを評価し、スコアとコメントを含むMetricScoreを返します。

        注意: LLM-as-a-Judgeを使用するメトリクスの場合は、LLMJudgeMetricを
        継承してください。LLMJudgeMetricでは追加のLLMパラメータ（model、
        temperature等）を受け取ります。

        Args:
            user_query: ユーザーからの元のクエリ
            submission: AIエージェントによって生成されたSubmission
            **kwargs: サブクラスで必要な追加パラメータ（例：model、temperature等）

        Returns:
            以下を含むMetricScore：
                - metric_name: このメトリクスの名前
                - score: 0から100の間の数値スコア
                - evaluator_comment: スコアの詳細な説明

        Raises:
            ValueError: 入力が無効な場合

        Example:
            ```python
            class CustomMetric(BaseMetric):
                async def evaluate(self, user_query: str, submission: str, **kwargs: object) -> MetricScore:
                    # カスタム評価ロジック（例：統計ベースの評価）
                    # 同期処理も async 関数内で実行可能
                    word_count = len(submission.split())
                    score = min(100.0, word_count * 2)  # 単純な例
                    return MetricScore(
                        metric_name="CustomMetric",
                        score=score,
                        evaluator_comment=f"Word count: {word_count}"
                    )

            metric = CustomMetric()
            score = await metric.evaluate(
                user_query="What is Python?",
                submission="Python is a programming language...",
            )
            print(f"Score: {score.score}")
            print(f"Comment: {score.evaluator_comment}")
            ```
        """
        pass


class LLMJudgeMetric(BaseMetric):
    """LLM-as-a-Judgeを使用した評価メトリクスの抽象基底クラス。

    すべてのLLM-as-a-Judge評価メトリクスは、このクラスを継承し、
    `get_instruction`メソッドを実装する必要があります。
    共通の評価ロジックは`evaluate`メソッドで提供されます。
    メトリクス名はクラス名から自動的に取得されます。

    Example:
        ```python
        from mixseek.evaluator.metrics.base import LLMJudgeMetric

        class CustomLLMMetric(LLMJudgeMetric):
            def get_instruction(self) -> str:
                return "カスタム評価の指示..."
        ```
    """

    @abstractmethod
    def get_instruction(self) -> str:
        """評価用のシステムプロンプト（instruction）を返します。

        このメソッドはサブクラスで実装する必要があります。
        LLM-as-a-Judgeに与える評価基準と指示を含む文字列を返してください。

        Returns:
            評価基準とスコアリングガイドを含むシステムプロンプト
        """
        pass

    def _get_user_prompt(
        self,
        user_query: str,
        submission: str,
        prompt_builder_settings: "PromptBuilderSettings",
    ) -> str:
        """評価指示を含むユーザープロンプトを生成します。

        UserPromptBuilderを使用してプロンプトを整形します。

        Args:
            user_query: ユーザーからの元のクエリ
            submission: AIエージェントによって生成されたSubmission
            prompt_builder_settings: PromptBuilder設定（必須）

        Returns:
            評価対象のクエリとSubmissionを含むユーザープロンプト
        """
        # Circular import回避のため、ランタイムでのみimport
        # (evaluator → prompt_builder → round_controller → evaluator)
        from mixseek.prompt_builder import EvaluatorPromptContext, UserPromptBuilder

        prompt_builder = UserPromptBuilder(settings=prompt_builder_settings)
        context = EvaluatorPromptContext(
            user_query=user_query,
            submission=submission,
        )
        return prompt_builder.build_evaluator_prompt(context)

    async def evaluate(  # type: ignore[override]
        self,
        user_query: str,
        submission: str,
        model: str,
        prompt_builder_settings: "PromptBuilderSettings",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        max_retries: int = 3,
        system_instruction: str | None = None,
        timeout_seconds: int | None = None,
        stop_sequences: list[str] | None = None,
        top_p: float | None = None,
        seed: int | None = None,
        **_kwargs: object,
    ) -> MetricScore:
        """LLM-as-a-Judgeを使用してSubmissionを評価します。

        このメソッドは共通の評価フローを実装しており、サブクラスで
        オーバーライドする必要はありません。各メトリクス固有の動作は、
        `get_instruction`メソッドで制御します。メトリクス名はクラス名から
        自動的に取得されます。

        Args:
            user_query: ユーザーからの元のクエリ
            submission: AIエージェントによって生成されたSubmission
            model: LLMモデル識別子（フォーマット："provider:model-name"）
                例："anthropic:claude-sonnet-4-5-20250929", "openai:gpt-4"
            prompt_builder_settings: PromptBuilder設定（必須、Article 9準拠）
            temperature: LLM temperature設定。0.0で決定的な出力、高いほどランダム性が増す（FR-019）
            max_tokens: LLM max_tokens設定。Noneの場合は制限なし（FR-019）
            max_retries: LLM API呼び出しの最大リトライ試行回数（FR-010, FR-019）
            system_instruction: オプションのsystem_instruction上書き。Noneの場合はget_instruction()を使用（FR-019）
            timeout_seconds: HTTPタイムアウト（秒）。Noneの場合はデフォルトタイムアウト
            stop_sequences: 生成を停止するシーケンスのリスト。Noneの場合は使用しない
            top_p: Top-pサンプリングパラメータ（0.0-1.0）。Noneの場合はモデルデフォルト
            seed: ランダムシード。Noneの場合はランダム（OpenAI/Geminiでサポート）

        Returns:
            評価スコア（0-100）と詳細なコメントを含むMetricScore

        Raises:
            EvaluatorAPIError: すべてのリトライ後にLLM API呼び出しが失敗した場合

        Example:
            ```python
            from mixseek.config.schema import PromptBuilderSettings
            from mixseek.evaluator.metrics.clarity_coherence import ClarityCoherence

            settings = PromptBuilderSettings()
            metric = ClarityCoherence()
            score = await metric.evaluate(
                user_query="What is Python?",
                submission="Python is a high-level programming language...",
                model="anthropic:claude-sonnet-4-5-20250929",
                prompt_builder_settings=settings,
                temperature=0.0,
                max_tokens=2000,
                max_retries=3,
                system_instruction=None  # デフォルトのinstructionを使用
            )
            print(f"Score: {score.score}")
            print(f"Comment: {score.evaluator_comment}")
            ```
        """

        # system_instructionの上書きがある場合は使用、なければget_instruction()を使用（FR-019）
        instruction = system_instruction if system_instruction is not None else self.get_instruction()

        user_prompt = self._get_user_prompt(user_query, submission, prompt_builder_settings)

        # 構造化された出力でLLMを呼び出す（FR-010, FR-019）
        raw_result = await evaluate_with_llm(
            instruction=instruction,
            user_prompt=user_prompt,
            model=model,
            response_model=BaseLLMEvaluation,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            stop_sequences=stop_sequences,
            top_p=top_p,
            seed=seed,
        )
        # BaseLLMEvaluation型として扱う
        assert isinstance(raw_result, BaseLLMEvaluation)
        result: BaseLLMEvaluation = raw_result

        # Type assertion for mypy (result is guaranteed to be BaseLLMEvaluation)
        assert isinstance(result, BaseLLMEvaluation)

        # MetricScoreに変換（メトリクス名はクラス名から取得）
        return MetricScore(
            metric_name=type(self).__name__,
            score=result.score,
            evaluator_comment=result.evaluator_comment,
        )
