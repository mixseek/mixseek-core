# Observability（可観測性）

mixseek-coreは4つの出力・観測方式を提供します。

## 4つの出力方式

| 出力方式 | 用途 | データ保存 | デフォルト |
|---------|------|-----------|-----------|
| コンソール | リアルタイム確認 | なし | **有効** |
| ファイル | 事後分析・デバッグ | `$WORKSPACE/logs/` | **有効** |
| `--save-db` | 永続化・SQL分析 | DuckDB（ローカル） | 無効 |
| `--logfire` | リアルタイム観測 | Logfireクラウド/OTel | 無効 |

これらは併用可能です：

```bash
mixseek team "..." --config team.toml --save-db --logfire
```

## アーキテクチャ

mixseek-coreのロギングは2つのパスで統合されています。

```text
┌─────────────────────────────────────────────────────────────────┐
│                    TWO INTEGRATION PATHS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Path 1: Standard Logging → Logfire + console* + file          │
│  ─────────────────────────────────────────────────────         │
│  logging.info("...") → LogfireLoggingHandler → Logfire Cloud   │
│                     → StreamHandler → console*                  │
│                     → FileHandler → file                        │
│                                                                 │
│  Path 2: Logfire Spans → console + file                        │
│  ─────────────────────────────────────────────────────         │
│  logfire.info("...")           ─┐                              │
│  Pydantic AI instrumentation   ─┼→ logfire.configure()         │
│  OpenTelemetry spans           ─┘     └→ ConsoleOptions        │
│                                            └→ TeeWriter        │
│                                                 ├→ console     │
│                                                 └→ file        │
│                                                                 │
│  * Logfire有効時、Path 1のコンソール出力は自動的に無効化       │
│    （Path 2のConsoleOptionsが代替するため重複を防止）          │
└─────────────────────────────────────────────────────────────────┘
```

### Path 1: 標準ロギング

Pythonの標準`logging`モジュールを使用したログ出力です。既存のコードで使用している`logging.info()`、`logging.warning()`等がそのまま動作します。

- **コンソール出力**: `StreamHandler`経由で即時表示（Logfire無効時のみ）
- **ファイル出力**: `FileHandler`経由で`$WORKSPACE/logs/mixseek.log`に保存
- **Logfire送信**: `LogfireLoggingHandler`経由でLogfireクラウドに送信（`--logfire`有効時）

```{note}
**Logfire有効時のコンソール出力**: `--logfire`フラグを使用すると、標準ロギングのコンソール出力（StreamHandler）は自動的に無効化されます。代わりに、Path 2のLogfire ConsoleOptionsがコンソール出力を担当します。これにより、同じログメッセージが重複して表示されることを防ぎます。ファイル出力は引き続き両方のパスで有効です。
```

### Path 2: Logfireスパン出力

Pydantic AI instrumentationやOpenTelemetryスパンのローカル出力です。Agent実行トレース等の詳細な観測データをコンソールやファイルで確認できます。

- **ConsoleOptions**: Logfireスパンをコンソール/ファイルに出力
- **TeeWriter**: 複数出力先への同時書き込み

## 標準ロギング設定

### CLIフラグ

```bash
# デフォルト: コンソール + ファイル出力（両方有効）
mixseek team "..." --config team.toml

# Logfireクラウドも追加
mixseek team "..." --config team.toml --logfire

# コンソール出力を無効化（ファイルのみ）
mixseek team "..." --config team.toml --no-log-console

# ファイル出力を無効化（コンソールのみ）
mixseek team "..." --config team.toml --no-log-file

# ログレベルを指定（debug/info/warning/error）
mixseek team "..." --config team.toml --log-level debug
```

| フラグ | 説明 | デフォルト |
|-------|------|-----------|
| `--log-level LEVEL` | グローバルログレベル | `info` |
| `--log-format FORMAT` | ログ出力形式（text/json） | `text` |
| `--no-log-console` | コンソール出力を無効化 | 有効 |
| `--no-log-file` | ファイル出力を無効化 | 有効 |
| `--logfire` | Logfireクラウド送信を有効化 | 無効 |

### 環境変数

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `MIXSEEK_LOG_LEVEL` | グローバルログレベル（debug/info/warning/error/critical） | `info` |
| `MIXSEEK_LOG_FORMAT` | ログ出力形式（text/json） | `text` |
| `MIXSEEK_LOG_CONSOLE` | コンソール出力有効化（true/false） | `true` |
| `MIXSEEK_LOG_FILE` | ファイル出力有効化（true/false） | `true` |

```bash
# 環境変数での設定例
export MIXSEEK_LOG_LEVEL=debug
export MIXSEEK_LOG_CONSOLE=true
export MIXSEEK_LOG_FILE=false  # ファイル出力無効

mixseek team "..." --config team.toml
```

### 優先順位

設定は以下の優先順位で適用されます：

1. CLIフラグ（`--log-level`、`--log-format`等）
2. 環境変数（`MIXSEEK_LOG_*`）
3. デフォルト値

### ログファイルの場所

ログファイルは`$MIXSEEK_WORKSPACE/logs/mixseek.log`に統一されています。

### ロガー名の統一ルール

mixseek-core の統一ロガーは `"mixseek"` 名前空間で propagate 経由に集約されます。ロガー取得方法はコードの位置によって使い分けてください。

#### 1. mixseek パッケージ内部コード（`src/mixseek/**`）

`logging.getLogger(__name__)` を使用します。`__name__` は `mixseek.config.manager` のように `"mixseek."` プレフィックスを自然に持つため、統一ロガーに正しく伝搬します。

```python
import logging

# 例: src/mixseek/config/manager.py
# __name__ == "mixseek.config.manager" → "mixseek" ロガーに伝搬
logger = logging.getLogger(__name__)
```

#### 2. mixseek パッケージ外部（カスタムエージェント等）

`"mixseek."` プレフィックスの named logger を明示指定します。`__name__` だと `"mixseek"` 名前空間外になり、統一ロガーのハンドラ（stderr/mixseek.log）に伝搬しません。

```python
import logging

# 統一ロガーに伝搬する
logger = logging.getLogger("mixseek.custom_agents.my_agent")

# 以下は "mixseek" 名前空間外のため伝搬しない（非推奨）
# logger = logging.getLogger(__name__)
```

要点: ロガー名が `"mixseek"` または `"mixseek."` で始まっていれば伝搬する、という一貫したルールで統一ロガーのハンドラに集約されます。

## Logfire統合

[Pydantic Logfire](https://logfire.pydantic.dev/)は、Pydantic AIのビルトインサポートを持つObservabilityプラットフォームです。mixseek-coreのLeader AgentとMember Agentの実行をリアルタイムで可視化できます。

### 特徴

- Agent実行フローの可視化（Leader → Member Agent delegationの階層）
- メッセージ履歴の自動キャプチャ（system/user/assistant/tool_call/tool_return）
- トークン使用量とコストの自動集計
- 実行時間の詳細分析
- HTTPリクエスト/レスポンスのキャプチャ（デバッグモード）
- OpenTelemetry準拠（任意のOTelバックエンドで使用可能）

## セットアップ

### 1. Logfireのインストール

```bash
uv sync --extra logfire
```

または開発環境全体をインストール：

```bash
uv sync --group dev
```

### 2. Logfire認証

```bash
uv run logfire auth
```

ブラウザが開き、Logfireアカウントにサインインします。

### 3. プロジェクト作成

```bash
uv run logfire projects new
```

プロジェクト名を入力すると、`.logfire`ディレクトリが作成されます。

既存のプロジェクトを使用する場合：

```bash
uv run logfire projects use
```

## 使用方法

### mixseek team での使用

開発・テスト用の単一チーム実行コマンド。

```bash
mixseek team "分析してください" --config team.toml --logfire
```

これで以下が実行されます：

1. Logfireが自動的に有効化（fullモード）
2. Pydantic AI instrumentationが設定される
3. Agent実行のトレースがLogfireに送信される
4. Logfire UIでリアルタイム確認可能（https://logfire.pydantic.dev/）

### mixseek exec での使用

本番環境想定の複数チーム並列実行コマンド。

```bash
mixseek exec "分析してください" --config orchestrator.toml --logfire
```

**特徴**:

- 複数チームが並列実行され、それぞれのトレースが階層的に記録される
- Orchestrator → RoundController → Leader Agent → Member Agentsの階層構造を可視化
- execution_idでDuckDBとの紐付けが可能

**トレース階層構造**:

```
📊 orchestrator.execute [10.2s] (execution_id: abc-123)
  ├─ 📊 round_controller.run_round (team_1) [4.1s]
  │   └─ 📊 agent run (leader_agent) [3.8s]
  │       ├─ 💬 request (user prompt)
  │       ├─ 🔧 delegate_to_researcher [2.5s]
  │       │   └─ 📊 agent run (web-search-agent)
  │       └─ 💬 final response
  ├─ 📊 round_controller.run_round (team_2) [5.3s]
  │   └─ 📊 agent run (leader_agent) [5.0s]
  └─ 📊 round_controller.run_round (team_3) [3.9s]
      └─ 📊 agent run (leader_agent) [3.6s]
```

### mixseek ui での使用

Streamlitベースのウェブインターフェース。Logfireと併用することで、UI上での実行をリアルタイムで観測できます。

```bash
# Full mode（すべてキャプチャ）- 開発環境推奨
mixseek ui --logfire

# Metadata only mode（本番推奨）- プロンプト/応答を除外
mixseek ui --logfire-metadata

# Full + HTTP capture（デバッグ用）
mixseek ui --logfire-http
```

**特徴**:

- UI上で実行したオーケストレーションのトレースをLogfireで確認
- ブラウザからの実行でもCLIコマンドと同等の観測機能
- サイドバーにLogfire状態表示（有効/無効/エラー）
- 環境変数でも制御可能（`LOGFIRE_ENABLED=1`）

**確認方法**:

1. `mixseek ui --logfire` でStreamlit起動
2. UIのサイドバーに「Logfire enabled (full)」表示を確認
3. UI上でタスクを実行
4. Logfire UIでトレースを確認（https://logfire.pydantic.dev/）

詳細は[ui-guide.md](ui-guide.md#logfire観測機能)を参照してください。

**記録される情報**:

- **Orchestratorレベル**: execution_id, team_count, best_team_id, best_score, execution_status
- **RoundControllerレベル**: team_id, team_name, round_number, evaluation_score, execution_time
- **Agentレベル**: メッセージ履歴、トークン使用量、コスト（Pydantic AI自動記録）

**DuckDBとの紐付け**:

```python
import duckdb

# Logfireから取得したexecution_id
execution_id = "abc-123"

# DuckDBで同じexecution_idのデータを取得
conn = duckdb.connect("mixseek.db")
result = conn.execute("""
    SELECT * FROM execution_summary
    WHERE execution_id = ?
""", [execution_id]).fetchall()

# Leader boardも取得可能
leaderboard = conn.execute("""
    SELECT * FROM leader_board
    WHERE execution_id = ?
    ORDER BY evaluation_score DESC
""", [execution_id]).fetchall()
```

**プライバシーモード**:

```bash
# 本番環境推奨: メタデータのみ
mixseek exec "..." --config orchestrator.toml --logfire-metadata

# デバッグモード: HTTP capture有効
mixseek exec "..." --config orchestrator.toml --logfire-http
```

### プライバシーモード

#### full（デフォルト）

すべてのコンテンツをキャプチャします（開発・デバッグ推奨）。

```bash
mixseek team "..." --config team.toml --logfire
```

**含まれる内容**:
- ✅ System instructions
- ✅ User prompts
- ✅ Assistant responses
- ✅ Tool calls（引数含む）
- ✅ Tool returns
- ✅ トークン使用量
- ✅ 実行時間
- ✅ コスト

#### metadata（本番推奨）

メトリクスのみをキャプチャし、プロンプト/応答は除外します。

```bash
mixseek team "..." --config team.toml --logfire-metadata
```

**含まれる内容**:
- ✅ トークン使用量
- ✅ 実行時間
- ✅ コスト
- ✅ Agent名
- ❌ System instructions（除外）
- ❌ User prompts（除外）
- ❌ Assistant responses（除外）

**ユースケース**: プライバシー要件が厳しい本番環境、顧客データを含むプロンプト

#### http（デバッグモード）

`full`に加えて、HTTPリクエスト/レスポンスもキャプチャします。

```bash
mixseek team "..." --config team.toml --logfire-http
```

**含まれる内容**:
- ✅ `full`モードの全内容
- ✅ HTTPリクエストヘッダー
- ✅ HTTPリクエストボディ（実際のLLM APIリクエスト）
- ✅ HTTPレスポンスヘッダー
- ✅ HTTPレスポンスボディ（実際のLLM APIレスポンス）

**ユースケース**: プロンプトエンジニアリング、APIエラーのデバッグ、レイテンシ分析

#### disabled（環境変数のみ）

Logfireを初期化するが、Pydantic AI instrumentationは実行しません。

**注意**: このモードは環境変数またはTOML設定でのみ使用でき、CLIフラグでは指定できません。
CLIでLogfireを無効化するには、`--logfire`フラグを省略してください。

```bash
# 環境変数での使用
export LOGFIRE_ENABLED=1
export LOGFIRE_PRIVACY_MODE=disabled
mixseek team "..." --config team.toml
```

**含まれる内容**:
- ✅ OpenTelemetryの基本トレース
- ❌ Pydantic AI instrumentation（実行されない）
- ❌ Agent実行の詳細

**ユースケース**: 非常にレアなケース。通常は`--logfire`を省略してLogfireを完全無効化するのが推奨です。

## Logfire UIでの確認

### 1. Live View（リアルタイム）

Logfire UIの「Live」タブで、実行中のtraceをリアルタイムで確認できます。

実行が完了すると、以下のような階層構造が表示されます：

```
📊 agent run (leader_agent) [4.5s]
  ├─ 💬 request (user prompt)
  ├─ 💬 response (tool call)
  │
  ├─ 🔧 delegate_to_researcher [3.2s]
  │   └─ 📊 agent run (web-search-agent) [3.2s]
  │       ├─ 💬 request
  │       ├─ 💬 response (tool call)
  │       ├─ 🔧 web_search [2.3s]
  │       │   └─ 🌐 HTTP request to Vertex AI (httpモード)
  │       └─ 💬 final response
  │
  └─ 💬 final response
```

### 2. Generation Tab（メッセージ詳細）

Spanをクリックして「Generation」タブを開くと、会話履歴が見やすく表示されます：

```
💬 system
  あなたは研究チームのリーダーエージェントです...

💬 user
  最新の情報を検索して日本の内閣総理大臣を教えてください

💬 assistant
  このタスクは最新情報を必要とするので、delegate_to_researcherを使用します。

  🔧 tool_call: delegate_to_researcher
     args: {"task": "日本の内閣総理大臣の最新情報を検索"}

📦 tool_return
  2025年10月21日、高市早苗氏が第104代内閣総理大臣に指名されました...

💬 assistant
  2025年10月21日、高市早苗氏が...
```

### 3. Details Tab（メトリクス）

- **Input tokens**: 457
- **Output tokens**: 110
- **Total cost**: $0.000172
- **Duration**: 4.519s
- **Model**: gemini-2.5-flash-lite

### 4. Explore（SQL分析）

Logfire UIの「Explore」タブで、SQLクエリによる集計・分析が可能です：

```sql
-- トークン使用量の推移
SELECT
  DATE_TRUNC('hour', start_timestamp) as hour,
  SUM(gen_ai_usage_input_tokens) as total_input,
  SUM(gen_ai_usage_output_tokens) as total_output
FROM records
WHERE span_name = 'agent run'
GROUP BY hour
ORDER BY hour DESC;

-- Agent別の実行時間
SELECT
  attributes->>'agent_name' as agent,
  AVG(duration) as avg_duration,
  COUNT(*) as runs
FROM records
WHERE span_name = 'agent run'
GROUP BY agent;

-- コストの集計
SELECT
  DATE(start_timestamp) as date,
  SUM((attributes->'logfire.metrics'->'operation.cost'->>'total')::float) as daily_cost
FROM records
WHERE span_name = 'agent run'
GROUP BY date
ORDER BY date DESC;
```

## Logfire環境変数

Logfireの設定は環境変数で制御できます。

```{note}
標準ロギング（コンソール/ファイル出力）の環境変数については、[標準ロギング設定](#標準ロギング設定)セクションを参照してください。
```

```bash
# Logfire有効化
export LOGFIRE_ENABLED=1
export LOGFIRE_PRIVACY_MODE=full

mixseek team "..." --config team.toml
# --logfireフラグなしでもLogfireが有効化される
```

### Logfire環境変数一覧

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `LOGFIRE_ENABLED` | "1"で有効化 | なし（無効） |
| `LOGFIRE_PRIVACY_MODE` | "full", "metadata_only", "disabled" | "metadata_only" |
| `LOGFIRE_CAPTURE_HTTP` | "1"でHTTPキャプチャ | なし（無効） |
| `LOGFIRE_PROJECT` | プロジェクト名 | .logfireから読み込み |
| `LOGFIRE_SEND_TO_LOGFIRE` | "1"でLogfireクラウドへ送信 | "1" |
| `LOGFIRE_TOKEN` | Logfire認証トークン（本番環境） | .logfireから読み込み |

#### 環境変数の詳細

**プロジェクト名の設定（オプション）**

環境変数 `LOGFIRE_PROJECT` でプロジェクト名を明示的に指定できます。

```bash
# 環境変数で設定
export LOGFIRE_PROJECT="my-project"
```

```{note}
`LOGFIRE_PROJECT` は通常、`.logfire/` ディレクトリの設定またはトークンから自動的に決定されるため、明示的な指定は必須ではありません。複数プロジェクトがある場合や明示的に切り替えたい場合に使用します。
```

**本番環境での認証**

開発環境では `uv run logfire auth` で認証情報が `.logfire/` ディレクトリに保存されますが、本番環境（CI/CD、コンテナなど）では環境変数 `LOGFIRE_TOKEN` を使用します。

```bash
# 本番環境での最小構成
export LOGFIRE_TOKEN="your-logfire-token-here"
export LOGFIRE_PRIVACY_MODE="metadata_only"
mixseek team "..." --config team.toml --logfire

# プロジェクトを明示的に指定する場合（推奨）
export LOGFIRE_TOKEN="your-logfire-token-here"
export LOGFIRE_PROJECT="production-project"
export LOGFIRE_PRIVACY_MODE="metadata_only"
mixseek team "..." --config team.toml --logfire
```

```{important}
**認証に関する重要事項**

- `LOGFIRE_TOKEN` はLogfireライブラリが自動的に読み取ります
- トークンは通常、特定のプロジェクトに紐付いています
- `LOGFIRE_PROJECT` を省略した場合、トークンのデフォルトプロジェクトが使用されます
- 複数プロジェクトがある場合は `LOGFIRE_PROJECT` の明示的な指定を推奨します
```

**トークンの取得方法**

Logfire UIから取得できます：
1. [Logfire Dashboard](https://logfire.pydantic.dev/) にアクセス
2. Settings → Write Tokens
3. "Create token" をクリック
4. トークンをコピーして `LOGFIRE_TOKEN` に設定

**Logfire設定の優先順位**:

1. CLIフラグ（`--logfire`）
2. 環境変数（`LOGFIRE_ENABLED`等）
3. デフォルト値（無効）

## 既存の出力方式との併用

### DuckDBとの併用

```bash
mixseek team "..." --config team.toml --save-db --logfire
```

- DuckDB: 永続化、後からSQL分析
- Logfire: リアルタイム可視化、デバッグ

### JSON出力との併用

```bash
mixseek team "..." --config team.toml --output-format json --logfire > result.json
```

- JSON: プログラム的にアクセス、パイプライン統合
- Logfire: 同時にリアルタイム観測

### 3つ全て併用

```bash
mixseek team "..." --config team.toml --output-format json --save-db --logfire > result.json
```

最も包括的な記録方法です。

## トラブルシューティング

### Logfire not installed

```
ImportError: Logfire not installed. Install with: uv sync --extra logfire
```

**解決方法**:

```bash
uv sync --extra logfire
```

### Logfire initialization failed

```
WARNING: Logfire initialization failed: ...
```

**原因**:
- Logfire認証が未完了
- `.logfire`ディレクトリがない
- プロジェクトが設定されていない

**解決方法**:

```bash
uv run logfire auth
uv run logfire projects new
```

### データが表示されない

**確認事項**:

1. **Logfireが有効化されているか確認**
   ```bash
   mixseek team "..." --config team.toml --logfire
   # "✓ Logfire observability enabled"メッセージが表示される
   ```

2. **正しいプロジェクトが選択されているか確認**
   ```bash
   cat .logfire/logfire_credentials.json
   ```

3. **Logfire UIのプロジェクトが正しいか確認**
   - UIの左上でプロジェクト名を確認

### プライバシー要件

センシティブなデータを送信したくない場合：

```bash
# メタデータのみ
mixseek team "..." --config team.toml --logfire metadata
```

または完全にLogfireを無効化：

```bash
mixseek team "..." --config team.toml
# --logfireフラグなし
```

## OpenTelemetry互換性

Logfireクラウドの代わりに、任意のOpenTelemetryバックエンドを使用できます。

### 代替バックエンドの設定

```bash
# 環境変数で代替エンドポイントを指定
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export LOGFIRE_SEND_TO_LOGFIRE=0

mixseek team "..." --config team.toml --logfire
```

### サポート済みバックエンド

- Langfuse（LLM特化の観測）
- W&B Weave（ML実験トラッキング）
- Arize（プロダクションモニタリング）
- Grafana Tempo（セルフホスト）
- その他のOpenTelemetry準拠バックエンド

詳細は[Pydantic AI Logfireドキュメント](https://ai.pydantic.dev/logfire/#using-opentelemetry)を参照してください。

## ベストプラクティス

### 開発環境

```bash
# フルモードで詳細確認
mixseek team "..." --config team.toml --logfire full
```

### ステージング環境

```bash
# メタデータのみ（プライバシー保護）
mixseek team "..." --config team.toml --logfire metadata
```

### 本番環境

```bash
# Logfire無効（最速）
mixseek team "..." --config team.toml

# または選択的に有効化
mixseek team "..." --config team.toml --logfire metadata
```

### デバッグ時

```bash
# HTTPキャプチャでプロンプト詳細確認
mixseek team "..." --config team.toml --logfire http
```

## コスト管理

### Logfire無料ティア

- 月間100万spans
- データ保持: 30日間

小規模チームには十分です。

### コスト最適化戦略

1. **開発環境のみ有効化**: 本番環境では`--logfire`なし
2. **メタデータモード**: `--logfire metadata`でデータ量削減
3. **選択的実行**: 重要な実行のみLogfire有効化

## 参考資料

- [Logfire公式ドキュメント](https://logfire.pydantic.dev/)
- [Pydantic AI Logfire統合](https://ai.pydantic.dev/logfire/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
