# Quickstart: LLMモデル互換性検証

**Date**: 2025-10-22
**Feature**: 036-model-validation
**Purpose**: 最小限の手順で検証機能を使い始めるためのガイド

## 概要

このツールは、llm-discoveryで取得したLLMモデル一覧から、mixseekの各エージェント種別（plain/web-search/code-exec）と互換性のあるモデルを特定し、オプションでAPI動作検証を行い、推奨モデルをレポート出力します。

**主な機能**:
- ✅ 143モデルから会話モデルを自動抽出（107モデル）
- ✅ mixseekエージェント種別との互換性判定
- ✅ Pydantic AIカテゴリのマッピング
- ✅ 個別モデル/プロバイダーフィルタリング
- ✅ オプションの実API検証（レイテンシ・トークン・コスト測定）
- ✅ TOML互換性マトリクス + Markdownレポート生成
- ✅ llm-discovery形式の完全対応

---

## 前提条件

### システム要件
- Python 3.13.9以上
- mixseek-core 0.1.0以上
- インターネット接続（API検証用）

### API認証情報
少なくとも1つのプロバイダーのAPI認証情報が必要です。Pydantic AIの標準環境変数を使用します。

#### Google Gemini API
```bash
export GOOGLE_API_KEY="AIzaSy..."
```

#### Vertex AI（Google Cloud）
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

#### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
```

#### Anthropic Claude
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**重要**: API キーは設定ファイルに記載せず、環境変数で設定してください。

---

## Step 1: 入力ファイルの準備

llm-discoveryコマンドで最新のモデルリストを取得します。

### モデルリストの生成

```bash
# TOML形式で出力
uvx llm-discovery export --format toml --output models.toml

# JSON形式で出力する場合
uvx llm-discovery export --format json --output models.json

# CSV形式で出力する場合
uvx llm-discovery export --format csv --output models.csv
```

生成されたファイルには、Google、OpenAI、Anthropicの全モデル（約143件）が含まれます。

**重要**: `llm-discovery`が生成するTOML形式（`[[providers]]`構造）は自動的に認識されます。そのまま使用できます。

### 既存のllm-models.tomlを使用する場合

```bash
# リポジトリ内のサンプルをそのまま使用
mixseek validate-models --input examples/llm-models.toml --skip-api-validation
```

### 生成されるTOML形式の例（シンプル形式）
```toml
[[models]]
provider = "google"
model_id = "gemini-2.5-flash"
name = "Gemini 2.5 Flash"
modality = "chat"
version = "stable"

[[models]]
provider = "openai"
model_id = "gpt-4o"
name = "GPT-4o"
modality = "chat"
version = "stable"

[[models]]
provider = "anthropic"
model_id = "claude-sonnet-4-5-20250929"
name = "Claude Sonnet 4.5"
modality = "chat"
version = "stable"
```

---

## Step 2: 基本的な検証実行

### 互換性判定のみ（APIコストなし、推奨）
```bash
mixseek validate-models --input models.toml --skip-api-validation
```

### 実行結果
```
[INFO] Loading models from: models.toml
[INFO] Found 3 models
[INFO] Extracting conversational models...
[INFO] Extracted 3 conversational models
[INFO] Starting compatibility check...
[INFO] Compatibility check completed: 3/3 compatible
[INFO] API validation skipped (--skip-api-validation)
[INFO] Generating reports...
[INFO] ✓ TOML matrix: validation-output/compatibility-matrix.toml
[INFO] ✓ Markdown report: validation-output/validation-report.md
[SUCCESS] Validation completed successfully
```

### 実API検証を含む完全な検証（コスト発生）
```bash
# APIキー設定後に実行
mixseek validate-models --input models.toml
```

### 実行結果（API検証あり）
```
[INFO] Loading models from: models.toml
[INFO] Found 3 models
[INFO] Extracting conversational models...
[INFO] Extracted 3 conversational models
[INFO] Starting compatibility check...
[INFO] Compatibility check completed: 3/3 compatible
[INFO] Starting API validation... (estimated models: 3)
[INFO] Validating 3 compatible models...
[INFO] API validation completed: 3/3 successful
[INFO] Total cost: $0.042
[INFO] Generating reports...
[INFO] ✓ TOML matrix: validation-output/compatibility-matrix.toml
[INFO] ✓ Markdown report: validation-output/validation-report.md
[SUCCESS] Validation completed successfully
```

---

## Step 3: 結果の確認

### TOML互換性マトリクス
```bash
cat ./validation-output/compatibility-matrix.toml
```

出力例:
```toml
[validation_metadata]
validated_at = "2025-10-22T15:30:00Z"
total_models = 3
successful_validations = 3
total_cost_usd = "0.042"

[[models]]
provider = "google"
model_id = "gemini-2.5-flash"
name = "Gemini 2.5 Flash"

[models.compatibility]
plain = true
code_exec = true
pydantic_ai_category = "google"

[models.metrics]
success = true
latency_p50_ms = 245.3

[models.recommendation]
rank = "⭐⭐⭐"
cost_performance = "high"
```

### Markdownレポート
```bash
cat ./validation-output/validation-report.md
```

出力例:
```markdown
# LLMモデル互換性検証レポート

**検証日時**: 2025-10-22 15:30:00 UTC
**総コスト**: $0.042
**検証モデル数**: 3 (成功: 3, 失敗: 0)

## 推奨順位

### ⭐⭐⭐ 高推奨

| Rank | Model ID | Provider | Cost/1K tokens | P50 Latency |
|------|----------|----------|----------------|-------------|
| 1 | gemini-2.5-flash | Google | $0.0152 | 245.3 ms |
| 2 | claude-sonnet-4-5-20250929 | Anthropic | $0.0189 | 398.7 ms |
| 3 | gpt-4o | OpenAI | $0.0325 | 512.8 ms |
```

---

## 高度な使用例

### 個別モデルの検証

#### 単一モデルのみ検証（完全一致）
```bash
# 特定の1モデルだけを検証
mixseek validate-models \
  --input examples/llm-models.toml \
  --exact-model "gemini-2.5-flash"
```

#### プロバイダーで絞り込み
```bash
# Anthropicモデルのみ検証
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "anthropic"
```

#### 部分一致で複数モデル
```bash
# "gemini-2.5-flash"を含む全モデルを検証
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-model "gemini-2.5-flash"
```

#### 複合フィルター
```bash
# GoogleプロバイダーのProモデルのみ
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "google" \
  --filter-model "pro"
```

---

### 実API検証の実行

#### 単一モデルのAPI検証（コスト最小）
```bash
export GOOGLE_API_KEY="AIzaSy..."

mixseek validate-models \
  --input examples/llm-models.toml \
  --exact-model "gemini-2.5-flash" \
  --cost-limit 0.10
```

#### プロバイダー単位のAPI検証
```bash
export ANTHROPIC_API_KEY="sk-ant-..."

mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "anthropic"
```

---

### その他のオプション

#### カスタム出力ディレクトリ
```bash
mixseek validate-models \
  --input models.toml \
  --output ./results/2025-10-22/
```

#### コスト上限の設定
```bash
mixseek validate-models \
  --input models.toml \
  --cost-limit 5.00
```

#### 詳細ログ出力
```bash
mixseek validate-models \
  --input models.toml \
  --verbose  # or -v, -vv for more verbosity
```

---

## よくある質問

### Q1: 「Cost limit exceeded」エラーが出た
**回答**: コスト上限に到達しました。`--cost-limit`オプションで上限を増やすか、検証対象モデル数を減らしてください。

```bash
# コスト上限を10ドルに設定
mixseek validate-models --input models.toml --cost-limit 10.00
```

### Q2: 「Authentication failed」エラーが出た
**回答**: API認証情報が未設定または無効です。環境変数を確認してください。

```bash
# Google Gemini API
export GOOGLE_API_KEY="AIzaSy..."

# Vertex AI（Google Cloud）
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"

# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

API キーが正しく設定されているか確認:
```bash
# Google Gemini API
echo $GOOGLE_API_KEY

# Vertex AI の場合
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# OpenAI
echo $OPENAI_API_KEY

# Anthropic
echo $ANTHROPIC_API_KEY
```

### Q3: 特定のプロバイダーや個別モデルのみ検証したい
**回答**: フィルターオプションを使用してください。

```bash
# 特定プロバイダーのみ
mixseek validate-models --input examples/llm-models.toml --filter-provider "google"

# 特定モデルのみ（完全一致）
mixseek validate-models --input examples/llm-models.toml --exact-model "gemini-2.5-flash"

# 部分一致（複数モデル）
mixseek validate-models --input examples/llm-models.toml --filter-model "claude"

# 複合フィルター
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "google" \
  --filter-model "pro"
```

**フィルターオプション**:
- `--filter-provider`: プロバイダー指定（google/openai/anthropic）
- `--filter-model`: モデルID部分一致
- `--exact-model`: モデルID完全一致

### Q4: CSV形式の入力ファイルを使用したい
**回答**: CSV形式もサポートしています。

```csv
provider,model_id,name,modality,version
google,gemini-2.5-flash,Gemini 2.5 Flash,chat,stable
openai,gpt-4o,GPT-4o,chat,stable
```

```bash
mixseek validate-models --input models.csv
```

### Q5: llm-discovery形式のファイルをそのまま使いたい
**回答**: 完全対応しています。`examples/llm-models.toml`をそのまま使用できます。

```bash
# llm-discoveryで生成したファイルをそのまま使用
uvx llm-discovery export --format toml --output models.toml
mixseek validate-models --input models.toml --skip-api-validation
```

**対応形式**:
- シンプル形式: `[[models]]`
- llm-discovery形式: `[[providers]] → [[providers.models]]`（自動検出）

### Q6: 最新のモデル情報を取得したい
**回答**: 検証の直前に`llm-discovery`コマンドを実行して、最新のモデルリストを取得してください。

```bash
# 最新のモデル情報を取得
uvx llm-discovery export --format toml --output models.toml

# すぐに検証を実行
mixseek validate-models --input models.toml --skip-api-validation
```

**重要**: モデル情報は頻繁に更新されるため、古いファイルを使い回さず、検証の都度最新データを取得することを推奨します。

### Q7: APIコストを最小化したい
**回答**: 以下の方法でコストを削減できます。

```bash
# 方法1: 互換性判定のみ（API呼び出しなし、コスト$0）
mixseek validate-models --input models.toml --skip-api-validation

# 方法2: 単一モデルのみAPI検証
mixseek validate-models \
  --input examples/llm-models.toml \
  --exact-model "gemini-2.5-flash" \
  --cost-limit 0.01

# 方法3: プロバイダー限定
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "google" \
  --cost-limit 0.50
```

### Q8: 環境変数でデフォルト設定を変更したい
**回答**: 以下の環境変数が利用可能です。

```bash
export MIXSEEK_COST_LIMIT_USD=5.00
export MIXSEEK_MAX_RETRIES=5
export MIXSEEK_RETRY_BASE_DELAY=2.0
export MIXSEEK_VALIDATION_TIMEOUT=300
export MIXSEEK_MAX_CONCURRENT_VALIDATIONS=10
```

---

## トラブルシューティング

### 大量のモデル検証でコストが心配
```
[INFO] Validating 107 compatible models...
```

**対処法**: フィルターで絞り込むか、互換性判定のみ実行:
```bash
# 方法1: 互換性判定のみ（コスト$0）
mixseek validate-models --input examples/llm-models.toml --skip-api-validation

# 方法2: 単一モデルのみAPI検証
mixseek validate-models \
  --input examples/llm-models.toml \
  --exact-model "gemini-2.5-flash" \
  --cost-limit 0.01

# 方法3: プロバイダー限定
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "google" \
  --cost-limit 0.50
```

### レート制限エラー
```
[ERROR] Rate limit exceeded, retrying in 2.0s... (attempt 1/3)
```

**対処法**: 自動リトライが実行されます。リトライ回数を増やす場合:
```bash
export MIXSEEK_MAX_RETRIES=5
mixseek validate-models --input models.toml
```

### タイムアウトエラー
```
[ERROR] Validation timeout after 120s
```

**対処法**: タイムアウト時間を延長:
```bash
export MIXSEEK_VALIDATION_TIMEOUT=300
mixseek validate-models --input models.toml
```

### 入力ファイル解析エラー（シンプル形式使用時）
```
ValidationError: Field 'model_id' is required for models[0]
```

**対処法**: シンプル形式の場合、必須フィールドを確認:
- `provider`
- `model_id`
- `name`
- `modality`
- `version`

**Note**: llm-discovery形式（`[[providers]]`）の場合、`modality`と`version`は自動推測されます。

---

## 次のステップ

### 推奨ワークフロー

#### ステップ1: 互換性判定（コストなし）
```bash
# 全モデルの互換性を確認
mixseek validate-models \
  --input examples/llm-models.toml \
  --skip-api-validation
```

#### ステップ2: 個別モデルのAPI検証（コスト最小）
```bash
# 推奨モデル1つだけ実API検証
export GOOGLE_API_KEY="AIzaSy..."
mixseek validate-models \
  --input examples/llm-models.toml \
  --exact-model "gemini-2.5-flash" \
  --cost-limit 0.01
```

#### ステップ3: プロバイダー単位のAPI検証
```bash
# Anthropic全モデルをAPI検証
export ANTHROPIC_API_KEY="sk-ant-..."
mixseek validate-models \
  --input examples/llm-models.toml \
  --filter-provider "anthropic" \
  --cost-limit 0.10
```

---

### 詳細なドキュメント
- [Data Model](./data-model.md): データモデルの詳細仕様
- [CLI Interface](./contracts/cli-interface.md): CLI引数の完全なリファレンス
- [Input Format](./contracts/input-format.md): 入力ファイル形式の詳細
- [Output Format](./contracts/output-format.md): 出力ファイル形式の詳細
- [Implementation Tasks](./tasks.md): 実装タスクの詳細

### 活用例
- ✅ TOMLマトリクスをパースして自動化スクリプトに組み込む
- ✅ Markdownレポートをドキュメントシステムに統合
- ✅ 検証結果をCI/CDパイプラインで活用
- ✅ 個別モデルのパフォーマンステスト

### フィードバック
問題や改善提案がある場合は、GitHubリポジトリのIssuesセクションで報告してください。

---

**最終更新**: 2025-10-22
