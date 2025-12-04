"""AIエージェント出力評価のためのメインEvaluatorクラス。"""

import importlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mixseek.config.schema import PromptBuilderSettings

from mixseek.config.schema import EvaluatorSettings
from mixseek.evaluator.exceptions import EvaluatorAPIError
from mixseek.evaluator.metrics.base import BaseMetric, LLMJudgeMetric
from mixseek.evaluator.metrics.clarity_coherence import ClarityCoherence
from mixseek.evaluator.metrics.coverage import Coverage
from mixseek.evaluator.metrics.llm_plain import LLMPlain
from mixseek.evaluator.metrics.relevance import Relevance
from mixseek.models.evaluation_config import EvaluationConfig, evaluator_settings_to_evaluation_config
from mixseek.models.evaluation_request import EvaluationRequest
from mixseek.models.evaluation_result import EvaluationResult, MetricScore


class Evaluator:
    """AIエージェント出力評価のためのメインevaluatorクラス。

    このクラスは、組み込みメトリクス(明瞭性/一貫性、包括性、関連性、汎用LLM評価)とカスタムメトリクスの
    サポートを持つLLM-as-a-Judgeを使用してAIエージェントのSubmissionを評価する
    主要なインターフェースを提供します。

    Evaluatorの機能:
        - {workspace}/configs/evaluator.tomlから設定を読み込み
        - 設定されたメトリクスを使用してSubmissionを評価
        - 重み付き総合スコアを計算
        - カスタムメトリクスの登録をサポート
        - リトライロジックによるLLM APIエラーの処理

    Example:
        ```python
        import asyncio
        from pathlib import Path
        from mixseek.config.manager import ConfigurationManager
        from mixseek.evaluator import Evaluator
        from mixseek.models.evaluation_request import EvaluationRequest

        async def main():
            # ConfigurationManager で設定を読み込み
            workspace = Path("/workspace")
            manager = ConfigurationManager(workspace=workspace)
            evaluator_settings = manager.get_evaluator_settings("configs/evaluator.toml")
            prompt_builder_settings = manager.get_prompt_builder_settings("configs/prompt_builder.toml")

            # Evaluator を初期化
            evaluator = Evaluator(
                settings=evaluator_settings,
                prompt_builder_settings=prompt_builder_settings
            )

            # 評価リクエストを作成
            request = EvaluationRequest(
                user_query="Pythonとは何ですか?",
                submission="Pythonはプログラミング言語です...",
                team_id="team-001",
                config=None,
            )

            # 評価を実行
            result = await evaluator.evaluate(request)
            print(f"Overall score: {result.overall_score}")

        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        settings: EvaluatorSettings,
        prompt_builder_settings: "PromptBuilderSettings",
    ) -> None:
        """設定を使用してEvaluatorを初期化します。

        .. note:: FR-046, FR-047準拠
            EvaluatorSettings を受け取り、内部で EvaluationConfig に変換します。
            設定の生成は呼び出し側の責務です。

        Args:
            settings: Evaluator設定（EvaluatorSettings インスタンス、必須）
            prompt_builder_settings: PromptBuilder設定（必須、Article 9準拠）

        Raises:
            TypeError: settings が指定されていない場合
            ValueError: 設定の検証が失敗した場合
        """
        # FR-047: EvaluatorSettings を EvaluationConfig に変換
        self.config = evaluator_settings_to_evaluation_config(settings)
        self.prompt_builder_settings = prompt_builder_settings

        # 組み込みメトリクスを初期化
        self._builtin_metrics: dict[str, BaseMetric] = {
            "ClarityCoherence": ClarityCoherence(),
            "Coverage": Coverage(),
            "LLMPlain": LLMPlain(),
            "Relevance": Relevance(),
        }

        # カスタムメトリクスレジストリ
        self._custom_metrics: dict[str, BaseMetric] = {}

        # TOML設定からカスタムメトリクスをロード (FR-007)
        if self.config.custom_metrics:
            self._load_custom_metrics_from_config(self.config.custom_metrics)

        # メトリクスディレクトリのパスを保存（動的ロード用）
        self._metrics_dir = Path(__file__).parent / "metrics"

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """設定されたメトリクスを使用してSubmissionを評価します。

        このメソッドは以下を実行します:
        1. 入力を検証(空でないクエリとSubmission)
        2. 使用する設定を決定(カスタムまたはデフォルト)
        3. 各メトリクスを順次評価
        4. 重み付き総合スコアを計算
        5. EvaluationResultを返却

        Args:
            request: クエリ、Submission、およびオプションの設定を含むEvaluationRequest

        Returns:
            個別のメトリクススコアと総合スコアを含むEvaluationResult

        Raises:
            ValueError: 入力が無効な場合(空のクエリ/Submission)
            EvaluatorAPIError: すべてのリトライ後にLLM API呼び出しが失敗した場合
            FileNotFoundError: 設定ファイルが見つからない場合

        Example:
            ```python
            import asyncio
            from mixseek.evaluator import Evaluator
            from mixseek.models.evaluation_request import EvaluationRequest

            async def main():
                evaluator = Evaluator()
                request = EvaluationRequest(
                    user_query="Pythonを説明してください",
                    submission="Pythonは...",
                    team_id="team-001",
                    config=None,
                )
                result = await evaluator.evaluate(request)
                print(f"Overall score: {result.overall_score}")

            asyncio.run(main())
            ```
        """
        # 入力検証 (FR-013) - Pydanticバリデータで既に処理済み
        # 必要に応じて追加チェックをここに追加可能

        # 使用する設定を決定
        config = request.config if request.config else self.config

        # 各メトリクスを順次評価 (FR-014)
        metric_scores = []
        for metric_config in config.metrics:
            metric_name = metric_config.name

            # 適切なメトリクス実装を取得
            metric = self._get_metric(metric_name)

            try:
                # メトリクスの型に応じて適切なパラメータで評価を実行
                if isinstance(metric, LLMJudgeMetric):
                    # このメトリクス用のLLMパラメータを取得（FR-019のフォールバックロジック）
                    model = config.get_model_for_metric(metric_name)
                    temperature = config.get_temperature_for_metric(metric_name)
                    max_tokens = config.get_max_tokens_for_metric(metric_name)
                    max_retries = config.get_max_retries_for_metric(metric_name)
                    system_instruction = config.get_system_instruction_for_metric(metric_name)
                    timeout_seconds = config.get_timeout_seconds_for_metric(metric_name)
                    stop_sequences = config.get_stop_sequences_for_metric(metric_name)
                    top_p = config.get_top_p_for_metric(metric_name)
                    seed = config.get_seed_for_metric(metric_name)
                    # LLM-as-a-Judgeメトリクスの場合はLLMパラメータを渡す (FR-010, FR-019)
                    score = await metric.evaluate(
                        user_query=request.user_query,
                        submission=request.submission,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        max_retries=max_retries,
                        system_instruction=system_instruction,
                        timeout_seconds=timeout_seconds,
                        stop_sequences=stop_sequences,
                        top_p=top_p,
                        seed=seed,
                        prompt_builder_settings=self.prompt_builder_settings,
                    )
                else:
                    # LLM以外のメトリクス（統計ベース等）の場合はuser_query, submissionのみを渡す
                    # BaseMetric.evaluate()は非同期なのでawaitで呼び出す
                    score = await metric.evaluate(
                        user_query=request.user_query,
                        submission=request.submission,
                    )

                metric_scores.append(score)

            except EvaluatorAPIError as e:
                # エラーにメトリクスコンテキストを追加
                e.metric_name = metric_name
                raise

        # 重み付き総合スコアを計算 (FR-004)
        overall_score = self._calculate_overall_score(metric_scores, config)

        # 結果を返却
        return EvaluationResult(metrics=metric_scores, overall_score=overall_score)

    def register_custom_metric(self, name: str, metric: BaseMetric) -> None:
        """カスタム評価メトリクスを登録します。

        カスタムメトリクスはBaseMetricを継承し、evaluate()メソッドを実装する必要があります。
        登録後、評価設定で使用できるようになります。

        Args:
            name: カスタムメトリクスの一意な名前
            metric: BaseMetricサブクラスのインスタンス

        Raises:
            TypeError: メトリクスがBaseMetricを継承していない場合
            ValueError: メトリクスがevaluate()メソッドを実装していない場合

        Example:
            ```python
            # 統計ベースのカスタムメトリクス（LLMを使用しない場合）
            class TechnicalAccuracyMetric(BaseMetric):
                def evaluate(self, user_query, submission):
                    # カスタムロジック
                    return MetricScore(...)

            # LLM-as-a-Judgeベースのカスタムメトリクス
            class CustomLLMMetric(LLMJudgeMetric):
                def get_instruction(self):
                    return "Your custom evaluation instruction..."

            evaluator.register_custom_metric("technical_accuracy", TechnicalAccuracyMetric())
            evaluator.register_custom_metric("custom_llm", CustomLLMMetric())
            ```
        """
        # 検証: BaseMetricを継承する必要がある
        if not isinstance(metric, BaseMetric):
            raise TypeError(
                f"Custom metric must inherit from BaseMetric, got {type(metric).__name__}. "
                "Please ensure your metric class inherits from mixseek.evaluator.metrics.base.BaseMetric"
            )

        # 検証: evaluate()を実装する必要がある
        if not hasattr(metric, "evaluate") or not callable(getattr(metric, "evaluate")):
            raise ValueError(
                f"Custom metric '{name}' must implement evaluate() method. "
                "See BaseMetric interface for method signature."
            )

        # メトリクスを登録
        self._custom_metrics[name] = metric

    def _get_metric(self, metric_name: str) -> BaseMetric:
        """名前によるメトリクス実装の取得（FR-020）。

        クラス名を指定することで評価指標を識別し、src/mixseek/evaluator/metrics/ディレクトリから
        該当クラスを自動的に検索・ロードします。

        検索順序:
        1. カスタムメトリクスレジストリ（register_custom_metricで登録されたもの）
        2. 組み込みメトリクスレジストリ
        3. メトリクスディレクトリから動的にロード

        Args:
            metric_name: メトリクスのクラス名（例："ClarityCoherence", "Coverage", "Relevance"）

        Returns:
            BaseMetricインスタンス

        Raises:
            ValueError: メトリクスが見つからない場合、または無効なメトリクスクラスの場合
        """
        # カスタムメトリクスを先にチェック
        if metric_name in self._custom_metrics:
            return self._custom_metrics[metric_name]

        # 組み込みメトリクスをチェック
        if metric_name in self._builtin_metrics:
            return self._builtin_metrics[metric_name]

        # メトリクスディレクトリから動的にロード（FR-020）
        try:
            metric = self._load_metric_from_directory(metric_name)
            # ロードに成功したら、カスタムメトリクスレジストリに追加
            self._custom_metrics[metric_name] = metric
            return metric
        except Exception as e:
            # 見つからない場合
            available = list(self._builtin_metrics.keys()) + list(self._custom_metrics.keys())
            raise ValueError(
                f"Metric class not found: '{metric_name}'. "
                f"Available metrics: {', '.join(available)}. "
                f"Error during dynamic loading: {e}"
            ) from e

    def _calculate_overall_score(self, metric_scores: list[MetricScore], config: EvaluationConfig) -> float:
        """重み付き総合スコアを計算します。

        Args:
            metric_scores: MetricScoreオブジェクトのリスト
            config: メトリクスの重みを含むEvaluationConfig

        Returns:
            重み付き平均スコア(0-100)

        Raises:
            ValueError: メトリクスの重みが設定に見つからない場合
        """
        total_score = 0.0

        for score in metric_scores:
            # このメトリクスの重みを検索
            weight = next((m.weight for m in config.metrics if m.name == score.metric_name), None)
            if weight is None:
                raise ValueError(f"Weight not found for metric '{score.metric_name}'. ")
            total_score += score.score * weight

        # 小数点以下2桁に丸める
        return round(total_score, 2)

    def _load_custom_metrics_from_config(self, custom_metrics: dict[str, dict[str, Any]]) -> None:
        """TOML設定からカスタムメトリクスを動的にロードします (FR-007)。

        custom_metricsの形式例:
        [custom_metrics]
        technical_accuracy = { module = "myproject.metrics", class = "TechnicalAccuracyMetric" }

        Args:
            custom_metrics: カスタムメトリクス設定の辞書

        Raises:
            ImportError: モジュールまたはクラスのインポートに失敗した場合
            TypeError: クラスがBaseMetricを継承していない場合
        """
        for metric_name, metric_config in custom_metrics.items():
            try:
                # モジュールパスとクラス名を取得
                module_path = metric_config.get("module")
                class_name = metric_config.get("class")

                if not module_path or not class_name:
                    raise ValueError(
                        f"Custom metric '{metric_name}' configuration must include 'module' and 'class' fields. "
                        f"Got: {metric_config}"
                    )

                # Type assertion for mypy
                assert isinstance(module_path, str)
                assert isinstance(class_name, str)

                # モジュールをインポート
                module = importlib.import_module(module_path)

                # クラスを取得
                metric_class = getattr(module, class_name)

                # インスタンス化
                metric_instance = metric_class()

                # BaseMetricを継承しているか検証
                if not isinstance(metric_instance, BaseMetric):
                    raise TypeError(
                        f"Custom metric class '{class_name}' must inherit from BaseMetric. "
                        f"Please ensure {module_path}.{class_name} extends mixseek.evaluator.metrics.base.BaseMetric"
                    )

                # 登録
                self._custom_metrics[metric_name] = metric_instance

            except Exception as e:
                # カスタムメトリクスのロードエラーは警告として扱う（起動は継続）
                logging.warning(
                    f"Failed to load custom metric '{metric_name}' from config: {e}. "
                    f"This metric will not be available for evaluation. "
                    f"Config: {metric_config}"
                )

    def _load_metric_from_directory(self, class_name: str) -> BaseMetric:
        """メトリクスディレクトリからクラス名でメトリクスを動的にロードします（FR-020）。

        src/mixseek/evaluator/metrics/ディレクトリ内のPythonファイルを検索し、
        指定されたクラス名のメトリクスクラスを見つけてインスタンス化します。

        検索対象:
        - ファイル名がsnake_caseで、クラス名がPascalCaseの場合、自動的にマッピング
        - 例: ClarityCoherence → clarity_coherence.py

        Args:
            class_name: ロードするメトリクスクラスの名前（例："ClarityCoherence"）

        Returns:
            BaseMetricインスタンス

        Raises:
            ValueError: クラスが見つからない、または無効なメトリクスクラスの場合
            ImportError: モジュールのインポートに失敗した場合
        """

        # PascalCaseをsnake_caseに変換（ファイル名の推測用）
        # 例: ClarityCoherence → clarity_coherence
        snake_case_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()

        # メトリクスモジュールのパス
        module_path = f"mixseek.evaluator.metrics.{snake_case_name}"

        try:
            # モジュールをインポート
            module = importlib.import_module(module_path)

            # クラスを取得
            if not hasattr(module, class_name):
                raise ValueError(
                    f"Class '{class_name}' not found in module '{module_path}'. "
                    f"Available classes: {[name for name in dir(module) if not name.startswith('_')]}"
                )

            metric_class = getattr(module, class_name)

            # インスタンス化
            metric_instance = metric_class()

            # BaseMetricを継承しているか検証
            if not isinstance(metric_instance, BaseMetric):
                raise TypeError(
                    f"Metric class '{class_name}' must inherit from BaseMetric. "
                    f"Please ensure {module_path}.{class_name} extends mixseek.evaluator.metrics.base.BaseMetric"
                )

            return metric_instance

        except ImportError as e:
            raise ImportError(
                f"Failed to import metric module '{module_path}'. "
                f"Make sure the file '{snake_case_name}.py' exists in src/mixseek/evaluator/metrics/ "
                f"and contains the class '{class_name}'. "
                f"Error: {e}"
            ) from e


if __name__ == "__main__":
    import argparse
    import asyncio

    from mixseek.config.manager import ConfigurationManager
    from mixseek.utils.env import get_workspace_path

    parser = argparse.ArgumentParser(description="Evaluate AI agent submission")
    parser.add_argument("user_query", help="User query string")
    parser.add_argument("submission", help="AI agent submission text")
    parser.add_argument("--team-id", default=None, help="Team ID (optional, default: None)")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace directory path (defaults to MIXSEEK_WORKSPACE env var)",
    )
    parser.add_argument(
        "--evaluator-config",
        type=Path,
        default=None,
        help="Evaluator config file path (defaults to {workspace}/configs/evaluator.toml)",
    )

    args = parser.parse_args()

    # workspace_pathを明示的に取得（Article 9準拠）
    workspace_path = get_workspace_path(cli_arg=args.workspace)

    # ConfigurationManager で Evaluator 設定を読み込み（FR-050準拠）
    manager = ConfigurationManager(workspace=workspace_path)
    evaluator_settings = manager.get_evaluator_settings(args.evaluator_config)
    prompt_builder_settings = manager.get_prompt_builder_settings()

    # FR-046準拠: EvaluatorSettings と PromptBuilderSettings を渡して初期化
    evaluator = Evaluator(
        settings=evaluator_settings,
        prompt_builder_settings=prompt_builder_settings,
    )
    request = EvaluationRequest(
        user_query=args.user_query,
        submission=args.submission,
        team_id=args.team_id,
        config=None,
    )

    result = asyncio.run(evaluator.evaluate(request))

    print(f"Overall Score: {result.overall_score}")
    print("\nMetric Scores:")
    for metric in result.metrics:
        print(f"  {metric.metric_name}: {metric.score}")
        if metric.evaluator_comment:
            print(f"    Comment: {metric.evaluator_comment}")
