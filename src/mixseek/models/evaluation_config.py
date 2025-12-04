"""評価設定モデル。"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from mixseek.config.schema import EvaluatorSettings


class MetricConfig(BaseModel):
    """単一の評価メトリクスの設定。

    このモデルはevaluator.tomlファイルの[[metrics]]セクションに対応します。
    各メトリクスは独自の重みとオプションで独自のLLMモデルを持つことができます。

    Attributes:
        name: メトリクスクラス名（例："ClarityCoherence"、"Coverage"、"Relevance"）（FR-020）
        weight: 重み付き平均計算のためのメトリクスの重み（0.0から1.0）（FR-003）
        model: オプションのLLMモデルオーバーライド（フォーマット："provider:model-name"）（FR-015）
        system_instruction: オプションのsystem_instruction上書き（FR-003, FR-019）
        temperature: オプションのtemperature設定（FR-019）
        max_tokens: オプションのmax_tokens設定（FR-019）
        max_retries: オプションのmax_retries設定（FR-019）
        timeout_seconds: オプションのHTTPタイムアウト（秒）
        stop_sequences: オプションの生成停止シーケンス
        top_p: オプションのTop-pサンプリングパラメータ
        seed: オプションのランダムシード

    Example TOML:
        ```toml
        [[metrics]]
        name = "ClarityCoherence"
        weight = 0.4
        model = "anthropic:claude-sonnet-4-5-20250929"
        system_instruction = "Custom instruction..."
        temperature = 0.0
        max_tokens = 1000
        max_retries = 5
        timeout_seconds = 120
        stop_sequences = ["END", "STOP"]
        top_p = 0.9
        seed = 42
        ```

    Example Python:
        ```python
        from mixseek.models.evaluation_config import MetricConfig

        metric = MetricConfig(
            name="ClarityCoherence",
            weight=0.4,
            model="anthropic:claude-sonnet-4-5-20250929",
            system_instruction="Custom instruction...",
            temperature=0.0
        )
        ```

    Validation Rules:
        - name: 空にできない（メトリクスクラス名）
        - weight: 0.0から1.0の間でなければならない（FR-003）
        - model: 提供する場合は、"provider:model-name"フォーマットでなければならない
        - temperature: 提供する場合は、0.0以上2.0以下でなければならない
        - max_tokens: 提供する場合は、正の整数でなければならない
        - max_retries: 提供する場合は、非負の整数でなければならない
        - timeout_seconds: 提供する場合は、非負の整数でなければならない
        - stop_sequences: 提供する場合は、文字列のリストでなければならない
        - top_p: 提供する場合は、0.0から1.0の間でなければならない
        - seed: 提供する場合は、整数でなければならない
    """

    name: str = Field(
        ...,
        description="メトリクスクラス名（例：'ClarityCoherence'、'Coverage'、'Relevance'）（FR-020）",
        examples=["ClarityCoherence", "Coverage", "Relevance"],
    )

    weight: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="重み付き平均のためのメトリクスの重み（0.0から1.0）。Noneの場合、均等な重みが割り当てられます（FR-003、FR-008）",
        examples=[0.4, 0.3, 0.3],
    )

    model: str | None = Field(
        None,
        description="オプションのLLMモデルオーバーライド（フォーマット：'provider:model-name'）（FR-015）",
        examples=["anthropic:claude-sonnet-4-5-20250929", "openai:gpt-5"],
    )

    system_instruction: str | None = Field(
        None,
        description="オプションのsystem_instruction上書き。指定された場合、デフォルトのプロンプトを置き換える",
        examples=["Evaluate the clarity of the response..."],
    )

    temperature: float | None = Field(
        None,
        ge=0.0,
        description="オプションのLLM temperature設定（FR-019）",
        examples=[0.0, 0.5, 1.0],
    )

    max_tokens: int | None = Field(
        None,
        gt=0,
        description="オプションのLLM max_tokens設定（FR-019）",
        examples=[1000, 2000, 4000],
    )

    max_retries: int | None = Field(
        None,
        ge=0,
        description="オプションのLLM API呼び出しの最大リトライ試行回数（FR-019）",
        examples=[3, 5, 10],
    )

    timeout_seconds: int | None = Field(
        None,
        ge=0,
        description="オプションのHTTPタイムアウト（秒）",
        examples=[60, 120, 300],
    )

    stop_sequences: list[str] | None = Field(
        None,
        description="オプションの生成を停止するシーケンスのリスト",
        examples=[["END", "STOP"], ["\n\n"]],
    )

    top_p: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="オプションのTop-pサンプリングパラメータ（Noneの場合はモデルのデフォルト値）",
        examples=[0.9, 0.95, 1.0],
    )

    seed: int | None = Field(
        None,
        description="オプションのランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
        examples=[42, 12345],
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """メトリクス名が空でないことを検証します。"""
        if not v or not v.strip():
            raise ValueError("Metric name cannot be empty")
        return v.strip()

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        """モデルフォーマットが'provider:model-name'であることを検証します。

        Raises:
            ValueError: モデルフォーマットが無効な場合
        """
        if v is not None:
            if ":" not in v:
                raise ValueError(
                    f"Invalid model format: '{v}'. "
                    "Expected format: 'provider:model-name' "
                    "(e.g., 'anthropic:claude-sonnet-4-5-20250929', 'openai:gpt-5')"
                )

            provider, model_name = v.split(":", 1)
            if not provider or not model_name:
                raise ValueError(f"Invalid model format: '{v}'. Both provider and model name must be non-empty.")

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "ClarityCoherence",
                    "weight": 0.4,
                    "model": "anthropic:claude-sonnet-4-5-20250929",
                    "system_instruction": "Custom instruction...",
                    "temperature": 0.0,
                    "max_tokens": 1000,
                    "max_retries": 5,
                    "timeout_seconds": 120,
                    "stop_sequences": ["END", "STOP"],
                    "top_p": 0.9,
                    "seed": 42,
                },
                {
                    "name": "Coverage",
                    "weight": 0.3,
                    "model": None,  # default_modelを使用
                },
            ]
        }
    }


class LLMDefaultConfig(BaseModel):
    """グローバルなLLMデフォルト設定。

    このモデルはevaluator.tomlファイルの[llm_default]セクションに対応します。
    各パラメータは、メトリクスレベルで指定されていない場合のデフォルト値として使用されます。

    全てのフィールドにハードコードされたデフォルト値が設定されており、
    TOMLファイルで明示的に指定しない場合はこれらの値が使用されます（FR-019）。

    Attributes:
        model: デフォルトLLMモデル（デフォルト: "google-gla:gemini-2.5-flash"）（FR-019）
        temperature: デフォルトtemperature設定（デフォルト: 0.0）（FR-019）
        max_tokens: デフォルトmax_tokens設定（デフォルト: None=制限なし）（FR-019）
        max_retries: デフォルトmax_retries設定（デフォルト: 3）（FR-019）
        timeout_seconds: デフォルトHTTPタイムアウト（秒）（デフォルト: 300）
        stop_sequences: デフォルト生成停止シーケンス（デフォルト: None）
        top_p: デフォルトTop-pサンプリングパラメータ（デフォルト: None）
        seed: デフォルトランダムシード（デフォルト: None）

    Example TOML:
        ```toml
        [llm_default]
        model = "anthropic:claude-sonnet-4-5-20250929"
        temperature = 0.0
        max_tokens = 2000
        max_retries = 3
        timeout_seconds = 300
        stop_sequences = ["END", "STOP"]
        top_p = 0.9
        seed = 42
        ```

    Example Python:
        ```python
        from mixseek.models.evaluation_config import LLMDefaultConfig

        # デフォルト値を使用
        defaults = LLMDefaultConfig()

        # 一部を上書き
        defaults = LLMDefaultConfig(
            temperature=0.5,
            max_tokens=2000
        )
        ```

    Validation Rules:
        - model: "provider:model-name"フォーマットでなければならない
        - temperature: 0.0以上でなければならない
        - max_tokens: 提供する場合は、正の整数でなければならない
        - max_retries: 非負の整数でなければならない
        - timeout_seconds: 提供する場合は、非負の整数でなければならない
        - stop_sequences: 提供する場合は、文字列のリストでなければならない
        - top_p: 提供する場合は、0.0から1.0の間でなければならない
        - seed: 提供する場合は、整数でなければならない
    """

    model: str = Field(
        default="google-gla:gemini-2.5-flash",
        description="デフォルトLLMモデル（フォーマット：'provider:model-name'）（FR-019）",
        examples=["anthropic:claude-sonnet-4-5-20250929", "openai:gpt-5"],
    )

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        description="デフォルトLLM temperature設定（FR-019）",
        examples=[0.0, 0.5, 1.0],
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="デフォルトLLM max_tokens設定（FR-019）",
        examples=[1000, 2000, 4000],
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="デフォルトLLM API呼び出しの最大リトライ試行回数（FR-019）",
        examples=[3, 5, 10],
    )

    timeout_seconds: int | None = Field(
        default=None,
        ge=0,
        description="デフォルトHTTPタイムアウト（秒）",
        examples=[60, 120, 300],
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="デフォルト生成を停止するシーケンスのリスト",
        examples=[["END", "STOP"], ["\n\n"]],
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="デフォルトTop-pサンプリングパラメータ（Noneの場合はモデルのデフォルト値）",
        examples=[0.9, 0.95, 1.0],
    )

    seed: int | None = Field(
        default=None,
        description="デフォルトランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
        examples=[42, 12345],
    )

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        """モデルフォーマットが'provider:model-name'であることを検証します。

        Raises:
            ValueError: モデルフォーマットが無効な場合
        """
        if ":" not in v:
            raise ValueError(
                f"Invalid model format: '{v}'. "
                "Expected format: 'provider:model-name' "
                "(e.g., 'anthropic:claude-sonnet-4-5-20250929', 'openai:gpt-5')"
            )

        provider, model_name = v.split(":", 1)
        if not provider or not model_name:
            raise ValueError(f"Invalid model format: '{v}'. Both provider and model name must be non-empty.")

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model": "anthropic:claude-sonnet-4-5-20250929",
                    "temperature": 0.0,
                    "max_tokens": 2000,
                    "max_retries": 3,
                    "timeout_seconds": 300,
                    "stop_sequences": ["END", "STOP"],
                    "top_p": 0.9,
                    "seed": 42,
                }
            ]
        }
    }


class EvaluationConfig(BaseModel):
    """{workspace}/configs/evaluator.tomlから読み込まれるグローバル評価設定。

    このモデルは、デフォルトのLLMモデル、リトライ設定、すべてのメトリクス設定を
    含む完全な評価器設定を表します。

    Attributes:
        llm_default: [llm_default]セクションのデフォルトLLM設定（FR-019）
        metrics: メトリクス設定のリスト
        metric_weights: メトリクス名を重みにマッピングする辞書（メトリクスリストから派生）
        enabled_metrics: 有効なメトリクス名のリスト（メトリクスリストから派生）
        custom_metrics: カスタムメトリクス設定のオプションの辞書

    Example TOML:
        ```toml
        [llm_default]
        model = "anthropic:claude-sonnet-4-5-20250929"
        temperature = 0.0
        max_tokens = 2000
        max_retries = 3

        [[metrics]]
        name = "ClarityCoherence"
        weight = 0.334

        [[metrics]]
        name = "Coverage"
        weight = 0.333

        [[metrics]]
        name = "Relevance"
        weight = 0.333

        [custom_metrics]
        # オプション：カスタムメトリクス設定
        ```

    Example Python:
        ```python
        from pathlib import Path
        from mixseek.models.evaluation_config import EvaluationConfig

        workspace = Path("/path/to/workspace")
        config = EvaluationConfig.from_toml_file(workspace)

        print(f"Default model: {config.get_model_for_metric('ClarityCoherence')}")
        print(f"Metrics: {len(config.metrics)}")
        ```

    Validation Rules:
        - metrics: 少なくとも1つのメトリクスを含む必要がある
        - metric weights: 均等な重みフォールバック後、1.0（±0.001許容範囲）に合計する必要がある（FR-008、FR-009）
        - metric names: 一意でなければならない
    """

    llm_default: LLMDefaultConfig = Field(
        default_factory=LLMDefaultConfig,
        description="[llm_default]セクションのデフォルトLLM設定（FR-019）",
    )

    metrics: list[MetricConfig] = Field(..., description="メトリクス設定のリスト（FR-003）", min_length=1)

    # 検証中に設定される派生フィールド
    metric_weights: dict[str, float] = Field(
        default_factory=dict,
        description="メトリクス名を重みにマッピングする辞書（メトリクスリストから派生）",
    )

    enabled_metrics: list[str] = Field(
        default_factory=list,
        description="有効なメトリクス名のリスト（メトリクスリストから派生）",
    )

    custom_metrics: dict[str, dict[str, Any]] | None = Field(
        None,
        description="カスタムメトリクス設定のオプションの辞書（FR-007）",
    )

    @model_validator(mode="after")
    def apply_equal_weights_if_needed(self) -> "EvaluationConfig":
        """重みが指定されていない場合、メトリクスに均等な重みを適用します（FR-008）。

        すべてのメトリクスの重みがNoneの場合、均等な重みを割り当てます。
        一部の重みがNoneで一部が設定されている場合、エラーを発生させます。
        また、metric_weights辞書とenabled_metricsリストを設定します。

        Raises:
            ValueError: 一部の重みがNoneで一部が設定されている場合、または処理後に重みが1.0に合計しない場合
        """
        # Noneの重みをカウント
        none_count = sum(1 for m in self.metrics if m.weight is None)

        if none_count == len(self.metrics):
            # すべての重みがNone → 均等な重みを適用（FR-008）
            equal_weight = 1.0 / len(self.metrics)
            for metric in self.metrics:
                metric.weight = equal_weight
        elif none_count > 0:
            # 一部がNoneで一部が設定されている → エラー
            none_metrics = [m.name for m in self.metrics if m.weight is None]
            set_metrics = [m.name for m in self.metrics if m.weight is not None]
            raise ValueError(
                f"すべてのメトリクスの重みを指定するか、すべて未指定にしてください。"
                f"重みが未指定: {', '.join(none_metrics)}。"
                f"重みが設定済み: {', '.join(set_metrics)}。"
            )

        # すべての重みが1.0に合計することを検証（FR-009）
        # この時点で、すべての重みは非Noneであるべき
        total_weight = sum(metric.weight for metric in self.metrics)  # type: ignore

        if not (0.999 <= total_weight <= 1.001):
            weight_details = ", ".join(f"{m.name}={m.weight}" for m in self.metrics)
            raise ValueError(
                f"Metric weights must sum to 1.0, got: {total_weight:.4f}. "
                f"Current weights: {weight_details}. "
                "Please adjust the weights in your configuration file."
            )

        # 派生フィールドを設定
        self.metric_weights = {m.name: m.weight for m in self.metrics}  # type: ignore
        self.enabled_metrics = [m.name for m in self.metrics]

        return self

    @model_validator(mode="after")
    def validate_unique_metric_names(self) -> "EvaluationConfig":
        """すべてのメトリクス名が一意であることを検証します。

        Raises:
            ValueError: 重複するメトリクス名が見つかった場合
        """
        names = [metric.name for metric in self.metrics]
        duplicates = [name for name in names if names.count(name) > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate metric names found: {', '.join(set(duplicates))}. Each metric must have a unique name."
            )

        return self

    @classmethod
    def from_toml_file(cls, workspace_path: Path) -> "EvaluationConfig":
        """TOMLファイルから設定を読み込みます。

        .. note:: T080移行完了
            内部実装は新しいConfigurationManager.load_evaluation_settings()を使用しています。
            外部APIは完全に後方互換性を維持しています。

        Args:
            workspace_path: ワークスペースルートディレクトリへのパス

        Returns:
            検証されたEvaluationConfigインスタンス

        Raises:
            FileNotFoundError: evaluator.tomlが存在しない場合
            ValueError: TOMLが無効または検証が失敗した場合

        Example:
            ```python
            from pathlib import Path
            config = EvaluationConfig.from_toml_file(Path("/workspace"))
            ```
        """
        # T080移行: 新しいConfigurationManagerを使用
        from mixseek.config.manager import ConfigurationManager

        config_file = workspace_path / "configs" / "evaluator.toml"

        if not config_file.exists():
            raise FileNotFoundError(
                f"Evaluator configuration not found: {config_file}\n"
                f"Please create {config_file} with your evaluation settings.\n"
                "See documentation for example configuration."
            )

        # 新しいConfigurationManagerで読み込み（トレース付き）
        manager = ConfigurationManager(workspace=workspace_path)
        evaluator_settings = manager.load_evaluation_settings(config_file)

        # 新しいEvaluatorSettingsを古いEvaluationConfigに変換（後方互換性）
        return evaluator_settings_to_evaluation_config(evaluator_settings)

    def _get_metric_config(self, metric_name: str) -> MetricConfig:
        """メトリクス名からMetricConfigを取得します。

        Args:
            metric_name: メトリクスの名前

        Returns:
            MetricConfigオブジェクト

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        for metric in self.metrics:
            if metric.name == metric_name:
                return metric

        raise ValueError(
            f"Metric not found: {metric_name}. Available metrics: {', '.join(m.name for m in self.metrics)}"
        )

    def get_model_for_metric(self, metric_name: str) -> str:
        """特定のメトリクスのLLMモデルを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのmodel設定
        2. [llm_default]のmodel設定（デフォルト: "anthropic:claude-sonnet-4-5-20250929"）

        Args:
            metric_name: メトリクスの名前

        Returns:
            "provider:model-name"フォーマットのモデル識別子

        Raises:
            ValueError: 設定でメトリクスが見つからない場合

        Example:
            ```python
            config = EvaluationConfig.from_toml_file(workspace)
            clarity_coherence_model = config.get_model_for_metric("ClarityCoherence")
            ```
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        # メトリクスレベルで設定されていればそれを使用、なければllm_defaultの値を使用
        return metric.model if metric.model is not None else self.llm_default.model

    def get_temperature_for_metric(self, metric_name: str) -> float:
        """特定のメトリクスのtemperatureを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのtemperature設定
        2. [llm_default]のtemperature設定（デフォルト: 0.0）

        Args:
            metric_name: メトリクスの名前

        Returns:
            temperature値

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.temperature if metric.temperature is not None else self.llm_default.temperature

    def get_max_tokens_for_metric(self, metric_name: str) -> int | None:
        """特定のメトリクスのmax_tokensを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのmax_tokens設定
        2. [llm_default]のmax_tokens設定（デフォルト: None=制限なし）

        Args:
            metric_name: メトリクスの名前

        Returns:
            max_tokens値、またはNone（制限なし）

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.max_tokens if metric.max_tokens is not None else self.llm_default.max_tokens

    def get_max_retries_for_metric(self, metric_name: str) -> int:
        """特定のメトリクスのmax_retriesを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのmax_retries設定
        2. [llm_default]のmax_retries設定（デフォルト: 3）

        Args:
            metric_name: メトリクスの名前

        Returns:
            max_retries値

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.max_retries if metric.max_retries is not None else self.llm_default.max_retries

    def get_system_instruction_for_metric(self, metric_name: str) -> str | None:
        """特定のメトリクスのsystem_instructionを取得します（FR-019のフォールバックロジック）。

        注意: system_instructionは、メトリクスレベルでのみ設定可能です。
        [llm_default]セクションにはsystem_instructionフィールドはありません。
        Noneが返された場合、各メトリクス実装のデフォルトプロンプトが使用されます。

        Args:
            metric_name: メトリクスの名前

        Returns:
            system_instruction文字列、またはNone（メトリクスのデフォルトを使用）

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # system_instructionはメトリクスレベルでのみ設定可能（FR-019）
        return metric.system_instruction

    def get_timeout_seconds_for_metric(self, metric_name: str) -> int | None:
        """特定のメトリクスのtimeout_secondsを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのtimeout_seconds設定
        2. [llm_default]のtimeout_seconds設定（デフォルト: None）

        Args:
            metric_name: メトリクスの名前

        Returns:
            timeout_seconds値、またはNone

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.timeout_seconds if metric.timeout_seconds is not None else self.llm_default.timeout_seconds

    def get_stop_sequences_for_metric(self, metric_name: str) -> list[str] | None:
        """特定のメトリクスのstop_sequencesを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのstop_sequences設定
        2. [llm_default]のstop_sequences設定（デフォルト: None）

        Args:
            metric_name: メトリクスの名前

        Returns:
            stop_sequencesリスト、またはNone

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.stop_sequences if metric.stop_sequences is not None else self.llm_default.stop_sequences

    def get_top_p_for_metric(self, metric_name: str) -> float | None:
        """特定のメトリクスのtop_pを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのtop_p設定
        2. [llm_default]のtop_p設定（デフォルト: None）

        Args:
            metric_name: メトリクスの名前

        Returns:
            top_p値、またはNone

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.top_p if metric.top_p is not None else self.llm_default.top_p

    def get_seed_for_metric(self, metric_name: str) -> int | None:
        """特定のメトリクスのseedを取得します（FR-019のフォールバックロジック）。

        フォールバック階層:
        1. メトリクスレベルのseed設定
        2. [llm_default]のseed設定（デフォルト: None）

        Args:
            metric_name: メトリクスの名前

        Returns:
            seed値、またはNone

        Raises:
            ValueError: 設定でメトリクスが見つからない場合
        """
        metric = self._get_metric_config(metric_name)

        # フォールバック階層（FR-019）
        return metric.seed if metric.seed is not None else self.llm_default.seed

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "llm_default": {
                        "model": "anthropic:claude-sonnet-4-5-20250929",
                        "temperature": 0.0,
                        "max_tokens": 2000,
                        "max_retries": 3,
                        "timeout_seconds": 300,
                        "stop_sequences": ["END", "STOP"],
                        "top_p": 0.9,
                        "seed": 42,
                    },
                    "metrics": [
                        {"name": "ClarityCoherence", "weight": 0.4, "model": None},
                        {"name": "Coverage", "weight": 0.3, "model": None},
                        {"name": "Relevance", "weight": 0.3, "model": "openai:gpt-5"},
                    ],
                }
            ]
        }
    }


def evaluator_settings_to_evaluation_config(
    evaluator_settings: "EvaluatorSettings",
) -> EvaluationConfig:
    """EvaluatorSettings（新）をEvaluationConfig（旧）に変換（T080移行ヘルパー）。

    この関数は新しい設定システム（EvaluatorSettings）から
    既存のAPIとの互換性のために旧形式（EvaluationConfig）に変換します。

    Args:
        evaluator_settings: EvaluatorSettingsインスタンス（T080拡張版）

    Returns:
        EvaluationConfigインスタンス（完全な検証済み）

    Example:
        >>> from mixseek.config.manager import ConfigurationManager
        >>> from mixseek.models.evaluation_config import evaluator_settings_to_evaluation_config
        >>> from pathlib import Path
        >>>
        >>> manager = ConfigurationManager(workspace=Path.cwd())
        >>> evaluator_settings = manager.get_evaluator_settings("configs/evaluator.toml")
        >>> evaluation_config = evaluator_settings_to_evaluation_config(evaluator_settings)
        >>> print(evaluation_config.llm_default.model)
        'anthropic:claude-sonnet-4-5-20250929'
    """
    # LLMDefaultConfigの構築（llm_default相当のフィールドから）
    llm_default = LLMDefaultConfig(
        model=evaluator_settings.default_model,
        temperature=evaluator_settings.temperature if evaluator_settings.temperature is not None else 0.0,
        max_tokens=evaluator_settings.max_tokens,
        max_retries=evaluator_settings.max_retries,
        timeout_seconds=evaluator_settings.timeout_seconds,
        stop_sequences=evaluator_settings.stop_sequences,
        top_p=evaluator_settings.top_p,
        seed=evaluator_settings.seed,
    )

    # metrics配列をlist[dict[str, Any]]からlist[MetricConfig]に変換
    metric_configs: list[MetricConfig] = []
    for metric_dict in evaluator_settings.metrics:
        # dict[str, Any]をMetricConfigに変換
        metric_configs.append(MetricConfig.model_validate(metric_dict))

    # EvaluationConfigを構築（バリデーション付き）
    evaluation_config = EvaluationConfig(
        llm_default=llm_default,
        metrics=metric_configs,
        custom_metrics=evaluator_settings.custom_metrics if evaluator_settings.custom_metrics else None,
    )

    return evaluation_config
