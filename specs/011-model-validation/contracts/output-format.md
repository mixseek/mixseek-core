# Contract: Output Format

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: TOML互換性マトリクスとMarkdownレポートの構造仕様

## Functional Requirements
- FR-012: 互換性マトリクス（TOML）を生成
- FR-013: Markdownレポートを生成

---

## 1. TOML Compatibility Matrix

### File Name
`compatibility-matrix.toml`

### Structure
```toml
[validation_metadata]
validated_at = "2025-10-22T12:34:56Z"
total_models = 65
successful_validations = 62
failed_validations = 3
total_cost_usd = "0.85"

# Model 1
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
function_calling_supported = true

[models.metrics]
success = true
latency_p50_ms = 245.3
latency_p95_ms = 892.1
latency_p99_ms = 1205.7
input_tokens = 128
output_tokens = 512
retry_count = 0
estimated_cost_usd = "0.0152"
validated_at = "2025-10-22T12:35:10Z"

[models.recommendation]
rank = "⭐⭐⭐"
cost_performance = "high"
limitations = []
notes = "Recommended for production use"

# Model 2
[[models]]
provider = "openai"
model_id = "gpt-4o"
name = "GPT-4o"
version = "stable"

[models.compatibility]
plain = true
web_search = false
code_exec = false
pydantic_ai_category = "openai"
function_calling_supported = true

[models.metrics]
success = true
latency_p50_ms = 512.8
latency_p95_ms = 1452.3
latency_p99_ms = 2103.5
input_tokens = 128
output_tokens = 512
retry_count = 1
estimated_cost_usd = "0.0325"
validated_at = "2025-10-22T12:36:22Z"

[models.recommendation]
rank = "⭐⭐"
cost_performance = "medium"
limitations = ["High latency", "Higher cost"]
notes = "Suitable for non-time-critical tasks"

# Model 3 (Failed validation)
[[models]]
provider = "anthropic"
model_id = "claude-opus-4-1"
name = "Claude Opus 4.1"
version = "stable"

[models.compatibility]
plain = true
web_search = false
code_exec = true
pydantic_ai_category = "anthropic"
function_calling_supported = false

[models.metrics]
success = false
error_type = "AuthenticationError"
error_message = "Invalid API key"
retry_count = 3
validated_at = "2025-10-22T12:37:45Z"

[models.recommendation]
rank = "⭐"
cost_performance = "low"
limitations = ["Authentication failed", "Validation incomplete"]
notes = "Check API credentials"
```

### Top-Level Metadata

#### `[validation_metadata]`
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `validated_at` | string (ISO 8601) | 検証実行日時（UTC） | `"2025-10-22T12:34:56Z"` |
| `total_models` | int | 検証対象総数 | `65` |
| `successful_validations` | int | 検証成功数 | `62` |
| `failed_validations` | int | 検証失敗数 | `3` |
| `total_cost_usd` | string (Decimal) | 累計コスト | `"0.85"` |

### Per-Model Structure

#### `[[models]]` (Root)
| Field | Type | Description |
|-------|------|-------------|
| `provider` | string | プロバイダー名 |
| `model_id` | string | モデルID |
| `name` | string | モデル表示名 |
| `version` | string | バージョン分類 |

#### `[models.compatibility]` (FR-005, FR-006)
| Field | Type | Description |
|-------|------|-------------|
| `plain` | bool | plainエージェント対応 |
| `web_search` | bool | web-searchエージェント対応 |
| `code_exec` | bool | code-execエージェント対応 |
| `pydantic_ai_category` | string | Pydantic AIカテゴリ |
| `function_calling_supported` | bool | Function calling対応 |

#### `[models.metrics]` (FR-007, FR-008)
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `success` | bool | 検証成功フラグ | Yes |
| `error_type` | string | エラー種別 | No (if success=false) |
| `error_message` | string | エラーメッセージ | No (if success=false) |
| `latency_p50_ms` | float | P50レイテンシ（ms） | No (if success=true) |
| `latency_p95_ms` | float | P95レイテンシ（ms） | No (if success=true) |
| `latency_p99_ms` | float | P99レイテンシ（ms） | No (if success=true) |
| `input_tokens` | int | 入力トークン数 | No (if success=true) |
| `output_tokens` | int | 出力トークン数 | No (if success=true) |
| `retry_count` | int | リトライ回数 | Yes |
| `estimated_cost_usd` | string | 推定コスト | No |
| `validated_at` | string (ISO 8601) | 検証日時 | Yes |

#### `[models.recommendation]` (FR-012)
| Field | Type | Description |
|-------|------|-------------|
| `rank` | string | 推奨度ランク（⭐⭐⭐/⭐⭐/⭐） |
| `cost_performance` | string | コストパフォーマンス（high/medium/low） |
| `limitations` | array[string] | 制約事項リスト |
| `notes` | string | 備考 |

---

## 2. Markdown Validation Report

### File Name
`validation-report.md`

### Structure
```markdown
# LLMモデル互換性検証レポート

**検証日時**: 2025-10-22 12:34:56 UTC
**総コスト**: $0.85
**検証モデル数**: 65 (成功: 62, 失敗: 3)

---

## プロバイダー別サマリー

### Google
- **対象モデル数**: 25
- **成功率**: 96% (24/25)
- **平均レイテンシ（P50）**: 312.5 ms
- **平均コスト**: $0.0145
- **推奨モデル**: gemini-1.5-pro, gemini-1.5-flash

### OpenAI
- **対象モデル数**: 20
- **成功率**: 90% (18/20)
- **平均レイテンシ（P50）**: 485.3 ms
- **平均コスト**: $0.0298
- **推奨モデル**: gpt-4-turbo

### Anthropic
- **対象モデル数**: 20
- **成功率**: 100% (20/20)
- **平均レイテンシ（P50）**: 398.7 ms
- **平均コスト**: $0.0189
- **推奨モデル**: claude-3-5-sonnet, claude-3-5-haiku

---

## 推奨順位

### ⭐⭐⭐ 高推奨（本番環境推奨）

| Rank | Model ID | Provider | Cost/1K tokens | P50 Latency | 対応エージェント |
|------|----------|----------|----------------|-------------|-----------------|
| 1 | gemini-2.5-flash | Google | $0.0152 | 245.3 ms | plain, code-exec |
| 2 | claude-sonnet-4-5-20250929 | Anthropic | $0.0189 | 398.7 ms | plain, code-exec |
| 3 | gemini-2.5-pro | Google | $0.0098 | 189.2 ms | plain, code-exec |

### ⭐⭐ 中推奨（検証環境推奨）

| Rank | Model ID | Provider | Cost/1K tokens | P50 Latency | 対応エージェント |
|------|----------|----------|----------------|-------------|-----------------|
| 4 | gpt-4o | OpenAI | $0.0325 | 512.8 ms | plain |
| 5 | claude-haiku-4-5 | Anthropic | $0.0142 | 295.1 ms | plain, code-exec |

### ⭐ 低推奨（制約あり）

| Rank | Model ID | Provider | 制約事項 |
|------|----------|----------|---------|
| 6 | o1 | OpenAI | 高レイテンシ（P95: 2.1s） |
| 7 | claude-opus-4-1 | Anthropic | 高コスト（$0.075/1K tokens） |

---

## 制約事項

### 全般
- web-searchエージェントに対応したモデルは現在ありません（全モデルで非対応）
- レート制限により3回リトライしたモデル: 5件

### Google
- （なし）

### OpenAI
- （なし）

### Anthropic
- （なし）

---

## 詳細メトリクス

### レイテンシ分布

| Provider | P50 (ms) | P95 (ms) | P99 (ms) |
|----------|----------|----------|----------|
| Google   | 312.5    | 985.2    | 1523.8   |
| OpenAI   | 485.3    | 1452.3   | 2103.5   |
| Anthropic| 398.7    | 1102.4   | 1687.9   |

### コスト分布

| Provider | 平均コスト/1K tokens | 最小 | 最大 |
|----------|---------------------|------|------|
| Google   | $0.0145             | $0.0098 | $0.0235 |
| OpenAI   | $0.0298             | $0.0215 | $0.0425 |
| Anthropic| $0.0189             | $0.0142 | $0.0451 |

---

## エラーサマリー

| Error Type | Count | Affected Models |
|------------|-------|-----------------|
| AuthenticationError | 0 | - |
| RateLimitError | 2 | gpt-3.5-turbo (x2) |
| TimeoutError | 1 | gpt-4o-mini |

---

## 検証環境

- **検証ツールバージョン**: mixseek-core 0.1.0
- **Python**: 3.13.9
- **Pydantic AI**: 0.0.8
- **検証タイムアウト**: 120秒
- **最大並列数**: 5
- **最大リトライ回数**: 3

---

**生成日時**: 2025-10-22 12:45:30 UTC
**レポート形式バージョン**: 1.0.0
```

### Sections

#### 1. Header
- 検証日時（UTC）
- 総コスト
- 検証モデル数（成功/失敗内訳）

#### 2. プロバイダー別サマリー
- 対象モデル数
- 成功率
- 平均レイテンシ（P50）
- 平均コスト
- 推奨モデルリスト

#### 3. 推奨順位（FR-012, FR-013）
- ⭐⭐⭐: 本番環境推奨
- ⭐⭐: 検証環境推奨
- ⭐: 制約あり

#### 4. 制約事項
- 全般的な制約
- プロバイダー別の制約

#### 5. 詳細メトリクス
- レイテンシ分布（P50/P95/P99）
- コスト分布

#### 6. エラーサマリー
- エラー種別ごとの集計
- 影響を受けたモデル

#### 7. 検証環境
- ツールバージョン
- 設定値

---

## 3. Output Generation Logic

### TOML Generation (Pydantic → TOML)
```python
import tomllib
from pathlib import Path
from decimal import Decimal

def generate_toml_matrix(
    reports: list[RecommendationReport],
    metadata: dict,
    output_path: Path,
) -> None:
    """TOML互換性マトリクスを生成"""
    toml_data = {
        "validation_metadata": {
            "validated_at": metadata["validated_at"].isoformat() + "Z",
            "total_models": len(reports),
            "successful_validations": sum(
                1 for r in reports if r.metrics and r.metrics.success
            ),
            "failed_validations": sum(
                1 for r in reports if not r.metrics or not r.metrics.success
            ),
            "total_cost_usd": str(
                sum(r.estimated_cost_usd for r in reports)
            ),
        },
        "models": [
            {
                "provider": r.provider,
                "model_id": r.model_id,
                "name": r.name,
                "version": r.compatibility.pydantic_ai_category,  # FIXME
                "compatibility": {
                    "plain": r.compatibility.plain_compatible,
                    "web_search": r.compatibility.web_search_compatible,
                    "code_exec": r.compatibility.code_exec_compatible,
                    "pydantic_ai_category": r.compatibility.pydantic_ai_category,
                    "function_calling_supported": r.compatibility.function_calling_supported,
                },
                "metrics": (
                    {
                        "success": r.metrics.success,
                        "latency_p50_ms": r.metrics.latency_p50_ms,
                        # ... (other fields)
                    }
                    if r.metrics
                    else {}
                ),
                "recommendation": {
                    "rank": r.recommendation_rank,
                    "cost_performance": r.cost_performance,
                    "limitations": r.limitations,
                    "notes": r.notes,
                },
            }
            for r in reports
        ],
    }

    # Write TOML (using tomli_w in actual implementation)
    with output_path.open("w") as f:
        tomli_w.dump(toml_data, f)
```

### Markdown Generation
```python
def generate_markdown_report(
    reports: list[RecommendationReport],
    metadata: dict,
    output_path: Path,
) -> None:
    """Markdownレポートを生成"""
    md_lines = [
        "# LLMモデル互換性検証レポート",
        "",
        f"**検証日時**: {metadata['validated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**総コスト**: ${metadata['total_cost_usd']}",
        f"**検証モデル数**: {len(reports)} (成功: {metadata['successful']}, 失敗: {metadata['failed']})",
        "",
        "---",
        "",
        "## プロバイダー別サマリー",
        "",
    ]

    # Provider summaries...
    # Recommendation rankings...
    # Detailed metrics...

    with output_path.open("w") as f:
        f.write("\n".join(md_lines))
```

---

## 4. Contract Tests

### Test Cases
1. **T-OUT-001**: TOML生成 → Valid TOML syntax
2. **T-OUT-002**: TOML生成 → All required fields present
3. **T-OUT-003**: Markdown生成 → Valid Markdown syntax
4. **T-OUT-004**: Markdown生成 → All sections present
5. **T-OUT-005**: Empty input → Minimal valid output
6. **T-OUT-006**: Failed validations → Error information included

**Implementation**: `tests/contract/test_output_format.py`
