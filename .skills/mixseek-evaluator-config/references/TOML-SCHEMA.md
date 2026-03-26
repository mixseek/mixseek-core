# Evaluator/Judgment Configuration TOML Schema

## 概要

評価設定ファイル（evaluator.toml）と判定設定ファイル（judgment.toml）のスキーマ定義です。

## ファイル配置

- Evaluator: `$MIXSEEK_WORKSPACE/configs/evaluators/evaluator.toml`
- Judgment: `$MIXSEEK_WORKSPACE/configs/judgment/judgment.toml`

---

## Evaluator Configuration (evaluator.toml)

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `default_model` | string | デフォルトの評価モデル（形式: `provider:model-name`） |
| `[[metrics]]` | array | 評価メトリクス（1つ以上） |
| `metrics[].name` | string | メトリクス名 |

### オプションフィールド

#### ルートレベル

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `temperature` | float | 0.0 | 0.0-2.0 | 生成の多様性 |
| `max_tokens` | integer | - | >0 | 最大トークン数 |
| `max_retries` | integer | 3 | >=0 | リトライ回数 |
| `timeout_seconds` | integer | 300 | >0 | タイムアウト秒数 |
| `top_p` | float | - | 0.0-1.0 | トップP |
| `seed` | integer | - | - | 乱数シード |
| `stop_sequences` | array[string] | - | - | 停止シーケンス |

#### [[metrics]] セクション

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `weight` | float | 均等 | 0.0-1.0 | メトリクスの重み |
| `model` | string | default_model | - | メトリクス固有モデル |
| `system_instruction` | string | - | - | カスタム指示 |
| `temperature` | float | 親設定 | 0.0-2.0 | メトリクス固有temperature |
| `max_tokens` | integer | 親設定 | >0 | メトリクス固有max_tokens |
| `max_retries` | integer | 親設定 | >=0 | メトリクス固有リトライ |
| `timeout_seconds` | integer | 親設定 | >0 | メトリクス固有タイムアウト |

### 標準メトリクス名

| 名前 | 説明 |
|------|------|
| `ClarityCoherence` | 回答の明確性と一貫性を評価 |
| `Coverage` | 質問に対するカバレッジを評価 |
| `Relevance` | 回答の関連性を評価 |

### バリデーションルール

```python
# 重み付けバリデーション
weights = [m.weight for m in metrics if m.weight is not None]

if len(weights) > 0:
    # 全て指定必須
    assert len(weights) == len(metrics), "All metrics must have weights"
    # 合計1.0
    assert 0.999 <= sum(weights) <= 1.001, f"Weights must sum to 1.0"
```

### 設定例

#### 最小構成

```toml
default_model = "google-gla:gemini-2.5-pro"

[[metrics]]
name = "ClarityCoherence"

[[metrics]]
name = "Coverage"

[[metrics]]
name = "Relevance"
```

#### 標準構成

```toml
default_model = "google-gla:gemini-2.5-pro"
temperature = 0.0
timeout_seconds = 300
max_retries = 3

[[metrics]]
name = "ClarityCoherence"
weight = 0.34

[[metrics]]
name = "Coverage"
weight = 0.33

[[metrics]]
name = "Relevance"
weight = 0.33
```

#### フル構成

```toml
default_model = "google-gla:gemini-2.5-pro"
temperature = 0.0
max_tokens = 2000
timeout_seconds = 300
max_retries = 3
top_p = 0.9
seed = 42
stop_sequences = ["[END]"]

[[metrics]]
name = "ClarityCoherence"
weight = 0.4
model = "anthropic:claude-sonnet-4-5-20250929"
system_instruction = """
回答の明確性と論理的一貫性を0-100で評価してください。
評価観点:
1. 文章構造の明確さ
2. 論理的な流れ
3. 結論の明確さ
"""
temperature = 0.0
max_tokens = 1000
timeout_seconds = 120

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3
```

---

## Judgment Configuration (judgment.toml)

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `model` | string | 判定モデル（形式: `provider:model-name`） |

### オプションフィールド

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `temperature` | float | 0.0 | 0.0-2.0 | 生成の多様性（0.0推奨） |
| `max_tokens` | integer | 1000 | >0 | 最大トークン数 |
| `max_retries` | integer | 3 | >=0 | リトライ回数 |
| `timeout_seconds` | integer | 60 | >0 | タイムアウト秒数 |
| `top_p` | float | - | 0.0-1.0 | トップP |
| `seed` | integer | - | - | 乱数シード |
| `stop_sequences` | array[string] | - | - | 停止シーケンス |
| `system_instruction` | string | - | - | カスタム指示 |

### 設定例

#### 最小構成

```toml
model = "google-gla:gemini-2.5-pro"
```

#### 標準構成

```toml
model = "google-gla:gemini-2.5-pro"
temperature = 0.0
timeout_seconds = 60
max_retries = 3
```

#### フル構成

```toml
model = "google-gla:gemini-2.5-pro"
temperature = 0.0
max_tokens = 1000
timeout_seconds = 120
max_retries = 5
top_p = 0.9
seed = 42
stop_sequences = ["[DECISION]"]

system_instruction = """
あなたは公正な審判です。
提示された回答を比較し、以下の基準で最も優れた回答を選択してください:
1. 質問への的確さ
2. 情報の正確性
3. 説明の分かりやすさ
"""
```

---

## モデル形式

```
provider:model-name
```

### 推奨モデル

| 用途 | 推奨モデル | 理由 |
|------|-----------|------|
| Evaluator | `google-gla:gemini-2.5-pro` | 高品質な評価 |
| Judgment | `google-gla:gemini-2.5-pro` | 安定した判定 |
| 高精度評価 | `anthropic:claude-opus-4-1` | 最高品質 |

---

## 設定ファイル構成例

### 一般的なセットアップ

```
$MIXSEEK_WORKSPACE/
└── configs/
    ├── evaluators/
    │   └── evaluator.toml
    └── judgment/
        └── judgment.toml
```

### オーケストレーターとの連携

オーケストレーターは自動的にこれらの設定を読み込みます:

```toml
# orchestrator.toml
[orchestrator]
max_rounds = 5

[[orchestrator.teams]]
config = "configs/agents/team-a.toml"

# evaluator.toml と judgment.toml は
# configs/evaluators/ と configs/judgment/ から自動検出
```
