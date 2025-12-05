"""Configuration schemas based on Pydantic Settings."""

import contextvars
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

from mixseek.models.member_agent import PluginMetadata, ToolSettings

from .mixins import WorkspaceValidatorMixin
from .sources.toml_source import CustomTomlConfigSettingsSource
from .sources.tracing_source import SourceTrace
from .validators_common import validate_model_format

# Phase 2: トレースストレージをcontext varsで管理（スレッド安全性確保）
_trace_storage_context: contextvars.ContextVar[dict[str, SourceTrace] | None] = contextvars.ContextVar(
    "_trace_storage_context", default=None
)


class MappedEnvSettingsSource(EnvSettingsSource):
    """環境変数ソースで公式環境変数を内部フィールド名にマッピング。

    os.environを変更せず、__call__時にマッピングを行います（テスト間の干渉を防止）。

    設計思想:
      - ユーザー向けAPI: MIXSEEK_WORKSPACE, MIXSEEK_UI__WORKSPACE (公式環境変数)
      - 内部Pydanticフィールド: workspace_path (実装詳細)
    """

    def __init__(self, settings_cls: type[BaseSettings], case_sensitive: bool | None = None) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス
            case_sensitive: 大文字小文字を区別するか
        """
        super().__init__(settings_cls, case_sensitive=case_sensitive)
        self.settings_cls_name = settings_cls.__name__

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールド値を取得（マッピング適用）。

        Article 10（DRY原則）準拠：条件分岐をStrategy Patternで置き換え。
        Article 11（Refactoring Policy）準拠：既存クラスを直接改善。

        Returns:
            環境変数から読み込んだ値の辞書
        """
        # 親クラスから通常の環境変数を取得
        data = super().__call__()

        # ファクトリーからマッパーを取得してマッピング適用
        from mixseek.config.env_mappers import EnvMapperFactory

        mapper = EnvMapperFactory.get_mapper(self.settings_cls_name)
        if mapper:
            data = mapper.map(data)

        return data


class MappedDotEnvSettingsSource(DotEnvSettingsSource):
    """DotEnvソースで公式環境変数を内部フィールド名にマッピング。

    MappedEnvSettingsSourceと同様に、.envファイルからの読み込み時に
    マッピングを適用します（Issue #251対応）。

    設計思想:
      - ユーザー向けAPI: MIXSEEK_WORKSPACE, MIXSEEK_UI__WORKSPACE (公式環境変数)
      - 内部Pydanticフィールド: workspace_path (実装詳細)
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        env_file: str | None = ".env",
        env_file_encoding: str | None = "utf-8",
        case_sensitive: bool | None = None,
        env_prefix: str | None = None,
        env_nested_delimiter: str | None = None,
    ) -> None:
        """初期化。

        Args:
            settings_cls: 設定クラス
            env_file: .envファイルパス
            env_file_encoding: ファイルエンコーディング
            case_sensitive: 大文字小文字を区別するか
            env_prefix: 環境変数プレフィックス
            env_nested_delimiter: ネスト区切り文字
        """
        super().__init__(
            settings_cls,
            env_file=env_file,
            env_file_encoding=env_file_encoding,
            case_sensitive=case_sensitive,
            env_prefix=env_prefix,
            env_nested_delimiter=env_nested_delimiter,
        )
        self.settings_cls_name = settings_cls.__name__

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールド値を取得（マッピング適用）。

        Returns:
            .envファイルから読み込んだ値の辞書（マッピング適用済み）
        """
        # 親クラスから.envファイルの値を取得
        data = super().__call__()

        # 設定クラスのフィールド名でフィルタリング（extra="forbid"対策, Issue #2）
        # DotEnvSettingsSourceは.envファイルの全変数を返すため、
        # 設定クラスに定義されているフィールド名またはマッパーの既知キーのみを保持する
        valid_field_names = set(self.settings_cls.model_fields.keys())
        # マッパーの既知キーも追加（workspace → workspace_path へのマッピング用）
        from mixseek.config.env_mappers import EnvMapperFactory

        mapper = EnvMapperFactory.get_mapper(self.settings_cls_name)
        if mapper and hasattr(mapper, "_SOURCE_KEYS"):
            valid_field_names.update(mapper._SOURCE_KEYS)
        # フィルタリング実行
        data = {k: v for k, v in data.items() if k.lower() in valid_field_names}

        # case_sensitive設定を取得（Noneの場合はmodel_configから）
        case_sensitive = self.case_sensitive
        if case_sensitive is None:
            case_sensitive = self.settings_cls.model_config.get("case_sensitive", False)

        # case_sensitive=Falseの場合、キーを小文字に変換
        # mapper.map()は小文字キー（例: mixseek_workspace）を期待している
        if not case_sensitive:
            data = {k.lower(): v for k, v in data.items()}

        # マッパーでマッピング適用（mapperは上でフィルタリング用に既に取得済み）
        # Note: マッパーがソースキーのクリーンアップも担当（extra="forbid"対策）
        if mapper:
            data = mapper.map(data)
        else:
            # マッパーがない場合でも、既知のworkspace関連キーをクリーンアップ
            # （extra="forbid"対策：未登録クラスでも不要キーを除去）
            fallback_cleanup_keys = ("workspace", "mixseek_workspace", "ui__workspace", "mixseek_ui__workspace")
            for key in fallback_cleanup_keys:
                data.pop(key, None)

        return data


class MixSeekBaseSettings(BaseSettings):
    """mixseek-core設定のベースクラス。

    すべての設定スキーマはこのクラスを継承します。
    トレーサビリティ機能と統一的な設定ソースの優先順位を提供します。

    Note:
        トレース情報はインスタンス属性 __source_traces__ として保存されます。
        ConfigurationManager.load_settings() および _load_settings_with_tracing()
        メソッドで自動的に添付されます（Phase 2: 選択肢B実装）。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # 環境識別
    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev",
        description="実行環境",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """設定ソースのカスタマイズ（Phase 2: 選択肢B実装 + トレーシング復活）。

        優先順位: init (CLI) > ENV > dotenv > TOML > secrets > default

        Note:
            トレース機能は context vars で管理され、インスタンス属性として保存されます。
            これによりスレッド安全性を確保します。

        Args:
            settings_cls: 設定クラス
            init_settings: 初期化設定（CLI引数など）
            env_settings: 環境変数設定
            dotenv_settings: .env ファイル設定
            file_secret_settings: シークレット設定

        Returns:
            ソースのタプル
        """
        # T097: config_fileパス決定（Article 9準拠）
        # 優先順位: ConfigurationManager渡し値 > MIXSEEK_CONFIG_FILE環境変数
        # contextvarsを使用し、並行処理・ネストされた呼び出しでも安全
        from mixseek.config.manager import _config_file_context

        from .sources.tracing_source import TracingSourceWrapper

        config_file_path = _config_file_context.get()
        if config_file_path is None:
            # 後方互換性: 環境変数フォールバック（ConfigurationManager経由でない直接呼び出し時）
            config_file_env = os.environ.get("MIXSEEK_CONFIG_FILE")
            config_file_path = Path(config_file_env) if config_file_env else None

        # トレースストレージを初期化（context varsで管理）
        # Phase 2-4修正: 既存のtrace_storageがある場合は再利用（_load_settings_with_tracing()との整合性）
        trace_storage = _trace_storage_context.get()
        if trace_storage is None:
            trace_storage = {}
            _trace_storage_context.set(trace_storage)

        # CLI引数（init_settings）をトレーシングでラップ
        traced_init_settings = TracingSourceWrapper(
            settings_cls,
            init_settings,
            source_name="CLI",
            source_type="cli",
            trace_storage=trace_storage,
        )

        # MappedEnvSettingsSourceを使用（os.environを変更せず、読み取り時にマッピング）
        # これによりテスト間の干渉を防ぎます
        env_settings = MappedEnvSettingsSource(settings_cls)

        # トレーシングでラップ
        traced_env_settings = TracingSourceWrapper(
            settings_cls,
            env_settings,
            source_name="environment_variables",
            source_type="env",
            trace_storage=trace_storage,
        )

        # MappedDotEnvSettingsSourceを使用（.envファイルからの読み込み時にマッピング適用）
        # Issue #251対応: dotenv_settings引数は使用せず、マッピング適用版を作成
        env_file_config = settings_cls.model_config.get("env_file", ".env")
        env_file_str = str(env_file_config) if env_file_config is not None else None
        dotenv_source = MappedDotEnvSettingsSource(
            settings_cls,
            env_file=env_file_str,
            env_file_encoding=settings_cls.model_config.get("env_file_encoding", "utf-8"),
            case_sensitive=settings_cls.model_config.get("case_sensitive", False),
            env_prefix=settings_cls.model_config.get("env_prefix", ""),
            env_nested_delimiter=settings_cls.model_config.get("env_nested_delimiter", "__"),
        )

        # トレーシングでラップ
        traced_dotenv_settings = TracingSourceWrapper(
            settings_cls,
            dotenv_source,
            source_name=".env",
            source_type="dotenv",
            trace_storage=trace_storage,
        )

        # TOML ファイルソースを準備（カスタム実装）
        toml_source = CustomTomlConfigSettingsSource(settings_cls, config_file_path=config_file_path)

        # トレーシングでラップ
        traced_toml_source = TracingSourceWrapper(
            settings_cls,
            toml_source,
            source_name="TOML",
            source_type="toml",
            trace_storage=trace_storage,
        )

        # 優先順位の高い順に列挙する
        sources = [
            traced_init_settings,
            traced_env_settings,
            traced_dotenv_settings,
            traced_toml_source,
            file_secret_settings,
        ]

        return tuple(sources)

    def model_post_init(self, __context: Any) -> None:
        """Pydantic初期化後の処理（トレースストレージをインスタンス属性にコピー）。

        Phase 2: context varsからトレースストレージを取得し、インスタンス属性として保存。
        これによりスレッド安全性を確保します。

        Args:
            __context: Pydantic内部コンテキスト（未使用）
        """
        # context varsからトレースストレージを取得
        trace_storage = _trace_storage_context.get()

        # インスタンス属性として保存（取り出し可能にする）
        if trace_storage is not None:
            object.__setattr__(self, "__source_traces__", trace_storage)

    def get_trace_info(self, field_name: str) -> SourceTrace | None:
        """フィールドのトレース情報を取得（Phase 2: インスタンスメソッド）。

        Args:
            field_name: フィールド名

        Returns:
            トレース情報（存在しない場合はNone）

        Note:
            トレース情報はインスタンス属性 __source_traces__ として保存されます。
            ConfigurationManager._load_settings_with_tracing()で設定されます。
        """
        traces: dict[str, SourceTrace] = getattr(self, "__source_traces__", {})
        return traces.get(field_name)


class LeaderAgentSettings(MixSeekBaseSettings):
    """Leader Agent用の設定スキーマ（T092完全実装版）。

    LLMモデル、タイムアウト、温度パラメータ、システムプロンプトなどを管理します。
    レガシーのLeaderAgentConfigの全機能を継承します。
    すべての環境（dev/staging/prod）でデフォルト値は同一です（FR-007準拠）。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_LEADER__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # システムプロンプト設定
    system_instruction: str | None = Field(
        default=None,
        description="システム指示（Pydantic AIのinstructions）",
    )

    system_prompt: str | None = Field(
        default=None,
        description="システムプロンプト（Pydantic AIのsystem_prompt、高度な利用者向け）",
    )

    # LLM設定（オプション、すべての環境で同じデフォルト値）
    model: str = Field(
        default="google-gla:gemini-2.5-flash-lite",
        description="LLMモデル (例: google-gla:gemini-2.5-flash-lite)",
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Temperature (Noneの場合はモデルのデフォルト値)",
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="最大トークン数 (Noneの場合はLLM側のデフォルト値)",
    )

    timeout_seconds: int = Field(
        default=300,
        ge=0,
        description="HTTPタイムアウト（秒、デフォルト: 300秒 / 5分）",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="LLM API呼び出しの最大リトライ回数",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="停止シーケンス（オプション）",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-pサンプリング (Noneの場合はLLM側のデフォルト値)",
    )

    seed: int | None = Field(
        default=None,
        description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
    )

    @field_validator("system_instruction")
    @classmethod
    def validate_system_instruction(cls, v: str | None) -> str | None:
        """system_instructionのバリデーション（レガシー互換）。

        Args:
            v: system_instruction文字列

        Returns:
            バリデーション済みのsystem_instruction

        Warnings:
            空白のみの場合は警告を出す
        """
        import warnings

        if v is None:
            return None
        if v == "":
            return ""
        if not v.strip():
            warnings.warn(
                "system_instruction is whitespace-only. Treating it as empty string.",
                UserWarning,
                stacklevel=2,
            )
            return ""
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """モデル形式のバリデーション（FR-007準拠：環境別分岐なし）。

        Note:
            共通関数 validate_model_format() を使用（Article 10: DRY原則準拠）

        Args:
            v: モデル形式文字列

        Returns:
            バリデーション済みのモデル形式

        Raises:
            ValueError: 形式が不正な場合
        """
        return validate_model_format(v, allow_empty=False)


class MemberAgentSettings(MixSeekBaseSettings):
    """Member Agent用の設定スキーマ（T093完全実装版）。

    複数のMember AgentのLLM設定とAgent固有の設定を管理します。
    レガシーのTeamMemberAgentConfigの全機能を継承します。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_MEMBER__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # Agent基本設定
    agent_name: str = Field(
        description="Agent名",
    )

    agent_type: str = Field(
        description="Agent種別（web_search, code_analyzer等）",
    )

    tool_name: str | None = Field(
        default=None,
        description="Tool名（Noneの場合は delegate_to_{agent_name} を使用）",
    )

    tool_description: str = Field(
        description="Tool説明",
    )

    # システムプロンプト設定
    system_instruction: str | None = Field(
        default=None,
        description="システム指示（Noneの場合はデフォルト指示を自動適用）",
    )

    system_prompt: str | None = Field(
        default=None,
        description="システムプロンプト（Pydantic AIのsystem_prompt、system_instructionと併用可能）",
    )

    # LLM設定
    model: str = Field(
        description="LLMモデル (例: anthropic:claude-sonnet-4-5)",
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Temperature (Noneの場合はモデルのデフォルト値)",
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="最大トークン数 (Noneの場合はLLM側のデフォルト値)",
    )

    timeout_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Agent実行タイムアウト（秒）",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="LLM API呼び出しの最大リトライ回数",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="停止シーケンス（オプション）",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-pサンプリング (Noneの場合はLLM側のデフォルト値)",
    )

    seed: int | None = Field(
        default=None,
        description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
    )

    # Custom Agent設定（Issue #146対応）
    plugin: "PluginMetadata | None" = Field(
        default=None,
        description="Plugin設定（custom agent用、Noneの場合は標準エージェント）",
    )

    tool_settings: "ToolSettings | None" = Field(
        default=None,
        description="Tool固有設定（web_search、code_execution等のツール設定）",
    )

    # カスタムプラグイン用のメタデータ（予約語）
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="追加のメタデータ（カスタムプラグインで利用可能）",
    )

    @field_validator("tool_description")
    @classmethod
    def validate_tool_description(cls, v: str) -> str:
        """tool_descriptionのバリデーション（レガシー互換）。

        Args:
            v: tool_description文字列

        Returns:
            バリデーション済みのtool_description

        Raises:
            ValueError: 空文字列の場合
        """
        if not v.strip():
            raise ValueError("tool_description cannot be empty")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """モデル形式のバリデーション。

        Note:
            共通関数 validate_model_format() を使用（Article 10: DRY原則準拠）
            空文字列を許容（allow_empty=True）

        Args:
            v: モデル形式文字列

        Returns:
            バリデーション済みのモデル形式

        Raises:
            ValueError: 形式が不正な場合
        """
        return validate_model_format(v, allow_empty=True)

    def get_tool_name(self) -> str:
        """Tool名を取得（レガシー互換メソッド）。

        Returns:
            Tool名（未設定の場合は delegate_to_{agent_name}）
        """
        return self.tool_name or f"delegate_to_{self.agent_name}"


class EvaluatorSettings(MixSeekBaseSettings):
    """Evaluator用の設定スキーマ（T080完全版 - 動的配列対応）。

    EvaluationConfig互換の完全な評価設定を管理します。
    TeamSettingsと同じパターンで動的配列（metrics）に対応しています。

    主要機能:
    - llm_default相当のデフォルトLLM設定
    - 動的な評価メトリクス配列（[[metrics]]）
    - カスタムメトリクス設定
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_EVALUATOR__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # llm_default相当のデフォルトLLM設定
    default_model: str = Field(
        default="google-gla:gemini-2.5-flash",
        description="デフォルトLLMモデル（EvaluationConfig.llm_default.model互換）",
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Temperature (Noneの場合はモデルのデフォルト値)",
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="最大トークン数（Noneの場合はモデルのデフォルト値）",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="LLM API呼び出しの最大リトライ回数",
    )

    timeout_seconds: int = Field(
        default=300,
        ge=0,
        description="HTTPタイムアウト（秒）",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="生成を停止するシーケンスのリスト",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-pサンプリングパラメータ（Noneの場合はモデルのデフォルト値）",
    )

    seed: int | None = Field(
        default=None,
        description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
    )

    # 動的配列（TeamSettingsパターン）
    metrics: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {"name": "ClarityCoherence", "weight": 0.334},
            {"name": "Coverage", "weight": 0.333},
            {"name": "Relevance", "weight": 0.333},
        ],
        description="評価メトリクス設定の配列（EvaluationConfig.metrics互換）。"
        "デフォルトは ClarityCoherence(0.334), Coverage(0.333), Relevance(0.333)",
    )

    # カスタムメトリクス
    custom_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="カスタムメトリクス設定（EvaluationConfig.custom_metrics互換）",
    )

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, v: str) -> str:
        """デフォルトモデル形式のバリデーション。

        Note:
            共通関数 validate_model_format() を使用（Article 10: DRY原則準拠）

        Args:
            v: モデル形式文字列

        Returns:
            バリデーション済みのモデル形式

        Raises:
            ValueError: 形式が不正な場合
        """
        return validate_model_format(v, allow_empty=False)


class JudgmentSettings(MixSeekBaseSettings):
    """Judgment用の設定スキーマ。

    LLM-as-a-Judgeによるラウンド継続判定の設定を管理します。
    すべての環境（dev/staging/prod）でデフォルト値は同一です（FR-007準拠）。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_JUDGMENT__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # LLM設定
    model: str = Field(
        default="google-gla:gemini-2.5-flash",
        description="LLMモデル (例: google-gla:gemini-2.5-flash)",
    )

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature (デフォルト: 0.0、決定論的判定)",
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="最大トークン数 (Noneの場合はLLM側のデフォルト値)",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="LLM API呼び出しの最大リトライ回数",
    )

    timeout_seconds: int = Field(
        default=60,
        ge=0,
        description="HTTPタイムアウト（秒、デフォルト: 60秒）",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="停止シーケンス（オプション）",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-pサンプリング (Noneの場合はLLM側のデフォルト値)",
    )

    seed: int | None = Field(
        default=None,
        description="ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）",
    )

    # システムプロンプト設定（カスタマイズ可能）
    system_instruction: str | None = Field(
        default=None,
        description="システム指示（Noneの場合はデフォルト指示を使用）",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """モデル形式のバリデーション。

        Note:
            共通関数 validate_model_format() を使用（Article 10: DRY原則準拠）

        Args:
            v: モデル形式文字列

        Returns:
            バリデーション済みのモデル形式

        Raises:
            ValueError: 形式が不正な場合
        """
        return validate_model_format(v, allow_empty=False)


class OrchestratorSettings(WorkspaceValidatorMixin, MixSeekBaseSettings):
    """Orchestrator用の設定スキーマ。

    オーケストレーション全体の設定を管理します。
    すべての環境（dev/staging/prod）でデフォルト値は同一です（FR-007準拠）。

    Note:
        WorkspaceValidatorMixinによりworkspace_pathのバリデーションを継承
        （Article 10: DRY原則準拠）
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # オーケストレーション設定
    workspace_path: Path = Field(
        ...,  # 必須
        description="ワークスペースディレクトリのパス",
        # Note: フィールド名 'workspace_path' は実装詳細
        #       公式環境変数 MIXSEEK_WORKSPACE は内部正規化層で処理
        #       公式TOMLキー 'workspace' は CustomTomlConfigSettingsSource で処理
    )

    timeout_per_team_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="チームごとのタイムアウト（秒）",
    )

    max_concurrent_teams: int = Field(
        default=4,
        ge=1,
        le=100,
        description="同時実行チーム数",
    )

    max_retries_per_team: int = Field(
        default=2,
        ge=0,
        le=10,
        description="チームごとのリトライ回数",
    )

    teams: list[dict[str, str]] = Field(
        default_factory=list,
        description="Team configuration file paths (from orchestrator.toml)",
    )

    evaluator_config: str | None = Field(
        default=None,
        description="Evaluator configuration file path (relative to workspace or absolute)",
    )

    judgment_config: str | None = Field(
        default=None,
        description="Judgment configuration file path (relative to workspace or absolute)",
    )

    prompt_builder_config: str | None = Field(
        default=None,
        description="PromptBuilder configuration file path (relative to workspace or absolute)",
    )

    # === Round configuration (Feature 101-round-config) ===
    max_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of rounds per team (matches OrchestratorTask default)",
    )

    min_rounds: int = Field(
        default=2,
        ge=1,
        description="Minimum number of rounds before LLM-based judgment (matches OrchestratorTask default)",
    )

    submission_timeout_seconds: int = Field(
        default=300,
        gt=0,
        description="Timeout for team submission in each round (seconds, matches OrchestratorTask default)",
    )

    judgment_timeout_seconds: int = Field(
        default=60,
        gt=0,
        description="Timeout for evaluation judgment in each round (seconds, matches OrchestratorTask default)",
    )

    @model_validator(mode="after")
    def validate_round_configuration(self) -> "OrchestratorSettings":
        """Validate min_rounds <= max_rounds constraint.

        Raises:
            ValueError: If min_rounds exceeds max_rounds

        Note:
            This validation is also implemented in OrchestratorTask for defensive programming.
            (Clarifications Session 2025-11-18: 二重検証による早期エラー検出)
        """
        if self.min_rounds > self.max_rounds:
            raise ValueError(f"min_rounds ({self.min_rounds}) must be <= max_rounds ({self.max_rounds})")
        return self

    # Note: workspace_path バリデーションは WorkspaceValidatorMixin から継承


class UISettings(WorkspaceValidatorMixin, MixSeekBaseSettings):
    """UI（Streamlit）用の設定スキーマ。

    WebUI実行時の設定を管理します（Phase 12追加）。
    すべての環境（dev/staging/prod）でデフォルト値は同一です（FR-007準拠）。

    Note:
        WorkspaceValidatorMixinによりworkspace_pathのバリデーションを継承
        （Article 10: DRY原則準拠）
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_UI__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # UI設定
    port: int = Field(
        default=8501,
        ge=1024,
        le=65535,
        description="Streamlit実行ポート",
    )

    workspace_path: Path = Field(
        ...,  # 必須
        description="ワークスペースディレクトリのパス",
        # Note: フィールド名 'workspace_path' は実装詳細
        #       公式環境変数 MIXSEEK_UI__WORKSPACE は内部正規化層で処理
        #       公式TOMLキー 'workspace' は CustomTomlConfigSettingsSource で処理
    )

    # Note: workspace_path バリデーションは WorkspaceValidatorMixin から継承


# Load default prompts at module level (before class definition)
def _load_prompt_builder_defaults() -> dict[str, str]:
    """Load default prompt templates from prompt_builder_default.toml.

    Returns:
        Dictionary containing default prompt templates

    Raises:
        FileNotFoundError: If template file is not found
    """
    import importlib.resources
    import tomllib

    try:
        # Try Python 3.9+ API
        template_content = (
            importlib.resources.files("mixseek")
            .joinpath("config/templates/prompt_builder_default.toml")
            .read_text(encoding="utf-8")
        )
    except AttributeError:
        # Fallback for older Python versions
        import pkgutil

        template_bytes = pkgutil.get_data("mixseek", "config/templates/prompt_builder_default.toml")
        if template_bytes is None:
            raise FileNotFoundError("prompt_builder_default.toml template not found in package")
        template_content = template_bytes.decode("utf-8")

    # Parse TOML
    config = tomllib.loads(template_content)

    # Extract prompt_builder section
    prompt_builder_config = config.get("prompt_builder", {})

    return {
        "team_user_prompt": prompt_builder_config.get("team_user_prompt", ""),
        "evaluator_user_prompt": prompt_builder_config.get("evaluator_user_prompt", ""),
        "judgment_user_prompt": prompt_builder_config.get("judgment_user_prompt", ""),
    }


# Load defaults once at module level
_PROMPT_BUILDER_DEFAULTS = _load_prompt_builder_defaults()


class PromptBuilderSettings(MixSeekBaseSettings):
    """PromptBuilder用の設定スキーマ。

    UserPromptBuilderのプロンプトテンプレート設定を管理します。
    ConfigurationManager統合により、トレーサビリティ機能を提供します。

    主要機能:
    - Team用プロンプトテンプレート（Jinja2形式）
    - Evaluator用プロンプトテンプレート（Jinja2形式）
    - Judgment用プロンプトテンプレート（Jinja2形式）

    Note:
        デフォルト値は prompt_builder_default.toml から読み込まれます。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_PROMPT_BUILDER__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # Prompt templates (use module-level defaults)
    team_user_prompt: str = Field(
        default=_PROMPT_BUILDER_DEFAULTS["team_user_prompt"],
        description="Jinja2 template string for Team user prompts",
    )

    evaluator_user_prompt: str = Field(
        default=_PROMPT_BUILDER_DEFAULTS["evaluator_user_prompt"],
        description="Jinja2 template string for Evaluator user prompts",
    )

    judgment_user_prompt: str = Field(
        default=_PROMPT_BUILDER_DEFAULTS["judgment_user_prompt"],
        description="Jinja2 template string for JudgementClient user prompts",
    )

    @field_validator("team_user_prompt", "evaluator_user_prompt", "judgment_user_prompt")
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that prompt templates are not empty.

        Args:
            v: Prompt template value
            info: Field validation info

        Returns:
            Validated prompt template

        Raises:
            ValueError: If prompt template is empty
        """
        if not v or v.strip() == "":
            field_name = info.field_name
            msg = f"{field_name} cannot be empty"
            raise ValueError(msg)
        return v


class TeamSettings(MixSeekBaseSettings):
    """Team設定スキーマ（T089完全移行版）。

    Leader Agent + 可変数のMember Agent設定を管理します。
    既存のteam.toml形式（参照形式を含む）と完全互換です。

    NOTE: このクラスはPydantic Settingsベースですが、可変数のMember Agent設定を
    扱うため、カスタムvalidatorと参照解決ロジックを使用します（T090で実装）。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_TEAM__",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # Team基本設定
    team_id: str = Field(
        description="チームID",
    )

    team_name: str = Field(
        description="チーム名",
    )

    max_concurrent_members: int = Field(
        default=15,
        ge=1,
        le=50,
        description="最大Member Agent数",
    )

    # Leader Agent設定（必須）
    leader: dict[str, Any] = Field(
        description="Leader Agent設定（LeaderAgentSettingsとして解釈）",
    )

    # Member Agent設定リスト（可変数、オプション）
    members: list[MemberAgentSettings] = Field(
        default_factory=list,
        description="Member Agent設定リスト",
    )

    @model_validator(mode="after")
    def validate_member_count(self) -> "TeamSettings":
        """Member Agent数のバリデーション。

        Returns:
            自身のインスタンス

        Raises:
            ValueError: Member Agent数が上限を超えている場合
        """
        if len(self.members) > self.max_concurrent_members:
            raise ValueError(
                f"Too many members: {len(self.members)} > {self.max_concurrent_members}. "
                f"Adjust max_concurrent_members or reduce member count."
            )
        return self

    @model_validator(mode="after")
    def validate_unique_agent_names(self) -> "TeamSettings":
        """Member Agent名の重複チェック。

        Returns:
            自身のインスタンス

        Raises:
            ValueError: agent_nameが重複している場合
        """
        names = [m.agent_name for m in self.members]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate agent_name detected: {duplicates}")
        return self

    @model_validator(mode="after")
    def validate_unique_tool_names(self) -> "TeamSettings":
        """Tool名の重複チェック。

        Returns:
            自身のインスタンス

        Raises:
            ValueError: tool_nameが重複している場合
        """
        tool_names = []
        for m in self.members:
            if m.tool_name:
                tool_names.append(m.tool_name)
            else:
                tool_names.append(f"delegate_to_{m.agent_name}")

        if len(tool_names) != len(set(tool_names)):
            duplicates = [name for name in tool_names if tool_names.count(name) > 1]
            raise ValueError(f"Duplicate tool_name detected: {duplicates}")
        return self
