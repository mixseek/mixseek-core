# クイックスタートガイド

MixSeek-Core を使い始めるための10-15分のガイドです。

## 環境構築

2つの方法から選択してください。

### 方法A: ローカル環境で実行

ローカルマシンで直接実行する方法です。最もシンプルで軽量です。

#### リポジトリをクローン

```bash
git clone https://github.com/mixseek/mixseek-core.git
cd mixseek-core
```

#### 依存関係をインストール

```bash
uv sync
```

#### 環境変数を設定

以下のいずれかの認証方法を選択してください。

**オプションA-1: Gemini Developer API（個人・プロトタイピング向け）**

Google Gemini Developer APIを使用します。APIキーの取得が簡単です。

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
export GOOGLE_API_KEY=your-api-key
```

`your-api-key` を [Google AI Studio](https://aistudio.google.com/app/apikey) から取得したAPIキーに置き換えてください。

**オプションA-2: Vertex AI（エンタープライズ向け）**

Google Cloud Vertex AIを使用します。GCPプロジェクトが必要です。

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp_credentials.json
```

`/path/to/gcp_credentials.json` を取得したサービスアカウントの認証情報JSONファイルのパスに置き換えてください。

**オプションA-3: OpenAI（GPT-4o等）**

OpenAI APIを使用します。

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
export OPENAI_API_KEY=your-openai-api-key
```

`your-openai-api-key` を [OpenAI API キー](https://platform.openai.com/api-keys) から取得したAPIキーに置き換えてください。

**オプションA-4: Anthropic（Claude）**

Anthropic APIを使用します。

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
export ANTHROPIC_API_KEY=your-anthropic-api-key
```

`your-anthropic-api-key` を [Anthropic Console](https://console.anthropic.com/account/keys) から取得したAPIキーに置き換えてください。

**オプションA-5: Grok（xAI）**

xAI Grok APIを使用します。

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
export GROK_API_KEY=your-grok-api-key
```

`your-grok-api-key` を [xAI Console](https://console.x.ai/) から取得したAPIキーに置き換えてください。

#### ワークスペース初期化

```bash
mixseek init
```

これでセットアップは完了です。[「Member Agent実行」](#member-agent実行)に進んでください。

### 方法B: Docker環境で実行

Docker コンテナ内で実行する方法です。隔離された環境で開発できます。

#### 前提条件

Docker環境での実行には、以下が必要です：

**Docker Engine 20.10以降**

```bash
docker --version
```

出力例：`Docker version 28.4.0, build d8eb465`

**Make 4.0以降**

```bash
make --version
```

出力例：`GNU Make 3.81`

これら2つが利用可能であることを確認してから、次に進んでください。

#### リポジトリをクローン

```bash
git clone https://github.com/mixseek/mixseek-core.git
cd mixseek-core
```

#### 環境設定ファイルを準備

```bash
cp dockerfiles/dev/.env.dev.template .env.dev
```

#### 環境ファイルを編集

```bash
vim .env.dev
```

以下のいずれかの認証方法を選択し、対応するAPIキーまたはパスを設定してください。

**オプションB-1: Gemini Developer API**

```bash
GOOGLE_GENAI_USE_VERTEXAI=false
GOOGLE_API_KEY=your-api-key
```

**オプションB-2: Vertex AI**

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_APPLICATION_CREDENTIALS=/app/.cred/gcp_credentials.json
```

Vertex AIを選択した場合、以下の手順でGCPサービスアカウントの認証情報を設定してください：

1. プロジェクトルートに `.cred/` ディレクトリを作成
   ```bash
   mkdir -p .cred
   ```

2. GCPサービスアカウントの認証情報JSONファイルをダウンロード（詳細は後述の「Vertex AI認証手順」参照）

3. ダウンロードしたJSONファイルを `.cred/gcp_credentials.json` に配置
   ```bash
   cp /path/to/downloaded-key.json .cred/gcp_credentials.json
   ```

4. ファイルのアクセス権限を確認
   ```bash
   ls -la .cred/gcp_credentials.json
   ```

Docker起動時、このプロジェクトルートの `.cred/gcp_credentials.json` は自動的にコンテナ内の `/app/.cred/gcp_credentials.json` にマウントされます（Dockerfileで設定済み）。

**オプションB-3: OpenAI（GPT-4o等）**

```bash
OPENAI_API_KEY=your-openai-api-key
```

**オプションB-4: Anthropic（Claude）**

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
```

#### Dockerコンテナをビルド・起動

```bash
# ビルド
make -C dockerfiles/dev build

# 起動
make -C dockerfiles/dev run

# コンテナ内シェルに接続
make -C dockerfiles/dev bash
```

これでDocker環境が起動し、コンテナ内のシェルプロンプトが表示されます。

#### ワークスペース初期化（Docker環境内）

コンテナ内のシェルで以下を実行してください：

```bash
# ワークスペースディレクトリを設定
export MIXSEEK_WORKSPACE=/app/workspaces/my_first_ws

# ディレクトリを作成
mkdir -p $MIXSEEK_WORKSPACE

# 初期化
mixseek init
```

これでセットアップは完了です。[「Member Agent実行」](#member-agent実行)に進んでください。

**Docker環境でStreamlit UIを使用する場合**: [Docker + Streamlit UI統合ガイド](ui-docker.md)を参照してください。

## 認証オプション選択ガイド

### 利用可能なLLMプロバイダー

| LLMプロバイダー | 用途 | セットアップ難易度 | 推奨用途 |
|-----------|------|-------------|---------|
| **Gemini Developer API** | 個人・プロトタイピング | 簡単（5分） | 学習・テスト・個人プロジェクト |
| **Vertex AI** | エンタープライズ | 中程度（15-20分） | 本番環境・チームプロジェクト |
| **OpenAI（GPT-4o等）** | 高精度応答が必要 | 簡単（5分） | 汎用利用・ビジネス用途 |
| **Anthropic（Claude）** | 長文対応・推論 | 簡単（5分） | 複雑な分析・研究用途 |

### Vertex AI認証手順（詳細）

Vertex AIを使用する場合の詳細手順です。

#### 前提条件

- Google Cloudアカウント
- GCPプロジェクト（新規作成可）

#### 手順

1. **GCPコンソールでプロジェクトを作成**
   - [Google Cloud Console](https://console.cloud.google.com/) にログイン
   - 新規プロジェクトを作成

2. **Vertex AI APIを有効化**
   - Google Cloud Consoleのサーチバーで「Vertex AI」を検索
   - Vertex AI APIを有効にする

3. **サービスアカウントを作成**
   - 「IAM と管理」→「サービスアカウント」から新規作成
   - 権限：「Vertex AI User」と「Vertex AI Service Agent」を付与

4. **認証情報JSONを作成・ダウンロード**
   - サービスアカウント詳細ページの「キー」タブから「新しいキー」を作成
   - JSON形式でダウンロード

5. **環境変数を設定**
   ```bash
   export GOOGLE_GENAI_USE_VERTEXAI=true
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/downloaded-key.json
   ```

## Member Agent実行

まず、単一の Member Agent を実行してみます。

### 例: Plain Agent で質問応答

```bash
# サンプル設定ファイルをワークスペースにコピー
cp examples/agents/plain_agent.toml $MIXSEEK_WORKSPACE/configs/

# Member Agentを実行
mixseek member "Pythonの特徴を3つ教えてください" \
  --config $MIXSEEK_WORKSPACE/configs/plain_agent.toml
```

実行結果例：

```
Agent: plain-agent (type: plain)
Status: SUCCESS

Response:
Pythonの特徴を3つ以下の通りです：

1. シンプルで読みやすい構文
   - インデント重視のコードスタイルで、可読性が非常に高い
   - 初心者にも理解しやすい

2. 豊富なライブラリエコシステム
   - NumPy、Pandas、Scikit-learn など科学計算・機械学習ライブラリが充実
   - WebフレームワークやDBライブラリなど一般的な用途もカバー

3. 動的型付けとその柔軟性
   - 開発速度が高速
   - 型安全性とバランスを取りながら、プロトタイピングに最適

Time: 2.3s | Tokens: 245 input, 187 output
```

### その他の Member Agent

**Web Search Agent で最新情報を取得**

```bash
cp examples/agents/researcher.toml $MIXSEEK_WORKSPACE/configs/

mixseek member "最新のAI技術トレンドを調査してください" \
  --config $MIXSEEK_WORKSPACE/configs/researcher.toml
```

**Code Execution Agent でPythonコードを実行**

```bash
cp examples/agents/code_execution_agent.toml $MIXSEEK_WORKSPACE/configs/

mixseek member "1から100までの合計を計算してください" \
  --config $MIXSEEK_WORKSPACE/configs/code_execution_agent.toml
```

詳細は [Member Agentガイド](member-agents.md) を参照してください。

## Team実行（Agent Delegation）

複数の Member Agent を協調動作させます。Leader Agent が タスクを分析して、適切な Member Agent を動的に選択・実行します。

### 例: チーム実行

```bash
# サンプル設定ファイルをワークスペースにコピー
cp examples/team-inline-agents.toml $MIXSEEK_WORKSPACE/configs/

# Teamを実行
mixseek team "最新のAI技術トレンドを調査・分析してまとめてください" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --verbose
```

実行フロー：

1. **タスク受信**: Leader Agentがタスクを受け取る
2. **分析**: LLMがタスクを分析し、どの Member Agent が必要か判断
3. **Agent Delegation**: 必要な Member Agent を順次実行
   - `delegate_to_researcher`: Web検索で最新情報を収集
   - `delegate_to_analyst`: 収集情報を論理的に分析
   - `delegate_to_summarizer`: 結果をまとめる
4. **統合**: Leader Agent が各Agentの結果を統合して最終応答を生成

実行結果例：

```
=== Leader Agent Execution ===
Team: Sample Research Team
Round: 1

Selected Member Agents: 3/3
✓ web-search-agent (SUCCESS) - 1200 input, 450 output tokens
✓ analyst (SUCCESS) - 800 input, 320 output tokens
✓ summarizer (SUCCESS) - 400 input, 150 output tokens

Total Usage: 2400 input, 920 output tokens, 3 requests

=== Leader Agent Final Response ===
[Leader Agentの最終的な分析・まとめが表示される]

=== Member Agent Responses (Details) ===
## web-search-agent:
[Web検索で収集した最新AI技術トレンド情報...]

## analyst:
[収集情報の論理的分析結果...]

## summarizer:
[最終的なまとめと主要ポイント...]
```

### JSON 出力

結果をJSON形式で取得することもできます。

```bash
mixseek team "Your task" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --output-format json
```

### Leader Agent応答の評価

`--evaluate` オプションを使用して、Leader Agentの最終応答を自動評価できます。

```bash
mixseek team "最新のAI技術トレンドを調査・分析してまとめてください" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --evaluate
```

カスタム評価設定を使用する場合：

```bash
mixseek team "Your task" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --evaluate \
  --evaluate-config $MIXSEEK_WORKSPACE/configs/evaluator.toml
```

評価結果は、チーム実行結果の後に表示されます：

```
=== Evaluation Results ===
Overall Score: 85.67

Metric Scores:
  clarity_coherence: 88.0
    Comment: 回答は明確で一貫性があります...
  coverage: 85.0
    Comment: 主要なポイントを包括的にカバーしています...
  relevance: 84.0
    Comment: ユーザーの質問に適切に答えています...
```

詳細なコメントを確認する場合は `--verbose` を追加してください（評価コメントが500文字以上の場合、全文が表示されます）。

### 独立した評価の実行

Leader Agentの応答を後から評価することもできます。

```bash
mixseek evaluate "質問" "Leader Agentの応答テキスト"
```

カスタム評価設定を使用：

```bash
mixseek evaluate "質問" "応答" --config evaluate.toml
```

```{important}
**Workspaceとログ機能について**:
- ログファイル出力を使用する場合、`--workspace` オプションまたは `MIXSEEK_WORKSPACE` 環境変数の設定を**強く推奨**します
- workspace未指定の場合、ログファイルはカレントディレクトリに出力されます
- `--no-log-file` を指定すればworkspace不要でコンソールのみにログ出力できます
```

ログオプションとLogfireを使用：

```bash
# デバッグログを有効化
mixseek evaluate "質問" "応答" --log-level debug --verbose

# Logfireで評価プロセスを観測
mixseek evaluate "質問" "応答" --logfire

# Workspace指定でログファイル出力先を管理
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek evaluate "質問" "応答" --logfire-metadata
```

### リアルタイム観測（Logfire）

Agent実行をリアルタイムで可視化できます（開発・デバッグ推奨）。

```bash
# Logfire有効化（開発時、fullモード）
mixseek team "最新のAI技術トレンドを調査してください" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --logfire

# 本番環境（メタデータのみ）
mixseek team "..." --config team.toml --logfire-metadata

# デバッグ（HTTP詳細含む）
mixseek team "..." --config team.toml --logfire-http
```

Logfire UIで以下が確認できます：
- Agent実行フローの可視化（Leader → Member Agent階層）
- メッセージ履歴の詳細
- トークン使用量とコスト
- 実行時間の分析

詳細は [Observability](observability.md) を参照してください。

### チーム設定ファイルの作成（詳細例）

カスタムなチーム設定ファイルを作成して、自分の用途に合わせたMember Agentを組み合わせることができます。

#### 複数のAgent typeを含むチーム設定例

以下は3つの異なるAgent type（plain、web_search、code_execution）を含むチーム設定の例です。

```bash
cat <<EOF > $MIXSEEK_WORKSPACE/configs/team1.toml
[team]
team_id = "dev-team-001"
team_name = "Analysis Team"
max_concurrent_members = 5

# Leader Agent設定
[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
system_prompt = """
タスクを分析し、適切なMember Agentを選択してください:
- delegate_to_analyst: 論理的分析が必要な場合
- delegate_to_web_search: 最新情報が必要な場合
- delegate_to_code_exec: 計算やデータ分析が必要な場合

リソース効率のため、必要最小限のAgentのみ選択してください。
"""

# Member Agent 1: Analyst（論理的分析）
[[team.members]]
name = "analyst"
type = "plain"
tool_description = "論理的な分析を実行します"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a data analyst. Analyze data using logical reasoning."
temperature = 0.2
max_tokens = 2048

# Member Agent 2: Web Researcher（Web検索）
[[team.members]]
name = "web-researcher"
type = "web_search"
tool_description = "Web検索で最新情報を取得します"
model = "google-gla:gemini-2.5-flash"
system_instruction = "You are a web researcher. Search for current information."
temperature = 0.3
max_tokens = 4096

# Member Agent 3: Code Executor（Python実行）
[[team.members]]
name = "calculator"
type = "code_execution"
tool_description = "Pythonコードで計算を実行します"
model = "anthropic:claude-sonnet-4-5"
system_instruction = "You are a calculator. Execute Python code for numerical computations."
temperature = 0.0
max_tokens = 2048
EOF
```

#### カスタム設定で実行

作成したチーム設定ファイルを使って実行します：

```bash
mixseek team "複数のデータソースを分析してトレンドを報告してください" \
  --config $MIXSEEK_WORKSPACE/configs/team1.toml \
  --verbose
```

### 設定のカスタマイズポイント

- **model**: 各Agentが使用するLLMモデル（変更可能）
- **system_prompt**: 各Agentの役割定義（カスタマイズ推奨）
- **temperature**: 応答の多様性（0.0=確定的、1.0=多様）
- **max_tokens**: 最大出力トークン数

詳細は [Teamガイド](team-guide.md) を参照してください。

## Orchestrator実行（複数チーム並列実行）

複数のチームを並列実行し、最高スコアのSubmissionを選択します。

### オーケストレータ設定の準備

オーケストレータ設定ファイルを作成：

```bash
# オーケストレータ設定ファイルを作成
cat > $MIXSEEK_WORKSPACE/configs/orchestrator.toml <<EOF
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/team1.toml"

[[orchestrator.teams]]
config = "configs/team2.toml"
EOF
```

### 例: オーケストレーション実行

```bash
# 複数チームを並列実行
mixseek exec "最新のAI技術トレンドを調査・分析してまとめてください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

実行フロー：

1. **タスク配信**: Orchestratorが全チームに同一タスクを配信
2. **並列実行**: 各チームが独立してLeader Agent → Member Agent → Evaluationを実行
3. **結果集約**: 全チーム完了後、最高スコアチームを特定
4. **リーダーボード表示**: スコア順にランキング表示

実行結果例:

```text
🚀 MixSeek Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task: 最新のAI技術トレンドを調査・分析してまとめてください

🔄 Running 2 teams in parallel...

✅ Team research-team-001: Research Team (completed in 45.2s)
   Score: 92.00
   Feedback: 包括的な調査結果が提供されました。

✅ Team analysis-team-001: Analysis Team (completed in 38.7s)
   Score: 88.00
   Feedback: 詳細な分析が行われました。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Leaderboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank  Team             Score    Status        Tokens
1     Research Team    92.00    ✅ Completed  15,234
2     Analysis Team    88.00    ✅ Completed  12,456

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Teams:      2
Completed Teams:  2
Failed Teams:     0
Execution Time:   45.2s

💾 Results saved to DuckDB
```

詳細は [Orchestratorガイド](orchestrator-guide.md) を参照してください。

## 設定管理

MixSeek-Coreは、Pydantic Settingsベースの統一設定管理システムを提供します。

### 設定の優先順位

設定値は以下の優先順位で適用されます（高い順）：

```
CLI引数 > 環境変数 > .env > TOML > デフォルト値
```

### 基本的な使い方

**設定テンプレートの生成**:

```bash
# ワークスペースを指定してテンプレート生成（推奨）
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
mixseek config init --component orchestrator
mixseek config init --component team

# または --workspace オプションで指定
mixseek config init --component orchestrator --workspace $HOME/mixseek-workspace

# カスタム出力先を指定
mixseek config init --component orchestrator \
  --output-path configs/production/orchestrator.toml \
  --workspace $HOME/mixseek-workspace
```

**環境変数による設定上書き**:

```bash
# ワークスペースパスを環境変数で設定
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# タイムアウトを環境変数で上書き
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600

# チーム実行
mixseek team "タスク" --config team.toml
```

詳細は [設定リファレンス](configuration-reference.md) を参照してください。

### 設定の確認

設定ファイルの内容を確認するには、以下のコマンドを使用します：

```bash
# 現在の設定値を階層表示（--config 必須）
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config show --config orchestrator.toml

# または --workspace オプションで指定
mixseek config show --config orchestrator.toml --workspace /path/to/workspace

# 特定の設定項目を表示
mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace

# 全設定項目のスキーマ情報をリスト表示
mixseek config list
```

`config show` コマンドは、orchestrator TOMLファイルを指定して、参照されている全てのteam/member設定を階層的に表示します。`--workspace` オプションは省略可能で、省略時は `MIXSEEK_WORKSPACE` 環境変数を使用します。

`config list` コマンドは、設定可能な項目のスキーマ情報（デフォルト値、型、説明）を表示します。出力形式は `--output-format` / `-f` で指定でき、`table`（デフォルト）、`text`、`json` が利用可能です。

詳細は [Configuration Guide](configuration-guide.md) を参照してください。

## 次のステップ

基本的な実行方法を習得したら、以下のガイドを参照して、より詳細な機能を学んでください。

### ガイドと参考資料

- **[Member Agentガイド](member-agents.md)** - Member Agentの詳細な使い方、各Agentタイプの特性
- **[Teamガイド](team-guide.md)** - Team実行、Agent Delegationパターン、複数ラウンド実行
- **[Orchestratorガイド](orchestrator-guide.md)** - 複数チームの並列実行、リーダーボード、ランキング
- **[Docker環境セットアップ](docker-setup.md)** - Docker環境の詳細設定、開発ワークフロー
- **[開発者ガイド](developer-guide.md)** - カスタムAgent作成、APIの詳細な使用方法
- **[APIリファレンス](api/index.md)** - 全APIの詳細ドキュメント

### トラブルシューティング

#### 認証エラーが発生する場合

- **Gemini API エラー**: APIキーが正しく設定されているか確認してください
- **Vertex AI エラー**: 認証情報JSONのパスが正しいか、サービスアカウントに正しい権限があるか確認してください

#### コマンドが見つからない

ローカル環境の場合、`mixseek` コマンドが見つからないエラーが表示される場合は、`uv sync` で依存関係をインストールしているか確認してください。

```bash
# パッケージをインストール（インストール済みの場合は不要）
uv sync

# または、uvで直接実行
uv run mixseek --help
```

#### Docker環境で問題が発生する場合

```bash
# ログを確認
docker logs <container-id>

# コンテナ内で直接実行
make -C dockerfiles/dev bash
uv sync
uv run mixseek --help
```
