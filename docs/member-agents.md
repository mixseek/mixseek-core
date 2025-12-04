# Member Agent ガイド

Member Agentは、MixSeek-Coreフレームワークに組み込まれた専門エージェントシステムです。各エージェントは特定のタスクに特化しており、Leader Agentから呼び出されて協調動作します。

## Member Agentとは

Member Agentは、以下の特徴を持つエージェントコンポーネントです：

- **特定ドメインへの特化**: 各エージェントは推論、Web検索、コード実行など特定の機能に特化
- **TOML設定ベース**: システムプロンプトやパラメータをTOMLファイルで定義
- **Pydantic AIベース**: Pydantic AIフレームワークを使用した実装
- **標準バンドル**: mixseek-coreパッケージに4種類のエージェントを同梱

## エージェントタイプ

### Plain Agent

基本的な推論と分析を行うエージェントです。外部ツールを使わずに、モデルの推論能力のみを使用します。

用途：
- 一般的な質問応答
- テキスト分析
- 論理的推論
- 概念の説明

設定例（`plain_agent.toml`）：

```toml
[agent]
name = "plain-assistant"
type = "plain"
model = "google-gla:gemini-2.5-flash"
temperature = 0.2 # 省略可（省略時はモデルのデフォルト値を使用）
max_tokens = 2048
timeout_seconds = 30
max_retries = 1
system_instruction = "You are a helpful assistant specialized in reasoning and analysis. Provide clear, well-structured responses to user questions."
description = "General reasoning and analysis"
```

### Web Search Agent

Web検索機能を持つエージェントです。最新情報の取得や事実確認が必要なタスクに使用します。

用途：
- 最新情報の調査
- 事実確認
- ニュースや動向の分析
- 情報収集

対応プロバイダー：
- **Google Gemini**: `google-gla:gemini-2.5-flash`
- **Anthropic Claude**: `anthropic:claude-sonnet-4-5-20250929`
- **Grok (xAI)**: `grok-responses:grok-4-fast` (ネイティブWeb検索ツール使用)

設定例（`web_search_agent.toml`）：

```toml
[agent]
name = "research-agent"
type = "web_search"
model = "google-gla:gemini-2.5-flash"
temperature = 0.3 # 省略可（省略時はモデルのデフォルト値を使用）
max_tokens = 3072
system_instruction = "You are a research assistant with web search capabilities. Search for current information when needed to provide accurate responses. Always cite your sources."
description = "Web search and research capabilities"
capabilities = ["web_search"]

[agent.tool_settings.web_search]
max_results = 10
timeout = 30
```

**Grok Web Search Agentの設定例**（`grok_web_search_agent.toml`）：

```toml
[agent]
name = "grok-researcher"
type = "web_search"
model = "grok-responses:grok-4-fast"
temperature = 0.2
max_tokens = 2048
system_instruction = """あなたは高度な研究エージェントです。

専門能力:
- リアルタイム情報収集とWeb検索
- 複数ソースからの情報統合と分析
- 信頼性の高い情報検証と評価

検索結果を批判的に評価し、信頼性を判断してください。"""
description = "Grok Web Search Agent with native search capabilities"
```

Grokモデルは`grok-responses:`プレフィックスを使用することで、xAIのネイティブWeb検索ツールを利用できます。

### Web Fetch Agent

指定したURLの内容を取得できるエージェントです。Webページの内容を読み込んで分析・要約するタスクに使用します。

用途：
- URLの内容取得と分析
- Webページの要約
- 特定サイトからの情報抽出
- Web Search Agentで見つけたURLの詳細確認

対応プロバイダー：
- **Anthropic Claude**: `anthropic:claude-sonnet-4-5-20250929`（フルサポート、パラメータ設定可能）
- **Google Gemini**: `google-gla:gemini-2.5-flash`（基本サポート、パラメータ設定不可）

制限事項：
- OpenAI/Grokではサポートされていません
- Anthropicモデルのみパラメータ設定（ドメイン制限、引用情報など）が可能
- **JavaScriptでレンダリングされるページは取得できません**（静的HTML/ドキュメントページは正常に動作）
- Claudeは動的にURLを構築できません（ユーザーが提供したURLのみ使用可能）
- 詳細: [Anthropic Web Fetch Tool ドキュメント](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-fetch-tool)

設定例（`web_fetch_agent.toml`）：

```toml
[agent]
name = "url-reader"
type = "web_fetch"
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.2
max_tokens = 4096
system_instruction = "あなたはWebページの内容を分析するエージェントです。URLから取得した情報を正確に要約し、重要なポイントを抽出してください。"
description = "Web page content fetching and analysis"
capabilities = ["web_fetch"]

[agent.tool_settings.web_fetch]
max_uses = 5
enable_citations = true
max_content_tokens = 30000
```

**Anthropicモデル専用パラメータ**:

```toml
[agent.tool_settings.web_fetch]
# ツール呼び出し回数制限
max_uses = 5

# 許可ドメイン（blocked_domainsと排他）
allowed_domains = ["example.com", "docs.example.com"]

# ブロックドメイン（allowed_domainsと排他）
# blocked_domains = ["malicious.com"]

# 引用情報の有効化
enable_citations = true

# 最大コンテンツトークン数（上限50000）
max_content_tokens = 30000
```

**Google Geminiでの設定例**：

```toml
[agent]
name = "url-reader-gemini"
type = "web_fetch"
model = "google-gla:gemini-2.5-flash"
temperature = 0.2
max_tokens = 4096
system_instruction = "あなたはWebページの内容を分析するエージェントです。"
description = "Web page content fetching (Google)"
capabilities = ["web_fetch"]

# Note: Googleモデルではtool_settings.web_fetchのパラメータは無視されます
```

**Web Search + Web Fetchの連携例**：

Web SearchでURLを見つけ、Web Fetchで詳細を確認するワークフロー：

```bash
# Step 1: Web Searchで関連URLを検索
mixseek member "Python asyncioのベストプラクティスを検索してください" \
  --config web_search_agent.toml

# Step 2: 見つかったURLの内容を詳細に分析
mixseek member "https://docs.python.org/3/library/asyncio.html の内容を要約してください" \
  --config web_fetch_agent.toml
```

### Code Execution Agent

Pythonコードを実行できるエージェントです。計算やデータ分析などの計算タスクに使用します。

制限事項：
- Anthropic Claudeモデルのみサポート
- Google AI/Vertex AI/OpenAIでは動作しません

用途：
- 数値計算
- データ分析
- 統計処理
- プログラミング問題の解決

設定例（`code_execution_agent.toml`）：

```toml
[agent]
name = "data-analyst"
type = "code_execution"
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.1 # 省略可（省略時はモデルのデフォルト値を使用）
max_tokens = 4096
system_instruction = "You are a data analyst with code execution capabilities. Use Python code to perform calculations and data analysis. Always explain your approach and interpret the results."
description = "Data analysis and code execution"
capabilities = ["code_execution"]

[agent.retry_config]
max_retries = 1
initial_delay = 1.5
backoff_factor = 2.0
```

## カスタムエージェント開発

```{seealso}
カスタムMember Agentの開発方法、TOML設定、実装例については、 [カスタムエージェント開発ガイド](custom-member-agent.md) を参照してください
```

## 設定方法

### 認証設定

Pydantic AIの標準環境変数を使用します：

Google Gemini API:

```bash
export GOOGLE_API_KEY="AIzaSy..."
```

Vertex AI:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

Anthropic Claude:

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

Grok (xAI):

```bash
export GROK_API_KEY="xai-..."
```

重要: API キーはTOMLファイルに記載せず、環境変数で設定してください。

### TOML設定構造

すべてのMember AgentはTOMLファイルで設定します：

```toml
[agent]
# 必須フィールド
name = "agent-name"
type = "plain|web_search|web_fetch|code_execution"
model = "provider:model-name"
temperature = 0.0-1.0
max_tokens = 1024

# オプション
description = "Agent description"
capabilities = ["capability1", "capability2"]

[agent.system_instruction]
text = """System prompt for the agent."""

[agent.metadata]
version = "1.0.0"
author = "Your Name"
```

## 使用方法

### CLIコマンド

開発・テスト用のCLIコマンド `mixseek member` を使用します：

基本的な使い方:

```bash
# 設定ファイルを指定
mixseek member "Your question here" --config agent.toml

# 事前定義されたエージェントを指定
mixseek member "Your question here" --agent agent-name
```

オプション:

**基本オプション**:
- `--config PATH, -c` - TOML設定ファイルのパス（絶対パスまたは相対パス）
- `--agent NAME` - バンドルされたエージェント名（plain, web-search, code-exec）
- `--workspace PATH, -w` - ワークスペースパス（ログ出力先とconfig相対パス解決用）
- `--output-format FORMAT, -f` - 出力形式（structured, json, text, csv）デフォルト: structured
- `--verbose, -v` - 詳細な出力（実行詳細とメッセージ履歴を表示）
- `--timeout SECONDS` - タイムアウト設定（デフォルト: 30秒）
- `--temperature FLOAT` - 温度パラメータの上書き（0.0-1.0）
- `--max-tokens NUMBER` - 最大トークン数の上書き

```{important}
**Workspaceとログ機能について**:
- ログファイル出力を使用する場合、`--workspace` オプションまたは `MIXSEEK_WORKSPACE` 環境変数の設定を**強く推奨**します
- workspace未指定の場合、ログファイルはカレントディレクトリに出力されます
- `--no-log-file` を指定すればworkspace不要でコンソールのみにログ出力できます
- `--agent` オプション使用時もworkspace指定なしで動作しますが、ログファイル出力には影響します
```

**ログオプション**:
- `--log-level LEVEL` - ログレベル（debug/info/warning/error/critical）デフォルト: info
- `--no-log-console` - コンソールログ出力を無効化
- `--no-log-file` - ファイルログ出力を無効化（workspace不要で動作）

**Logfireオプション（observability）**:
- `--logfire` - Logfire完全モード（メッセージ履歴とトークン使用量を記録）
- `--logfire-metadata` - Logfireメタデータモード（メタデータのみ記録）
- `--logfire-http` - Logfire HTTPキャプチャモード（完全モード + HTTP通信記録）

Note: Logfireオプションは排他的です（同時に1つのみ指定可能）

### 使用例

Plain Agentで質問応答:

```bash
mixseek member "Explain the concept of recursion" \
  --config plain_agent.toml
```

Web Search Agentで最新情報を検索:

```bash
mixseek member "What are the latest developments in AI safety?" \
  --config web_search_agent.toml
```

Code Execution Agentで計算:

```bash
mixseek member "Calculate compound annual growth rate for \$1000 to \$2500 over 5 years" \
  --config code_execution_agent.toml
```

JSON形式で出力:

```bash
mixseek member "Analyze this data" \
  --agent data-analyst \
  --output-format json
```

詳細出力モード（verbose）の使用:

```bash
# ツール呼び出しの詳細を確認
mixseek member "Search for Python tutorials" \
  --agent web-search \
  --verbose

# JSON形式でメッセージ履歴を含む完全な出力
mixseek member "Calculate the fibonacci sequence" \
  --agent code-exec \
  --output-format json \
  --verbose
```

ワークスペースを指定してconfig相対パスを使用:

```bash
# --workspace を指定すると --config の相対パスが workspace からの相対パスとして解決される
mixseek member "質問" \
  --config configs/my_agent.toml \
  --workspace /path/to/workspace
```

ログオプションの使用:

```bash
# デバッグログを有効化
mixseek member "質問" \
  --agent plain \
  --log-level debug \
  --verbose

# コンソールログを無効化（ファイルログのみ）
mixseek member "質問" \
  --agent plain \
  --no-log-console

# すべてのログを無効化
mixseek member "質問" \
  --agent plain \
  --no-log-console \
  --no-log-file
```

Logfireによるobservability:

```bash
# Logfire完全モード（メッセージ履歴とトークン使用量を記録）
mixseek member "質問" \
  --agent plain \
  --logfire

# Logfireメタデータモード（メタデータのみ記録、本番環境推奨）
mixseek member "質問" \
  --agent plain \
  --logfire-metadata

# Logfire HTTPキャプチャモード（デバッグ用、HTTP通信も記録）
mixseek member "質問" \
  --agent web-search \
  --logfire-http
```

### 出力フォーマット

#### structured（デフォルト）

人間が読みやすい構造化されたテキスト形式です。色付きで整形された出力を提供します。

基本出力:
- ステータス（成功/エラー/警告）
- エージェント名とタイプ
- 実行時間
- 応答内容
- エラー詳細（エラー時）

`--verbose` オプション使用時の追加情報:
- **モデル情報**: model ID, temperature, max_tokens
- **使用量情報**: トークン数（input/output）、リクエスト数
- **メッセージ履歴**:
  - ユーザープロンプト
  - システム命令
  - モデルの応答
  - **ツール呼び出し詳細**（ツール名、引数、実行結果）
  - 中間推論ステップ

使用例:
```bash
mixseek member "Search for latest AI news" --agent web-search --verbose
```

出力例:
```
============================================================
MEMBER AGENT EXECUTION RESULT
============================================================

Status: SUCCESS
Agent: research-agent (web_search)
Execution Time: 1523ms
Timestamp: 2025-11-21 12:30:45 UTC

Response:
----------------------------------------
最新のAI関連ニュースを調査しました...

Execution Details:
----------------------------------------
  Model: google-gla:gemini-2.5-flash-lite
  Temperature: 0.7
  Max Tokens: 4096
  Usage:
    total_tokens: 1234
    prompt_tokens: 890
    completion_tokens: 344

Message History:
----------------------------------------

  [1] ModelRequest
      Instructions: You are a research assistant...
      Part: UserPromptPart
        Content: Search for latest AI news

  [2] ModelResponse
      Model: gemini-2.5-flash-lite
      Usage: input=890, output=50
      Part: ToolCallPart
        Tool: web_search
        Args:
          {
            "query": "latest AI news 2025",
            "max_results": 10
          }

  [3] ModelResponse
      Model: gemini-2.5-flash-lite
      Usage: input=940, output=294
      Part: ToolReturnPart
        Tool Return: web_search
        Content: Search results: [...]
      Part: TextPart
        Content: 最新のAI関連ニュースを調査しました...
```

#### json

プログラムで処理しやすいJSON形式です。パイプラインやスクリプトとの連携に適しています。

**JSON形式では常に完全な情報が出力されます**（`--verbose` フラグ不要）。

出力フィールド:
- `status`: 実行ステータス
- `agent_name`: エージェント名
- `agent_type`: エージェントタイプ
- `content`: 応答内容
- `execution_time_ms`: 実行時間（ミリ秒）
- `timestamp`: タイムスタンプ（ISO 8601形式）
- `usage_info`: 使用量情報（トークン数など）
- `metadata`: 追加メタデータ
- `all_messages`: 完全なメッセージ履歴（Pydantic AI形式、常に含まれる）

使用例:
```bash
# 基本的なJSON出力（all_messagesも含まれる）
mixseek member "Hello" --agent plain --output-format json

# jqでcontentのみ抽出
mixseek member "Calculate 123 * 456" --agent code-exec --output-format json | jq '.content'

# メッセージ履歴を抽出
mixseek member "Search for tutorials" --agent web-search --output-format json | jq '.all_messages'

# ツール呼び出しの引数を確認
mixseek member "Search for AI news" --agent web-search --output-format json | jq '.all_messages[].parts[] | select(.tool_name) | .args'
```

#### text

レスポンス内容のみを出力するシンプルな形式です。パイプ処理や他のコマンドとの連携に最適です。

使用例:
```bash
# contentのみを出力
mixseek member "Translate 'Hello' to Japanese" --agent plain --output-format text

# 他のコマンドとパイプ
mixseek member "Generate a haiku" --agent plain --output-format text | wc -l
```

#### csv

バッチ処理用のCSV形式です。複数の実行結果を一括処理する場合に使用します。

CSV列:
- timestamp
- agent_name
- agent_type
- status
- execution_time_ms
- content_length
- error_code

注: `csv` フォーマットは通常、バッチ処理ツールから使用されます。

## トラブルシューティング

### 認証エラー

症状: "Authentication failed"

解決方法:

```bash
# API キーが設定されているか確認
echo $GOOGLE_API_KEY

# Vertex AI の場合
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

### 設定エラー

症状: "Invalid configuration"

解決方法:

```bash
# TOML構文を検証
python -c "
import tomllib
with open('agent.toml', 'rb') as f:
    data = tomllib.load(f)
    print('TOML syntax is valid')
"
```

### Code Execution Agent のプロバイダーエラー

症状: "Code Execution Agent only supports Anthropic Claude models"

解決方法: Anthropic Claudeモデルを使用するように設定を変更してください：

```toml
[agent]
model = "anthropic:claude-sonnet-4-5-20250929"
```

環境変数を設定:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Web Fetch Agent のプロバイダーエラー

症状: "Web Fetch Agent only supports Anthropic and Google models"

解決方法: AnthropicまたはGoogleモデルを使用するように設定を変更してください：

```toml
# Anthropic（推奨、フルサポート）
[agent]
model = "anthropic:claude-sonnet-4-5-20250929"

# または Google（基本サポート）
[agent]
model = "google-gla:gemini-2.5-flash"
```

環境変数を設定:

```bash
# Anthropicの場合
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Geminiの場合
export GOOGLE_API_KEY="AIzaSy..."
```

### タイムアウトエラー

症状: "Execution timed out"

解決方法: タイムアウト値を増やす：

```bash
mixseek member "complex prompt" \
  --config agent.toml \
  --timeout 120
```

## 実装詳細

Member Agentの実装について詳しくは、以下のファイルを参照してください：

- ベースクラス: `src/mixseek/agents/base.py`
- Plain Agent: `src/mixseek/agents/plain.py`
- Web Search Agent: `src/mixseek/agents/web_search.py`
- Code Execution Agent: `src/mixseek/agents/code_execution.py`
- モデル定義: `src/mixseek/models/member_agent.py`
- 設定例: `examples/config_templates/`

詳細な仕様は `specs/009-member/spec.md` を参照してください。

## 参考資料

- [開発者ガイド](developer-guide.md) - 開発環境のセットアップとテスト
- [Docker セットアップ](docker-setup.md) - Docker環境での開発
- Pydantic AI公式ドキュメント: <https://ai.pydantic.dev/>
