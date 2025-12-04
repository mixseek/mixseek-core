# Research: LLMモデル互換性検証

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: Technical Contextで特定された技術選択の根拠、既存実装パターン、ベストプラクティスの調査

## 1. Pydantic BaseModelによるデータモデル設計

### Decision
全データモデルに`pydantic.BaseModel`を使用し、`@field_validator`と`@model_validator`による段階的検証を実装する。

### Rationale
- **既存実装との一貫性**: `src/mixseek/models/member_agent.py::MemberAgentConfig`で実証済みのパターン
- **型安全性**: Article 16（Python Type Safety Mandate）の厳格な遵守
- **自動バリデーション**: Pydantic v2の`ConfigDict(extra="forbid", validate_assignment=True)`により、代入時にも再検証が実行される
- **エラーの明確性**: `ValidationError`により、どのフィールドがどのような理由で検証失敗したかを詳細に把握可能

### Alternatives Considered
1. **dataclass + 手動バリデーション**
   - 却下理由: Article 9（データ正確性）違反リスク、バリデーションロジックの重複、型安全性の低下
2. **辞書ベースのデータ構造**
   - 却下理由: Article 16（型安全性）の完全違反、mypy strict mode非対応

### Implementation Pattern (from existing code)
```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ModelInfo(BaseModel):
    """モデルカタログ項目"""
    model_config = ConfigDict(
        extra="forbid",              # 追加フィールド禁止
        str_strip_whitespace=True,   # 文字列トリム
        validate_assignment=True,    # 代入時再検証
    )

    provider: str
    model_id: str
    name: str
    modality: str
    version: str

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        if not v:
            raise ValueError("model_id must not be empty")
        return v
```

**Reference**: `src/mixseek/models/member_agent.py:46-95`

---

## 2. API認証とPydantic AIモデル生成

### Decision
既存の`src/mixseek/core/auth.py::create_authenticated_model`を再利用し、Article 10（DRY原則）を遵守する。

### Rationale
- **DRY原則の厳守**: 認証ロジックの重複実装を回避
- **一貫性**: Google AI、OpenAI、Anthropicの認証方式を統一的に扱う
- **エラーハンドリング**: 認証失敗時の明示的エラー送出（Article 9準拠）

### Existing Implementation
```python
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel

def create_authenticated_model(model_id: str):
    # プロバイダー判定とモデル生成
    if auth_provider == AuthProvider.GOOGLE_AI:
        return GoogleModel(base_model_name, provider="google-gla")
    elif auth_provider == AuthProvider.OPENAI:
        return OpenAIChatModel(base_model_name)
    elif auth_provider == AuthProvider.ANTHROPIC:
        return AnthropicModel(base_model_name)
    else:
        raise ValueError(f"Unsupported provider: {auth_provider}")

# Example model ID patterns:
# Google: gemini-2.5-flash, gemini-2.5-pro
# OpenAI: gpt-4o, gpt-4o-mini, o1
# Anthropic: claude-sonnet-4-5-20250929, claude-haiku-4-5
```

**Reference**: `src/mixseek/core/auth.py:123-167`

### Integration Strategy
- API検証機能は`create_authenticated_model`をインポートして直接使用
- 認証失敗時は`AuthenticationError`を補足し、`ValidationMetrics`のエラー情報に記録
- **Article 9違反の防止**: 認証失敗時のフォールバックは一切行わない

---

## 3. 包括的検証パターン（ConfigValidator）

### Decision
`src/mixseek/config/validators.py::ConfigValidator`の検証パターンを踏襲し、段階的検証アーキテクチャを採用する。

### Rationale
- **既存パターンの再利用**: プロジェクト全体で統一された検証アプローチ
- **エラー収集**: 単一フィールドエラーで即座に停止せず、全エラーを収集してユーザーに提示
- **改善提案**: `suggest_improvements()`による建設的なフィードバック

### Existing Pattern
```python
class ConfigValidator:
    def validate_config(self, config: MemberAgentConfig) -> list[str]:
        errors: list[str] = []
        errors.extend(self._validate_basic_config(config))
        errors.extend(self._validate_environment(config))
        errors.extend(self._validate_model_config(config))
        errors.extend(self._validate_consistency(config))
        return errors

    def _validate_basic_config(self, config: MemberAgentConfig) -> list[str]:
        errors: list[str] = []
        if not config.name:
            errors.append("Agent name is required")
        return errors
```

**Reference**: `src/mixseek/config/validators.py:15-138`

### Adaptation for Model Validation
- `CompatibilityChecker`クラスで同様の段階的検証を実装
- 検証メソッド:
  1. `_validate_modality()`: モダリティ検証（会話モデル判定）
  2. `_validate_provider()`: プロバイダー検証（Google/OpenAI/Anthropic）
  3. `_validate_agent_compatibility()`: エージェント種別互換性検証
  4. `_validate_pydantic_ai_category()`: Pydantic AIカテゴリ検証

---

## 4. 非同期API検証とリトライ機構

### Decision
`pytest-asyncio`による非同期テスト、指数バックオフによる最大3回リトライを実装する。

### Rationale
- **パフォーマンス**: 最大70モデルの並列検証で2時間以内完了（SC-003）
- **信頼性**: レート制限・一時的エラーへの自動対処（FR-008）
- **コスト管理**: 不必要なリトライによるAPI消費を防止

### Retry Strategy
```python
class ExponentialBackoff:
    """指数バックオフによるリトライ機構"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        raise MaxRetriesExceededError()
```

### Test Strategy (from existing test patterns)
- ユニットテスト: リトライロジックのみ（モック使用）
- インテグレーションテスト: API呼び出し全体（モック使用、レート制限シミュレーション）
- E2Eテスト: 実API（`@pytest.mark.e2e`でマーク、コスト発生に注意）

**Reference**: `tests/unit/test_member_agent_config.py`

---

## 5. コスト追跡とメトリクス測定

### Decision
累計APIコスト追跡（デフォルト上限$1.00）、P50/P95/P99レイテンシ測定、トークン消費記録を実装する。

### Rationale
- **コスト制御**: FR-009、SC-004の厳格な遵守
- **パフォーマンス分析**: レイテンシ統計による実運用への適用可否判定
- **トレーサビリティ**: 検証結果の長期保存とレポート生成

### Implementation Approach
```python
from decimal import Decimal
from collections.abc import Callable

class CostTracker:
    """累計APIコスト追跡"""

    def __init__(self, cost_limit: Decimal):
        self.cost_limit = cost_limit
        self.cumulative_cost = Decimal("0.00")
        self.cost_history: list[Decimal] = []

    def add_cost(self, cost: Decimal) -> None:
        """コスト追加とチェック（Article 9: 明示的エラー送出）"""
        self.cumulative_cost += cost
        self.cost_history.append(cost)

        if self.cumulative_cost >= self.cost_limit:
            raise CostLimitExceededError(
                f"Cost limit ${self.cost_limit} exceeded: ${self.cumulative_cost}"
            )

    def can_proceed(self, estimated_cost: Decimal) -> bool:
        """次のAPI呼び出しが可能かチェック"""
        return (self.cumulative_cost + estimated_cost) < self.cost_limit
```

### Metrics Collection
- **レイテンシ**: `time.perf_counter()`でマイクロ秒精度測定
- **統計計算**: `statistics.quantiles()`でP50/P95/P99を計算
- **トークン数**: Pydantic AIの`Usage`オブジェクトから取得

---

## 6. TOML/JSON/CSV入力の統一的処理

### Decision
`typer`CLIで入力形式を選択可能にし、内部的には全て`pydantic.BaseModel`に統一する。入力ファイルは`llm-discovery`コマンドで動的に生成されることを前提とする。

### Rationale
- **柔軟性**: FR-004の要件（複数入力形式サポート）
- **既存パターン**: `src/mixseek/config/member_agent_loader.py::MemberAgentLoader`の踏襲
- **型安全性**: 入力形式によらず、Pydantic検証を通過
- **Article 9準拠**: 静的ファイルではなく、ユーザーが明示的に最新データを取得

### データソース
入力ファイルは`llm-discovery`コマンドで生成：
```bash
# 最新のモデルリストを取得
uvx llm-discovery export --format toml --output models.toml
```

**重要**:
- 静的なデフォルトファイルをパッケージに含めない
- ユーザーが検証実行前に明示的に最新データを取得
- 古いモデル情報による誤った判定を防ぐ

### Loader Pattern (from existing code)
```python
import tomllib
from pathlib import Path

class MemberAgentLoader:
    @staticmethod
    def load_config(toml_path: Path) -> MemberAgentConfig:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
        # Pydantic v2のmodel_validate()を使用
        return MemberAgentConfig.model_validate(data["agent"])
```

**Reference**: `src/mixseek/config/member_agent_loader.py:12-24`

### Adaptation for Model Validation
- `ModelListLoader`クラスで同様のパターンを実装
- TOML: `tomllib.load()` → Pydantic検証
- JSON: `json.load()` → Pydantic検証
- CSV: `csv.DictReader()` → 辞書のリスト → Pydantic検証

---

## 7. 出力形式（TOML互換性マトリクス、Markdownレポート）

### Decision
TOMLは階層構造でモデル情報を出力、Markdownはプロバイダー別サマリーと推奨順位を含む。

### Rationale
- **再利用性**: TOML出力は後続の自動化スクリプトで読み込み可能
- **可読性**: Markdownレポートは人間が意思決定に利用
- **トレーサビリティ**: 検証日時、総コスト、制約事項を記録（FR-011、FR-013）

### Output Structure

#### TOML互換性マトリクス
```toml
[validation_metadata]
validated_at = "2025-10-22T10:30:00Z"
total_models = 65
total_cost_usd = "0.85"

[[models]]
provider = "google"
model_id = "gemini-2.5-flash"
name = "Gemini 2.5 Flash"
version = "stable"

[models.compatibility]
plain = true
web_search = false
code_exec = true
pydantic_ai_category = "google"

[models.metrics]
success = true
latency_p50_ms = 245.3
latency_p95_ms = 892.1
latency_p99_ms = 1205.7
input_tokens = 128
output_tokens = 512

[models.recommendation]
rank = "⭐⭐⭐"
cost_performance = "high"
```

#### Markdownレポート
```markdown
# LLMモデル互換性検証レポート

**検証日時**: 2025-10-22 10:30:00 UTC
**総コスト**: $0.85
**検証モデル数**: 65

## プロバイダー別サマリー

### Google
- **対象モデル数**: 25
- **成功率**: 96%（24/25）
- **推奨モデル**: gemini-2.5-flash (⭐⭐⭐)

## 推奨順位

1. ⭐⭐⭐ gemini-2.5-flash (Google) - コストパフォーマンス: 高
2. ⭐⭐⭐ claude-sonnet-4-5-20250929 (Anthropic) - コストパフォーマンス: 高
3. ⭐⭐ gpt-4o (OpenAI) - コストパフォーマンス: 中
```

---

## 8. Article 9（データ正確性）の厳格な遵守

### Decision
すべての設定値を環境変数またはTOML設定で管理し、マジックナンバー・暗黙的フォールバックを完全に排除する。

### Prohibited Patterns
```python
# ❌ Article 9違反
DEFAULT_COST_LIMIT = 1.00  # ハードコード
if not config:
    config = {}  # 暗黙的フォールバック
```

### Compliant Patterns
```python
# ✅ Article 9準拠
from decimal import Decimal
import os

DEFAULT_COST_LIMIT = Decimal(os.getenv("MIXSEEK_COST_LIMIT", "1.00"))

if not config:
    raise ValueError("Configuration is required and must not be empty")
```

### Environment Variables
- `MIXSEEK_COST_LIMIT`: コスト上限（デフォルト: 1.00）
- `MIXSEEK_MAX_RETRIES`: 最大リトライ回数（デフォルト: 3）
- `MIXSEEK_RETRY_BASE_DELAY`: リトライ基本遅延秒数（デフォルト: 1.0）
- `MIXSEEK_VALIDATION_TIMEOUT`: 検証タイムアウト秒数（デフォルト: 120）

**Reference**: `src/mixseek/models/member_agent.py::EnvironmentConfig`（BaseSettings使用パターン）

---

## 9. Pydantic AI Output Typeとリフレクション

### Research Question
Pydantic AIの構造化出力とReflection機能をどのように活用するか？

### Findings (from draft/references/pydantic-ai-docs/output.md)
- **Output Type**: `Agent`の`output_type`パラメータでPydantic Modelを指定可能
- **自動リトライ**: `ValidationError`発生時、Pydantic AIがLLMに自動的にフィードバックして再試行
- **型安全性**: 出力が必ずPydantic Modelの制約を満たす

### Decision
本機能（モデル検証）では、LLM出力の構造化は不要。理由:
- モデル検証はプログラマティックなAPI呼び出しであり、LLMの自然言語生成を利用しない
- Pydantic AIの`Agent`は使用せず、`create_authenticated_model`で取得したモデルに直接API呼び出し

### Alternative Use Case
将来的に「検証結果の自然言語サマリー生成」機能を追加する場合は、以下のパターンを検討:
```python
from pydantic import BaseModel
from pydantic_ai import Agent

class ValidationSummary(BaseModel):
    overall_status: str
    key_findings: list[str]
    recommendations: list[str]

agent = Agent(model="gemini-2.5-flash", output_type=ValidationSummary)
summary = await agent.run(validation_results)
```

**Reference**: `draft/references/pydantic-ai-docs/output.md`, `draft/references/pydantic-ai-docs/examples/pydantic-model.md`

---

## 10. テスト戦略とマーカー

### Decision
pytest markersを使用して、unit/integration/e2e/contractテストを明確に分離する。

### Test Markers (from pyproject.toml)
- `@pytest.mark.unit`: 高速、外部依存なし、モック使用
- `@pytest.mark.integration`: 中速、外部サービスモック
- `@pytest.mark.e2e`: 低速、実APIコール、コスト発生
- `@pytest.mark.contract`: APIインターフェース検証

### Test Coverage Requirements
- **ユニットテスト**: カバレッジ95%以上
- **インテグレーションテスト**: 主要フロー（抽出→互換性判定→API検証→レポート生成）
- **E2Eテスト**: コスト制約により最小限（成功ケース1件、失敗ケース1件）
- **コントラクトテスト**: CLI引数解析、入出力フォーマット検証

**Reference**: `pyproject.toml:81-87`, `tests/unit/test_member_agent_config.py`

---

## Summary

| 項目 | 決定事項 | 根拠 |
|------|----------|------|
| データモデル | Pydantic BaseModel | Article 16, 既存パターン |
| 認証 | create_authenticated_model再利用 | Article 10（DRY） |
| 検証 | ConfigValidator段階的パターン | 既存実装の一貫性 |
| API呼び出し | 非同期+指数バックオフ | SC-003, FR-008 |
| コスト追跡 | Decimal型、明示的エラー | Article 9 |
| 入力形式 | TOML/JSON/CSV統一処理 | FR-004 |
| 出力形式 | TOML+Markdown | FR-012, FR-013 |
| 環境変数 | pydantic-settings BaseSettings | Article 9, 既存パターン |
| テスト | pytest markers分離 | 既存テスト戦略 |

**全ての技術選択はArticle 9（データ正確性）、Article 10（DRY原則）、Article 16（型安全性）を厳格に遵守する。**
