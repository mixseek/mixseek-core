# Data Model: Pydantic Settings based Configuration Manager

**Feature**: 051-configuration
**Created**: 2025-11-11
**Status**: Draft

## Overview

本ドキュメントでは、Pydantic Settings based Configuration Managerで使用されるすべてのエンティティ（Pydanticモデル、dataclass）を定義します。

## Entities Overview

### Core Infrastructure Layer

| Entity | Type | Purpose |
|--------|------|---------|
| `SourceTrace` | dataclass | 設定値のトレース情報を保持 |
| `CLISource` | PydanticBaseSettingsSource | CLI引数から設定を読み込むカスタムソース |
| `TracingSourceWrapper` | PydanticBaseSettingsSource | 既存ソースをラップしてトレース情報を記録 |
| `ConfigurationManager` | Class | 設定の読み込みとトレース情報管理を行う薄いラッパー |

### Settings Schema Layer

| Entity | Type | Purpose |
|--------|------|---------|
| `MixSeekBaseSettings` | BaseSettings | すべての設定スキーマの基底クラス |
| `LeaderAgentSettings` | BaseSettings | Leader Agent用の設定スキーマ |
| `MemberAgentSettings` | BaseSettings | Member Agent用の設定スキーマ |
| `EvaluatorSettings` | BaseSettings | Evaluator用の設定スキーマ |
| `OrchestratorSettings` | BaseSettings | Orchestrator用の設定スキーマ |

---

## Entity Definitions

### 1. SourceTrace (dataclass)

**Purpose**: 設定値のトレース情報を保持するデータクラス。どのソースから値が読み込まれたか、いつ読み込まれたかを記録します。

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `value` | `Any` | 設定値（読み込まれた値） |
| `source_name` | `str` | ソース名（例: "config.toml", "environment_variables", "init"） |
| `source_type` | `str` | ソースタイプ（"cli", "env", "toml", "dotenv", "secrets"） |
| `field_name` | `str` | フィールド名（例: "model", "timeout_seconds"） |
| `timestamp` | `datetime` | 読み込み日時（UTC） |

**Validation Rules**: なし（単純なデータコンテナ）

**Relationships**:
- `TracingSourceWrapper`によって生成される
- `ConfigurationManager.get_trace_info()`で取得される

**State Transitions**: なし（イミュータブル）

**Example**:

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

@dataclass
class SourceTrace:
    """設定値のトレース情報"""
    value: Any
    source_name: str
    source_type: str  # "cli", "env", "toml", "dotenv", "secrets"
    field_name: str
    timestamp: datetime

# 使用例
trace = SourceTrace(
    value="openai:gpt-4o",
    source_name="environment_variables",
    source_type="env",
    field_name="model",
    timestamp=datetime.now(UTC),
)
```

---

### 2. CLISource (Custom Settings Source)

**Purpose**: CLI引数から設定を読み込むカスタム設定ソース。pydantic-settingsの`PydanticBaseSettingsSource`を継承し、typerなどのCLIフレームワークとの統合を実現します。

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `settings_cls` | `type[BaseSettings]` | 設定クラス（継承元から） |
| `cli_args` | `dict[str, Any]` | CLI引数（typerから渡される辞書） |

**Methods**:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_field_value(field_name, field_info)` | `tuple[Any, str, bool]` | 指定したフィールドの値を取得 |
| `prepare_field_value(field_name, field_info, value, value_is_complex)` | `Any` | 値の前処理（型変換等） |
| `__call__()` | `dict[str, Any]` | すべてのフィールドの値を取得 |

**Validation Rules**:
- CLI引数がNoneの場合は空辞書として扱う
- フィールド名のマッピング（`timeout_seconds` → `timeout`）をサポート

**Relationships**:
- `MixSeekBaseSettings.settings_customise_sources()`で使用される
- `TracingSourceWrapper`でラップされる

**Example**:

```python
from typing import Any
from pydantic import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

class CLISource(PydanticBaseSettingsSource):
    """CLI引数から設定を読み込むソース"""

    def __init__(
        self,
        settings_cls: type,
        cli_args: dict[str, Any] | None = None,
    ):
        super().__init__(settings_cls)
        self.cli_args = cli_args or {}

    def get_field_value(
        self, field_name: str, field_info: FieldInfo
    ) -> tuple[Any, str, bool]:
        """CLI引数から値を取得"""
        # CLI引数名のマッピング（例: timeout_seconds → timeout）
        cli_name = field_name.replace("_", "-")

        # 値を検索
        if field_name in self.cli_args:
            value = self.cli_args[field_name]
            return value, field_name, True
        elif cli_name in self.cli_args:
            value = self.cli_args[cli_name]
            return value, field_name, True

        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field_info: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        """値の前処理（型変換等）"""
        if value is None:
            return None
        return value

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールドの値を取得"""
        d = {}
        for field_name, field_info in self.settings_cls.model_fields.items():
            value, key, value_is_set = self.get_field_value(field_name, field_info)
            if value_is_set and value is not None:
                d[key] = value
        return d

    def __repr__(self) -> str:
        return f"CLISource(args={len(self.cli_args)} items)"
```

---

### 3. TracingSourceWrapper (Custom Settings Source)

**Purpose**: 既存の設定ソースをラップし、トレース情報を記録するカスタム設定ソース。すべての設定値の出所を追跡可能にします。

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `settings_cls` | `type[BaseSettings]` | 設定クラス（継承元から） |
| `wrapped_source` | `PydanticBaseSettingsSource` | ラップ対象のソース |
| `source_name` | `str` | ソース名（例: "config.toml", "environment_variables"） |
| `source_type` | `str` | ソースタイプ（"cli", "env", "toml", "dotenv", "secrets"） |
| `trace_storage` | `dict[str, SourceTrace]` | トレース情報を保存する辞書 |

**Methods**:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_field_value(field_name, field_info)` | `tuple[Any, str, bool]` | ラップされたソースから値を取得し、トレース情報を記録 |
| `prepare_field_value(field_name, field_info, value, value_is_complex)` | `Any` | 値の前処理（ラップされたソースに委譲） |
| `__call__()` | `dict[str, Any]` | すべてのフィールドの値を取得 |

**Validation Rules**: なし（ラップされたソースのバリデーションに委譲）

**Relationships**:
- 任意の`PydanticBaseSettingsSource`をラップする
- `MixSeekBaseSettings.settings_customise_sources()`で使用される
- `SourceTrace`を生成する

**Example**:

```python
from typing import Any
from dataclasses import dataclass
from datetime import UTC, datetime
from pydantic import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

class TracingSourceWrapper(PydanticBaseSettingsSource):
    """トレース機能を追加するソースラッパー"""

    def __init__(
        self,
        settings_cls: type,
        wrapped_source: PydanticBaseSettingsSource,
        source_name: str,
        source_type: str,
        trace_storage: dict[str, SourceTrace] | None = None,
    ):
        super().__init__(settings_cls)
        self.wrapped_source = wrapped_source
        self.source_name = source_name
        self.source_type = source_type
        self.trace_storage = trace_storage if trace_storage is not None else {}

    def get_field_value(
        self, field_name: str, field_info: FieldInfo
    ) -> tuple[Any, str, bool]:
        """ラップされたソースから値を取得し、トレース情報を記録"""
        value, key, value_is_set = self.wrapped_source.get_field_value(field_name, field_info)

        if value_is_set:
            # トレース情報を記録
            self.trace_storage[field_name] = SourceTrace(
                value=value,
                source_name=self.source_name,
                source_type=self.source_type,
                field_name=field_name,
                timestamp=datetime.now(UTC),
            )

        return value, key, value_is_set

    def prepare_field_value(
        self, field_name: str, field_info: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        """値の前処理（ラップされたソースに委譲）"""
        return self.wrapped_source.prepare_field_value(field_name, field_info, value, value_is_complex)

    def __call__(self) -> dict[str, Any]:
        """すべてのフィールドの値を取得"""
        return self.wrapped_source()

    def __repr__(self) -> str:
        return f"TracingSourceWrapper({self.source_name}, wrapped={self.wrapped_source})"
```

---

### 4. ConfigurationManager

**Purpose**: 設定の読み込みとトレース情報の管理を行う薄いラッパークラス。Pydantic Settingsの機能を統一的なインターフェースで提供します。

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `cli_args` | `dict[str, Any]` | CLI引数（typerから渡される辞書） |
| `workspace` | `Path \| None` | ワークスペースパス |
| `environment` | `str` | 実行環境（dev/staging/prod） |

**Methods**:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `load_settings(settings_class, **extra_kwargs)` | `BaseSettings` | 設定を読み込み（優先順位: CLI > ENV > .env > TOML > デフォルト） |
| `get_trace_info(settings_class, field_name)` | `SourceTrace \| None` | 設定値のトレース情報を取得 |
| `print_debug_info(settings, verbose)` | `None` | デバッグ情報を出力 |
| `get_all_defaults(settings_class)` | `dict[str, Any]` | すべての設定項目のデフォルト値を取得 |

**Validation Rules**: なし（設定スキーマのバリデーションに委譲）

**Relationships**:
- `BaseSettings`（およびそのサブクラス）を読み込む
- `SourceTrace`を取得する
- CLI層（typer）と設定スキーマ層の橋渡し

**Example**:

```python
from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings

class ConfigurationManager:
    """統一的な設定管理マネージャー"""

    def __init__(
        self,
        cli_args: dict[str, Any] | None = None,
        workspace: Path | None = None,
        environment: str = "dev",
    ):
        """初期化

        Args:
            cli_args: CLI引数（typerから変換）
            workspace: ワークスペースパス
            environment: 実行環境（dev/staging/prod）
        """
        self.cli_args = cli_args or {}
        self.workspace = workspace
        self.environment = environment

    def load_settings(
        self,
        settings_class: type[BaseSettings],
        **extra_kwargs,
    ) -> BaseSettings:
        """設定を読み込み

        Args:
            settings_class: 設定クラス（LeaderAgentSettings等）
            **extra_kwargs: 追加のキーワード引数

        Returns:
            設定インスタンス
        """
        # CLI引数と追加引数をマージ
        init_kwargs = {**self.cli_args, **extra_kwargs}

        # 環境を設定
        if "environment" not in init_kwargs:
            init_kwargs["environment"] = self.environment

        # ワークスペースを設定
        if self.workspace and "workspace_path" not in init_kwargs:
            init_kwargs["workspace_path"] = self.workspace

        # Pydantic Settingsで読み込み
        settings = settings_class(**init_kwargs)

        return settings

    def get_trace_info(
        self,
        settings_class: type[BaseSettings],
        field_name: str,
    ) -> SourceTrace | None:
        """設定値のトレース情報を取得

        Args:
            settings_class: 設定クラス
            field_name: フィールド名

        Returns:
            トレース情報（存在しない場合はNone）
        """
        if hasattr(settings_class, "get_trace_info"):
            return settings_class.get_trace_info(field_name)
        return None

    def print_debug_info(
        self,
        settings: BaseSettings,
        verbose: bool = False,
    ):
        """デバッグ情報を出力

        Args:
            settings: 設定インスタンス
            verbose: 詳細情報を出力するか
        """
        print("=" * 60)
        print("Configuration Debug Information")
        print("=" * 60)
        print()

        # 設定値とトレース情報
        for field_name in settings.model_fields:
            value = getattr(settings, field_name)
            trace = self.get_trace_info(type(settings), field_name)

            print(f"{field_name}: {value!r}")
            if trace:
                print(f"  Source: {trace.source_name} ({trace.source_type})")
                print(f"  Timestamp: {trace.timestamp.isoformat()}")
            else:
                print(f"  Source: default")

            if verbose and trace:
                print(f"  Raw value: {trace.value!r}")
            print()

        print("=" * 60)

    def get_all_defaults(
        self,
        settings_class: type[BaseSettings],
    ) -> dict[str, Any]:
        """すべての設定項目のデフォルト値を取得

        Args:
            settings_class: 設定クラス

        Returns:
            デフォルト値の辞書
        """
        defaults = {}
        for field_name, field_info in settings_class.model_fields.items():
            if field_info.default is not None:
                defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                defaults[field_name] = field_info.default_factory()
        return defaults
```

---

### 5. MixSeekBaseSettings (BaseSettings)

**Purpose**: すべての設定スキーマの基底クラス。pydantic-settingsの`BaseSettings`を継承し、共通設定とトレーサビリティ機能を提供します。

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `environment` | `Literal["dev", "staging", "prod"]` | `"dev"` | 実行環境 |

**Class Variables**:

| Variable | Type | Description |
|----------|------|-------------|
| `_trace_storage` | `dict[str, SourceTrace]` | トレース情報を保存する辞書（クラス変数） |
| `model_config` | `SettingsConfigDict` | Pydantic設定 |

**Methods**:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `settings_customise_sources()` | `tuple[PydanticBaseSettingsSource, ...]` | 設定ソースのカスタマイズとトレース機能の追加 |
| `get_trace_info(field_name)` | `SourceTrace \| None` | フィールドのトレース情報を取得 |

**Validation Rules**:
- `extra="forbid"`: 未知の設定項目を拒否
- `validate_default=True`: デフォルト値もバリデーション

**Relationships**:
- すべての設定スキーマ（`LeaderAgentSettings`等）の親クラス
- `TracingSourceWrapper`を使用してトレース情報を記録

**State Transitions**:

```
[未初期化] → load_settings() → [初期化完了] → get_trace_info() → [トレース情報取得]
```

**Example**:

```python
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class MixSeekBaseSettings(BaseSettings):
    """mixseek-core設定のベースクラス"""

    # トレース情報を保存する辞書（クラス変数）
    _trace_storage: dict[str, SourceTrace] = {}

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        toml_file="config.toml",
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
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """設定ソースのカスタマイズとトレース機能の追加

        優先順位: init (CLI) > ENV > dotenv > TOML > secrets
        """
        # トレースストレージを初期化
        cls._trace_storage = {}

        # カスタムソースの準備
        from pydantic_settings import TomlConfigSettingsSource

        toml_source = TomlConfigSettingsSource(settings_cls)

        # 各ソースをトレーシングラッパーで包む
        sources = [
            TracingSourceWrapper(
                settings_cls,
                init_settings,
                source_name="init",
                source_type="cli",
                trace_storage=cls._trace_storage,
            ),
            TracingSourceWrapper(
                settings_cls,
                env_settings,
                source_name="environment_variables",
                source_type="env",
                trace_storage=cls._trace_storage,
            ),
            TracingSourceWrapper(
                settings_cls,
                dotenv_settings,
                source_name=".env",
                source_type="dotenv",
                trace_storage=cls._trace_storage,
            ),
            TracingSourceWrapper(
                settings_cls,
                toml_source,
                source_name="config.toml",
                source_type="toml",
                trace_storage=cls._trace_storage,
            ),
            TracingSourceWrapper(
                settings_cls,
                file_secret_settings,
                source_name="secrets",
                source_type="secrets",
                trace_storage=cls._trace_storage,
            ),
        ]

        return tuple(sources)

    @classmethod
    def get_trace_info(cls, field_name: str) -> SourceTrace | None:
        """フィールドのトレース情報を取得"""
        return cls._trace_storage.get(field_name)
```

---

### 6. LeaderAgentSettings (BaseSettings)

**Purpose**: Leader Agent用の設定スキーマ。LLMモデル、タイムアウト、温度パラメータなどを管理します。

**Fields**:

| Field | Type | Default | Description | Validation |
|-------|------|---------|-------------|------------|
| `model` | `str` | `"openai:gpt-4o"` | LLMモデル（例: "openai:gpt-4o"） | `validate_model()` |
| `temperature` | `float \| None` | `None` | Temperature（Noneの場合はモデルのデフォルト） | `0.0 <= x <= 2.0` |
| `max_tokens` | `int \| None` | `None` | 最大トークン数（Noneの場合はLLM側のデフォルト） | `> 0` |
| `timeout_seconds` | `int` | `300` | HTTPタイムアウト（秒） | `>= 0` |
| `max_retries` | `int` | `3` | LLM API呼び出しの最大リトライ回数 | `>= 0` |
| `stop_sequences` | `list[str] \| None` | `None` | 停止シーケンス（オプション） | - |
| `top_p` | `float \| None` | `None` | Top-pサンプリング | `0.0 <= x <= 1.0` |
| `seed` | `int \| None` | `None` | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | - |

**Validation Rules** (FR-007, FR-014, FR-015):

1. **model (FR-007, FR-009, Article 9)**:
   - デフォルト値: `"openai:gpt-4o"` （すべての環境で同一、issue #51準拠）
   - 形式チェック: `provider:model-name`形式であること（":"が含まれること）
   - 環境別の動作差異なし（FR-007準拠）

2. **temperature**:
   - 範囲: `0.0 <= temperature <= 1.0`
   - Noneは許容（モデルのデフォルト値を使用）

3. **timeout_seconds (FR-007, FR-009, Article 9)**:
   - デフォルト値: `300`秒 （すべての環境で同一）
   - 範囲: `10 <= timeout_seconds <= 600`
   - 環境別の動作差異なし（FR-007準拠）

**Note**: FR-007により、すべてのオプション設定のデフォルト値は環境（dev/staging/prod）を問わず同一です。環境別の設定変更は、CLI引数・環境変数・TOML設定による上書きで実現します。

**Relationships**:
- `MixSeekBaseSettings`を継承
- `ConfigurationManager`で読み込まれる

**Example**:

```python
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

class LeaderAgentSettings(MixSeekBaseSettings):
    """Leader Agent設定（Article 9完全準拠、FR-007準拠）"""

    model_config = SettingsConfigDict(
        **MixSeekBaseSettings.model_config,
        env_prefix="MIXSEEK_LEADER_",
    )

    # LLM設定（オプション、すべての環境で同じデフォルト値）
    model: str = Field(
        default="openai:gpt-4o",
        description="LLMモデル (例: openai:gpt-4o)",
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
        description="HTTPタイムアウト（秒）",
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

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """モデル形式のバリデーション（FR-007準拠：環境別分岐なし）"""
        # モデル形式のバリデーション
        if ":" not in v:
            raise ValueError(
                f"Invalid model format: '{v}'. Expected format: 'provider:model-name'"
            )
        return v
```

---

### 7. MemberAgentSettings (BaseSettings)

**Purpose**: Member Agent用の設定スキーマ。複数のMember AgentのLLM設定を管理します。

**Fields**:

| Field | Type | Default | Description | Validation |
|-------|------|---------|-------------|------------|
| `model` | `str` | `""` | LLMモデル | `validate_model()` |
| `temperature` | `float \| None` | `None` | Temperature | `0.0 <= x <= 2.0` |
| `max_tokens` | `int \| None` | `None` | 最大トークン数（Noneの場合はLLM側のデフォルト） | `> 0` |
| `timeout_seconds` | `int` | `0` | HTTPタイムアウト（秒） | `>= 0` |
| `max_retries` | `int` | `3` | LLM API呼び出しの最大リトライ回数 | `>= 0` |
| `stop_sequences` | `list[str] \| None` | `None` | 停止シーケンス（オプション） | - |
| `top_p` | `float \| None` | `None` | Top-pサンプリング | `0.0 <= x <= 1.0` |
| `seed` | `int \| None` | `None` | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | - |

**Validation Rules**: `LeaderAgentSettings`と同様

**Relationships**:
- `MixSeekBaseSettings`を継承
- `ConfigurationManager`で読み込まれる

**Example**:

```python
class MemberAgentSettings(MixSeekBaseSettings):
    """Member Agent設定（Article 9完全準拠）"""

    model_config = SettingsConfigDict(
        **MixSeekBaseSettings.model_config,
        env_prefix="MIXSEEK_MEMBER_",
    )

    # LLM設定
    model: str = Field(
        default="",
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

    timeout_seconds: int = Field(
        default=0,
        ge=0,
        description="HTTPタイムアウト（秒）",
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

    # バリデーションは LeaderAgentSettings と同様
    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        # 同じロジック
        ...

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int, info) -> int:
        # 同じロジック
        ...
```

---

### 8. EvaluatorSettings (BaseSettings)

**Purpose**: Evaluator用の設定スキーマ。評価ロジックとLLM設定を管理します。T080拡張により、動的メトリクス配列とEvaluationConfig互換性をサポートします。

**Fields**:

| Field | Type | Default | Description | Validation |
|-------|------|---------|-------------|------------|
| `default_model` | `str` | `"anthropic:claude-sonnet-4-5-20250929"` | デフォルトLLMモデル（既存実装との後方互換性維持） | `validate_model()` |
| `temperature` | `float \| None` | `None` | Temperature | `0.0 <= x <= 2.0` |
| `max_tokens` | `int \| None` | `None` | 最大トークン数 (Noneの場合はLLM側のデフォルト値) | `> 0` |
| `timeout_seconds` | `int` | `300` | HTTPタイムアウト（秒） | `>= 0` |
| `max_retries` | `int` | `3` | 最大リトライ回数 | `>= 0` |
| `stop_sequences` | `list[str] \| None` | `None` | 停止シーケンス（オプション） | - |
| `top_p` | `float \| None` | `None` | Top-pサンプリング | `0.0 <= x <= 1.0` |
| `seed` | `int \| None` | `None` | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | - |
| `metrics` | `list[dict[str, Any]]` | `[]` | メトリクス配列（動的、EvaluationConfig互換） | - |
| `custom_metrics` | `dict[str, Any]` | `{}` | カスタムメトリクス設定 | - |

**Validation Rules**: `LeaderAgentSettings`と同様（ただしT080拡張により追加フィールドあり）

**Relationships**:
- `MixSeekBaseSettings`を継承
- `ConfigurationManager`で読み込まれる

**Example**:

```python
class EvaluatorSettings(MixSeekBaseSettings):
    """Evaluator設定（Article 9完全準拠）"""

    model_config = SettingsConfigDict(
        **MixSeekBaseSettings.model_config,
        env_prefix="MIXSEEK_EVALUATOR_",
    )

    # LLM設定
    default_model: str = Field(
        default="anthropic:claude-sonnet-4-5-20250929",
        description="デフォルトLLMモデル (例: anthropic:claude-sonnet-4-5-20250929)",
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
        description="HTTPタイムアウト（秒）",
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

    # 動的メトリクス配列（T080拡張）
    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="メトリクス配列（EvaluationConfig互換）",
    )

    custom_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="カスタムメトリクス設定",
    )

    # バリデーションは LeaderAgentSettings と同様
    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        # 同じロジック
        ...

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int, info) -> int:
        # 同じロジック
        ...
```

---

### 9. OrchestratorSettings (BaseSettings)

**Purpose**: Orchestrator用の設定スキーマ。オーケストレーション全体の設定を管理します。

**Fields**:

| Field | Type | Default | Description | Validation |
|-------|------|---------|-------------|------------|
| `workspace_path` | `Path` | （必須） | ワークスペースディレクトリのパス | 必須フィールド、存在チェック |
| `timeout_per_team_seconds` | `int` | `300` | チームごとのタイムアウト（秒） | `10 <= x <= 3600` |
| `max_concurrent_teams` | `int` | `4` | 同時実行チーム数 | `1 <= x <= 100` |

**Validation Rules** (FR-007, FR-008, Article 9):

1. **workspace_path (必須フィールド)**:
   - すべての環境で必須（未設定の場合はエラー）
   - 存在チェック: パスが存在しない場合はエラー
   - 環境別の動作差異なし（FR-007準拠）

2. **timeout_per_team_seconds (オプションフィールド)**:
   - デフォルト値: `300`秒（すべての環境で同一）
   - 範囲: `10 <= timeout_per_team_seconds <= 3600`
   - 環境別の動作差異なし（FR-007準拠）

3. **max_concurrent_teams (オプションフィールド)**:
   - デフォルト値: `4`（すべての環境で同一）
   - 範囲: `1 <= max_concurrent_teams <= 100`
   - 環境別の動作差異なし（FR-007準拠）

**Note**: FR-007により、すべてのオプション設定のデフォルト値は環境（dev/staging/prod）を問わず同一です。必須フィールド（workspace_path）はすべての環境で未設定時にエラーを出します（FR-008）。

**Relationships**:
- `MixSeekBaseSettings`を継承
- `ConfigurationManager`で読み込まれる

**Example**:

```python
from pathlib import Path

class OrchestratorSettings(MixSeekBaseSettings):
    """Orchestrator設定（Article 9完全準拠）"""

    model_config = SettingsConfigDict(
        **MixSeekBaseSettings.model_config,
        env_prefix="MIXSEEK_ORCHESTRATOR_",
    )

    # オーケストレーション設定（必須）
    workspace_path: Path = Field(
        ...,  # 必須（FR-008: すべての環境で必須）
        description="ワークスペースディレクトリのパス",
    )

    # オーケストレーション設定（オプション、すべての環境で同じデフォルト値）
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

    @field_validator("workspace_path")
    @classmethod
    def validate_workspace(cls, v: Path) -> Path:
        """ワークスペースパスの存在チェック（FR-007準拠：環境別分岐なし）"""
        if not v.exists():
            raise ValueError(f"Workspace path does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Workspace path is not a directory: {v}")
        return v
```

---

## Entity Relationships Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ConfigurationManager                     │
│  - load_settings()                                          │
│  - get_trace_info()                                         │
│  - print_debug_info()                                       │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ uses
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   MixSeekBaseSettings                       │
│  - environment: Literal["dev", "staging", "prod"]           │
│  - settings_customise_sources() (ClassMethod)               │
│  - get_trace_info() (ClassMethod)                           │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ inherits
       ┌───────┴────────┬───────────┬─────────────┐
       ▼                ▼           ▼             ▼
┌─────────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
│Leader       │  │Member    │ │Evaluator │ │Orchestr. │
│Agent        │  │Agent     │ │Settings  │ │Settings  │
│Settings     │  │Settings  │ │          │ │          │
└─────────────┘  └──────────┘ └──────────┘ └──────────┘

┌─────────────────────────────────────────────────────────────┐
│             TracingSourceWrapper                            │
│  - wrapped_source: PydanticBaseSettingsSource               │
│  - source_name: str                                         │
│  - source_type: str                                         │
│  - trace_storage: dict[str, SourceTrace]                    │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ wraps
       ┌───────┴────────┬───────────┬─────────────┐
       ▼                ▼           ▼             ▼
┌─────────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐
│CLISource    │  │Env       │ │DotEnv    │ │TOML      │
│(Custom)     │  │Source    │ │Source    │ │Source    │
│             │  │(Built-in)│ │(Built-in)│ │(Built-in)│
└─────────────┘  └──────────┘ └──────────┘ └──────────┘

┌─────────────────────────────────────────────────────────────┐
│                      SourceTrace                            │
│  - value: Any                                               │
│  - source_name: str                                         │
│  - source_type: str                                         │
│  - field_name: str                                          │
│  - timestamp: datetime                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Settings Priority Flow

設定値の優先順位解決フロー:

```
CLI引数 (CLISource)
    ↓ (最高優先度)
環境変数 (EnvSource)
    ↓
.envファイル (DotEnvSource)
    ↓
TOMLファイル (TomlSource)
    ↓
デフォルト値 (field default)
    ↓ (最低優先度)
[最終値]

すべてのソースは TracingSourceWrapper でラップされ、
値が読み込まれた時点で SourceTrace が記録される
```

---

## Validation Flow

環境別バリデーションのフロー:

```
[設定値読み込み]
    ↓
[Pydanticバリデーション（型チェック、範囲チェック）]
    ↓
[field_validator実行]
    ↓
environment == "prod"?
    ├─ Yes → 値が未設定（空文字列または0）の場合はエラー
    └─ No  → 値が未設定の場合はデフォルト値を適用
    ↓
[最終値]
```

---

## Summary

本データモデルは、以下の特徴を持ちます:

1. **トレーサビリティ**: すべての設定値の出所（CLI、ENV、TOML等）を`SourceTrace`で追跡
2. **型安全性**: Pydanticバリデーションによる厳密な型チェック
3. **環境別戦略**: 本番環境では明示的な設定を強制、開発環境ではデフォルト値を許容
4. **拡張性**: カスタムソース（`CLISource`、`TracingSourceWrapper`）で機能拡張可能
5. **統一性**: `MixSeekBaseSettings`を基底クラスとして、すべての設定スキーマが統一的なインターフェースを持つ

Article 9（Data Accuracy Mandate）に完全準拠し、ハードコードされたデフォルト値を排除し、明示的な設定管理を実現します。
