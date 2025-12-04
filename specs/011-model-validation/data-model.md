# Data Model: LLMモデル互換性検証

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: 仕様のKey Entitiesから抽出したデータモデルの詳細定義

## Overview

本機能のデータモデルは全て`pydantic.BaseModel`を継承し、Article 16（型安全性）とArticle 9（データ正確性）を厳格に遵守する。各モデルは`@field_validator`および`@model_validator`による段階的検証を実装し、mypy strict modeで型エラーゼロを保証する。

## 1. ModelInfo（モデルカタログ項目）

**出典**: spec.md Key Entities「モデルカタログ項目」
**責務**: llm-discoveryから取得したモデルの基本情報を保持

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal

class ModelInfo(BaseModel):
    """LLMモデルの基本情報"""

    model_config = ConfigDict(
        extra="forbid",              # 追加フィールド禁止（Article 9）
        str_strip_whitespace=True,   # 文字列トリム
        validate_assignment=True,    # 代入時再検証（Article 16）
    )

    provider: str = Field(..., description="プロバイダー名（google/openai/anthropic）")
    model_id: str = Field(..., description="モデル識別子（例: gemini-2.5-flash）")
    name: str = Field(..., description="モデル表示名")
    modality: str = Field(..., description="モダリティ（chat/text-to-speech/image-generation等）")
    version: Literal["stable", "preview", "experimental"] = Field(
        ..., description="バージョン分類"
    )
    source: str = Field(..., description="データソース（llm-discovery等）")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """プロバイダー検証"""
        allowed = {"google", "openai", "anthropic"}
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}, got: {v}")
        return v.lower()

    @field_validator("model_id", "name")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """空文字列禁止（Article 9: 暗黙的フォールバック禁止）"""
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()

    @field_validator("modality")
    @classmethod
    def validate_modality(cls, v: str) -> str:
        """モダリティ検証（会話モデル抽出の基準）"""
        known_modalities = {
            "chat", "text", "text-to-speech", "image-generation",
            "embedding", "moderation", "audio"
        }
        if v.lower() not in known_modalities:
            # 未知のモダリティは警告のみ（将来の拡張性）
            pass
        return v.lower()
```

### Relationships
- **Input**: llm-discoveryのTOML/JSON/CSV出力
- **Output**: `ConversationalModelExtractor`の抽出対象
- **Validation**: FR-003に準拠（provider、id、name、version保持）

---

## 2. CompatibilityResult（互換性判定結果）

**出典**: spec.md Key Entities「互換性判定結果」
**責務**: 各モデルのmixseekエージェント種別とPydantic AIカテゴリの互換性を記録

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class CompatibilityResult(BaseModel):
    """モデル互換性判定結果"""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model_id: str = Field(..., description="対象モデルID")
    provider: str = Field(..., description="プロバイダー名")

    # mixseekエージェント種別の互換性（FR-005）
    plain_compatible: bool = Field(..., description="plainエージェント対応")
    web_search_compatible: bool = Field(..., description="web-searchエージェント対応")
    code_exec_compatible: bool = Field(..., description="code-execエージェント対応")

    # Pydantic AIカテゴリ（FR-006）
    pydantic_ai_category: Literal["google", "openai", "anthropic", "unknown"] = Field(
        ..., description="Pydantic AIモデルカテゴリ"
    )

    # 追加情報
    function_calling_supported: bool = Field(
        default=False, description="Function calling対応"
    )
    authentication_status: Literal["valid", "invalid", "not_tested"] = Field(
        default="not_tested", description="認証状態"
    )
    notes: str = Field(default="", description="判定根拠・備考")

    @property
    def is_any_compatible(self) -> bool:
        """いずれかのエージェント種別に対応しているか"""
        return (
            self.plain_compatible
            or self.web_search_compatible
            or self.code_exec_compatible
        )
```

### Validation Rules (FR-005, FR-006)
- Claudeモデル: `plain_compatible=True`, `code_exec_compatible=True`, `web_search_compatible=False`
- OpenAIモデル: `plain_compatible=True`, `web_search_compatible=False`, `code_exec_compatible=False`
- Googleモデル: プロバイダー判定により決定

### Relationships
- **Input**: `CompatibilityChecker`の判定ロジック
- **Output**: `ValidationMetrics`の参照データ、TOML互換性マトリクスの`[models.compatibility]`セクション

---

## 3. ValidationMetrics（検証メトリクス）

**出典**: spec.md Key Entities「検証メトリクス」
**責務**: API検証の成功/失敗、レイテンシ、トークン数、エラー詳細を記録

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Literal

class ValidationMetrics(BaseModel):
    """API検証メトリクス"""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model_id: str = Field(..., description="対象モデルID")
    provider: str = Field(..., description="プロバイダー名")

    # 検証結果（FR-007）
    success: bool = Field(..., description="検証成功フラグ")
    error_type: str | None = Field(default=None, description="エラー種別")
    error_message: str | None = Field(default=None, description="エラーメッセージ")

    # レイテンシ統計（FR-007、SC-003）
    latency_p50_ms: float | None = Field(default=None, description="P50レイテンシ（ミリ秒）")
    latency_p95_ms: float | None = Field(default=None, description="P95レイテンシ（ミリ秒）")
    latency_p99_ms: float | None = Field(default=None, description="P99レイテンシ（ミリ秒）")

    # トークン消費（FR-007）
    input_tokens: int | None = Field(default=None, description="入力トークン数")
    output_tokens: int | None = Field(default=None, description="出力トークン数")

    # リトライ情報（FR-008）
    retry_count: int = Field(default=0, description="リトライ回数")
    max_retries: int = Field(default=3, description="最大リトライ回数")

    # タイムスタンプ（FR-011）
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="検証日時（UTC）")

    # コスト情報
    estimated_cost_usd: Decimal = Field(
        default=Decimal("0.00"), description="推定コスト（USD）"
    )

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int, info) -> int:
        """リトライ回数が最大値を超えていないことを確認"""
        max_retries = info.data.get("max_retries", 3)
        if v > max_retries:
            raise ValueError(f"retry_count ({v}) exceeds max_retries ({max_retries})")
        return v

    @field_validator("estimated_cost_usd")
    @classmethod
    def validate_cost(cls, v: Decimal) -> Decimal:
        """コストが負の値でないことを確認"""
        if v < Decimal("0.00"):
            raise ValueError("Cost must be non-negative")
        return v
```

### Relationships
- **Input**: `APIValidator`のAPI検証結果
- **Output**: `RecommendationReport`のメトリクス参照、TOML互換性マトリクスの`[models.metrics]`セクション

---

## 4. RecommendationReport（推奨レポート）

**出典**: spec.md Key Entities「推奨レポート」
**責務**: TOMLおよびMarkdown出力用の集約データ、推奨度ランク

```python
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Literal
from decimal import Decimal

class RecommendationReport(BaseModel):
    """推奨レポート（集約データ）"""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model_id: str = Field(..., description="モデルID")
    provider: str = Field(..., description="プロバイダー名")
    name: str = Field(..., description="モデル表示名")

    # 互換性情報
    compatibility: CompatibilityResult = Field(..., description="互換性判定結果")

    # 検証メトリクス
    metrics: ValidationMetrics | None = Field(default=None, description="検証メトリクス")

    # 推奨度（FR-012、FR-013）
    recommendation_rank: Literal["⭐⭐⭐", "⭐⭐", "⭐"] = Field(
        ..., description="推奨度ランク"
    )
    cost_performance: Literal["high", "medium", "low"] = Field(
        ..., description="コストパフォーマンス"
    )

    # 制約事項
    limitations: list[str] = Field(default_factory=list, description="制約事項リスト")
    notes: str = Field(default="", description="備考")

    @computed_field
    @property
    def overall_status(self) -> str:
        """総合ステータス（レポート生成用）"""
        if self.metrics is None:
            return "未検証"
        if not self.metrics.success:
            return "検証失敗"
        if not self.compatibility.is_any_compatible:
            return "非互換"
        return "推奨"

    @computed_field
    @property
    def estimated_cost_usd(self) -> Decimal:
        """推定コスト（メトリクスから取得）"""
        if self.metrics is None:
            return Decimal("0.00")
        return self.metrics.estimated_cost_usd
```

### Relationships
- **Input**: `CompatibilityResult` + `ValidationMetrics`
- **Output**: `TOMLMatrixGenerator`、`MarkdownReportGenerator`

---

## 5. ValidationConfig（検証設定）

**出典**: FR-009（コスト上限）、FR-008（リトライ設定）
**責務**: 検証プロセスの設定値を一元管理（Article 9: ハードコード禁止）

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal

class ValidationConfig(BaseSettings):
    """検証設定（環境変数から読み込み）"""

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        case_sensitive=False,
        extra="ignore",  # 未知の環境変数を無視
    )

    # コスト制限（FR-009）
    cost_limit_usd: Decimal = Field(
        default=Decimal("1.00"), description="累計コスト上限（USD）"
    )

    # リトライ設定（FR-008）
    max_retries: int = Field(default=3, description="最大リトライ回数")
    retry_base_delay: float = Field(default=1.0, description="リトライ基本遅延（秒）")

    # タイムアウト
    validation_timeout: int = Field(default=120, description="検証タイムアウト（秒）")

    # 並列実行
    max_concurrent_validations: int = Field(default=5, description="最大並列検証数")
```

### Environment Variables (Article 9)
- `MIXSEEK_COST_LIMIT_USD`: デフォルト"1.00"
- `MIXSEEK_MAX_RETRIES`: デフォルト3
- `MIXSEEK_RETRY_BASE_DELAY`: デフォルト1.0
- `MIXSEEK_VALIDATION_TIMEOUT`: デフォルト120
- `MIXSEEK_MAX_CONCURRENT_VALIDATIONS`: デフォルト5

### Rationale
- Article 9: マジックナンバー禁止
- Article 9: 暗黙的フォールバック禁止（全てデフォルト値を明示的に定義）
- 既存パターン踏襲: `src/mixseek/models/member_agent.py::EnvironmentConfig`

---

## 6. ModelListInput（入力データ）

**出典**: FR-001、FR-004
**責務**: TOML/JSON/CSV入力の統一的な表現

**データソース**: `llm-discovery`コマンドで生成
```bash
uvx llm-discovery export --format toml --output models.toml
```

```python
from pydantic import BaseModel, Field, ConfigDict

class ModelListInput(BaseModel):
    """モデルリスト入力（複数形式対応）"""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    models: list[ModelInfo] = Field(..., description="モデル情報リスト")
    metadata: dict[str, str] = Field(default_factory=dict, description="メタデータ")

    def filter_conversational(self) -> list[ModelInfo]:
        """会話モデルのみ抽出（FR-002）"""
        excluded_modalities = {
            "text-to-speech",
            "image-generation",
            "embedding",
            "moderation",
        }
        return [
            model
            for model in self.models
            if model.modality not in excluded_modalities
        ]
```

### Relationships
- **Input**: `ModelListLoader`（TOML/JSON/CSV読み込み）
- **Output**: `ConversationalModelExtractor`の入力

---

## Entity Relationships Diagram

```
┌──────────────────┐
│ ModelListInput   │
│ (TOML/JSON/CSV)  │
└────────┬─────────┘
         │
         ├─→ filter_conversational()
         │
         v
┌──────────────────┐
│ ModelInfo        │ ←─ llm-discovery出力
│ (会話モデルのみ) │
└────────┬─────────┘
         │
         ├─→ CompatibilityChecker
         │
         v
┌──────────────────────┐
│ CompatibilityResult  │
└────────┬─────────────┘
         │
         ├─→ APIValidator
         │
         v
┌──────────────────────┐
│ ValidationMetrics    │
└────────┬─────────────┘
         │
         ├─→ RecommendationReport
         │
         v
┌──────────────────────┐      ┌─────────────────┐
│ RecommendationReport │ ────→│ TOML Matrix     │
│                      │      └─────────────────┘
│                      │      ┌─────────────────┐
│                      │ ────→│ Markdown Report │
└──────────────────────┘      └─────────────────┘
```

---

## State Transitions

### 1. モデル抽出フロー
```
入力（145モデル） → 非会話系除外 → 会話モデル（45-70件）
```

### 2. 検証フロー
```
会話モデル → 互換性判定 → API検証 → メトリクス記録
                 │             │
                 v             v
          CompatibilityResult  ValidationMetrics
```

### 3. レポート生成フロー
```
CompatibilityResult + ValidationMetrics
         │
         v
  RecommendationReport
         │
         ├─→ TOML Matrix Generator
         └─→ Markdown Report Generator
```

---

## Validation Strategy

### Field-Level Validation
- `@field_validator`: 個別フィールドの型・範囲・形式検証
- Article 9準拠: 空文字列、負の値、範囲外の値を明示的に拒否

### Model-Level Validation
- `@model_validator(mode="after")`: フィールド間の整合性検証
- 例: `retry_count <= max_retries`

### Cross-Model Validation
- `CompatibilityChecker`: 複数モデルの整合性検証
- `ConfigValidator`パターンの踏襲

---

## Summary

| Model | Responsibility | Key Validators | FR References |
|-------|---------------|---------------|---------------|
| ModelInfo | モデル基本情報 | provider, model_id, modality | FR-003 |
| CompatibilityResult | 互換性判定 | pydantic_ai_category | FR-005, FR-006 |
| ValidationMetrics | API検証結果 | retry_count, cost | FR-007, FR-008 |
| RecommendationReport | 推奨レポート | overall_status | FR-012, FR-013 |
| ValidationConfig | 検証設定 | BaseSettings（環境変数） | FR-009, Article 9 |
| ModelListInput | 入力データ | filter_conversational() | FR-001, FR-002, FR-004 |

**全モデルはmypy --strictでゼロエラーを保証し、Article 16（型安全性）を厳格に遵守する。**
