---
name: mixseek-model-list
description: MixSeek-Coreで利用可能なLLMモデルの一覧を表示します。「使えるモデル」「モデル一覧」「どのモデルがある」「モデルを取得」「APIからモデル」といった依頼で使用してください。API経由でプロバイダー別のモデル情報を動的取得し、推奨設定、互換性情報を提供します。
---

# MixSeek モデル一覧

## 概要

MixSeek-Coreで利用可能なLLMモデルの一覧を提供します。API経由で最新のモデル情報を動的に取得し、プロバイダー別のモデル情報、用途別の推奨設定、agent_typeとの互換性情報を確認できます。

**FR-008準拠**: Google Gemini、Anthropic Claude、OpenAI、Grokの各プロバイダーからAPI経由でモデル一覧を取得。APIが利用できない場合は`docs/data/valid-models.csv`からフォールバック取得します。

## 前提条件

### 環境変数（API取得に必要）

APIからモデル一覧を取得する場合、対応する環境変数を設定:

| プロバイダー | 環境変数 |
|-------------|---------|
| Google | `GOOGLE_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Grok | `GROK_API_KEY` |

**注意**: 環境変数が未設定の場合は、該当プロバイダーのみフォールバック（静的CSV）を使用します。

## 使用方法

### Step 1: 環境変数の確認

APIキーが設定されているか確認:

```bash
# 設定状況を確認
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:+設定済み}"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+設定済み}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+設定済み}"
echo "GROK_API_KEY: ${GROK_API_KEY:+設定済み}"
```

### Step 2: 要件の確認

ユーザーの用途を確認:

1. **全モデル一覧**: すべてのプロバイダーのモデルを表示
2. **プロバイダー指定**: 特定プロバイダーのモデルのみ表示
3. **用途別推奨**: Leader/Member/Evaluator等の用途に適したモデル
4. **API経由取得**: 最新のモデル情報をAPIから取得

### Step 3: モデル情報の取得

**スクリプトによるAPI取得（推奨）:**

```bash
# 全プロバイダーからモデル取得（MixSeek形式）
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py

# 特定プロバイダーのみ
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --provider google

# JSON形式で出力
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --json

# 詳細出力（フォールバック使用状況を表示）
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --verbose --format text

# フォールバックのみ使用（APIスキップ）
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --fallback-only
```

**静的参照（APIが利用できない場合）:**

`docs/data/valid-models.csv` からフォールバックデータを取得。

## CLIコマンドリファレンス

```
fetch-models.py [OPTIONS]

OPTIONS:
  --provider TEXT    プロバイダー指定: google, anthropic, openai, grok, all
                     (default: all)
  --format TEXT      出力形式: text, json, csv, mixseek
                     (default: mixseek)
  --json             --format json のショートカット
  --fallback-only    APIをスキップし、フォールバックのみ使用
  --verbose, -v      詳細出力（フォールバック使用状況を表示）
```

### 出力形式

| 形式 | 説明 | 用途 |
|------|------|------|
| `mixseek` | `provider:model-id` 形式（1行1モデル） | チーム設定への直接コピー |
| `json` | JSON形式（メタデータ含む） | プログラム連携 |
| `text` | プロバイダー別の詳細表示 | 人間が読む用 |
| `csv` | CSV形式 | スプレッドシート等 |

## モデル形式

MixSeek-Coreでは以下の形式でモデルを指定します:

```
provider:model-name
```

| プロバイダー | プレフィックス | 環境変数 |
|-------------|---------------|---------|
| Google | `google-gla` | `GOOGLE_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Grok | `grok` | `GROK_API_KEY` |

**利用可能なモデル一覧は `fetch-models.py` スクリプトで取得してください。**

## プロバイダー特性

| プロバイダー | 特徴 |
|-------------|------|
| Google | 高品質・安定。Leader Agent / Evaluator向け |
| Anthropic | `code_execution` agent_type に完全対応 |
| OpenAI | 安定・汎用性が高い |
| Grok | Web検索機能内蔵モデルあり |

## 用途別推奨

### Leader Agent

タスクの調整・指示を行うリーダー向け。高品質（`-pro`系）なモデルを推奨。

### Member Agent

タスク実行を担当するメンバー向け。高速・コスト効率（`-flash`、`-mini`系）を推奨。

### code_execution Agent

コード実行が必要な場合。**Anthropicモデルのみ対応**。

### Evaluator / Judgment

評価・判定向け。安定性・一貫性のある高品質モデルを推奨。

## agent_type互換性

| agent_type | Google | Anthropic | OpenAI | Grok |
|------------|--------|-----------|--------|------|
| `plain` | ✓ | ✓ | ✓ | ✓ |
| `web_search` | ✓ | ✓ | ✓ | ✓ |
| `code_execution` | ✗ | ✓ | ✗ | ✗ |
| `web_fetch` | ✓ | ✓ | ✓ | ✓ |
| `custom` | ✓ | ✓ | ✓ | ✓ |

**注意**: `code_execution`はAnthropicモデルのみ対応

## 例

### 全モデル一覧の取得

```bash
# スクリプトを実行してAPIから最新のモデル一覧を取得
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --format text
```

出力例:
```
[GOOGLE]
  Prefix: google-gla
  Models:
    - gemini-2.5-pro: Gemini 2.5 Pro
    - gemini-2.5-flash: Gemini 2.5 Flash
    ...

[ANTHROPIC]
  Prefix: anthropic
  Models:
    - claude-sonnet-4-5-...: Claude Sonnet 4.5 [code_exec]
    ...
```

### code_execution対応モデルの確認

```bash
# JSON形式で取得し、code_exec_compatible を確認
.skills/detect-python-command/scripts/run-python.sh \
    .skills/mixseek-model-list/scripts/fetch-models.py --provider anthropic --json
```

**ポイント**: `code_exec_compatible: true` のモデルが `code_execution` agent_type に対応

### チーム設定での使用例

```toml
[[team.members]]
agent_name = "coder"
agent_type = "code_execution"
model = "anthropic:<model-id>"  # fetch-models.py で取得したモデルIDを使用
```

## トラブルシューティング

### APIキーエラー（fetch-models.py）

```
Warning: GOOGLE_API_KEY not set, using fallback for google
```

**解決方法**:
対応する環境変数を設定:
```bash
export GOOGLE_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
export OPENAI_API_KEY="your-api-key"
export GROK_API_KEY="your-api-key"
```

### API接続エラー

```
Warning: API fetch failed for google: <urlopen error ...>, using fallback
```

**原因と解決方法**:
- ネットワーク接続を確認
- プロキシ設定を確認（企業環境の場合）
- APIキーの有効性を確認
- フォールバックが自動で使用されるため、処理は継続されます

### API認証エラー（401/403）

```
Warning: API fetch failed for openai: HTTP Error 401: Unauthorized
```

**解決方法**:
- APIキーが正しく設定されているか確認
- APIキーの有効期限を確認
- APIキーの権限（スコープ）を確認

### タイムアウトエラー

```
Warning: API fetch failed for anthropic: timed out
```

**解決方法**:
- ネットワーク接続を確認
- 後で再試行
- `--fallback-only` オプションでフォールバックを使用

### MixSeek設定時のAPIキーエラー

```
Error: API key not found for provider: google-gla
```

**解決方法**:
対応する環境変数を設定してからMixSeekを実行

### モデルが見つからない

```
Error: Unknown model: invalid-model
```

**解決方法**:
- `provider:model-name` 形式を確認
- 有効なモデル名を使用（このスキルで確認）

### code_execution非対応エラー

```
Error: code_execution not supported for model: google-gla:...
```

**解決方法**:
- Anthropicモデルに変更（`code_execution`はAnthropicのみ対応）
- `fetch-models.py --provider anthropic` で対応モデルを確認

## 参照

- スクリプト: `scripts/fetch-models.py`
- フォールバックデータ: `docs/data/valid-models.csv`
- チーム設定: `.skills/mixseek-team-config/`
- 評価設定: `.skills/mixseek-evaluator-config/`
