# Mixseek UI ガイド

## 概要

Mixseek UIは、Streamlitベースのウェブインターフェースで、Mixseekオーケストレーションの実行と監視を提供します。

### 主要機能

- **実行ページ**: オーケストレーション選択とタスク実行
- **結果ページ**: リーダーボードとサブミッション詳細
- **履歴ページ**: 過去の実行履歴とフィルタリング
- **設定ページ**: TOML設定ファイルの管理

### 利用シーン

- インタラクティブなマルチエージェント実行
- リアルタイムな結果比較
- 設定ファイルのビジュアル編集
- 実行履歴の分析

## セットアップ

### 前提条件

**システム要件**:
- Python 3.13.9
- uvパッケージマネージャー
- Linux/macOS/Windows（Streamlit対応環境）

**依存関係**:
- streamlit >=1.51.0
- plotly >=6.4.0
- duckdb >=1.3.1
- pydantic >=2.0
- tomllib（Python 3.13標準ライブラリ）

### インストール手順

**Step 1: 依存関係のインストール**

プロジェクトルートディレクトリで実行:

```bash
uv sync
```

**Step 2: 環境変数の設定**

`MIXSEEK_WORKSPACE`環境変数を設定します。

Linux/macOS:

```bash
export MIXSEEK_WORKSPACE=/path/to/your/workspace
```

永続化する場合（`~/.bashrc`または`~/.zshrc`に追加）:

```bash
echo 'export MIXSEEK_WORKSPACE=/path/to/your/workspace' >> ~/.bashrc
source ~/.bashrc
```

Windows (PowerShell):

```powershell
$env:MIXSEEK_WORKSPACE = "C:\path\to\your\workspace"
```

環境変数の確認:

```bash
echo $MIXSEEK_WORKSPACE
```

**設定の優先順位**:

`MIXSEEK_WORKSPACE`は以下の優先順位で適用されます：

1. CLI引数（`--workspace`オプション） - 最高優先度
2. 環境変数（`MIXSEEK_WORKSPACE`）
3. デフォルト値（未設定時はエラー）

**Step 3: ワークスペースディレクトリの作成**

```bash
mkdir -p $MIXSEEK_WORKSPACE/configs
```

**Step 4: サンプル設定ファイルの作成（オプション）**

```bash
cat > $MIXSEEK_WORKSPACE/configs/example.toml <<'EOF'
# Mixseek Configuration File - Example

# Member Agents
[[member_agents]]
agent_id = "researcher"
provider = "anthropic"
model = "claude-sonnet-4"
system_prompt = "You are a research assistant. Provide detailed, well-researched answers."
temperature = 0.7
max_tokens = 4096

[[member_agents]]
agent_id = "coder"
provider = "google-adk"
model = "google-gla:gemini-2.5-flash"
system_prompt = "You are a coding expert. Write clean, efficient code."
temperature = 0.3
max_tokens = 8192

# Leader Agents
[[leader_agents]]
agent_id = "coordinator"
provider = "anthropic"
model = "claude-sonnet-4-5"
system_prompt = "You are a team coordinator. Delegate tasks and synthesize results."
temperature = 0.5
max_tokens = 8192

# Orchestrations
[[orchestrations]]
orchestration_id = "research_team"
leader_agent_id = "coordinator"
member_agent_ids = ["researcher", "coder"]
description = "Research team with coordinator, researcher, and coder"
EOF
```

### アプリケーション起動

プロジェクトルートディレクトリから実行:

```bash
# 推奨: CLIコマンド
mixseek ui

# または直接実行
uv run streamlit run src/mixseek/ui/app.py
```

期待される出力:

```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

ブラウザで`http://localhost:8501`にアクセスします。

## Logfire観測機能

Mixseek UIでもLogfireによるリアルタイム観測が利用可能です。

### 使用方法

Logfireを有効化するには、`mixseek ui`コマンドにLogfireオプションを追加します。

```bash
# Full mode（すべてキャプチャ）- 開発環境推奨
export LOGFIRE_PROJECT=your-project-name
mixseek ui --logfire

# Metadata only mode（本番推奨）- プロンプト/応答を除外
mixseek ui --logfire-metadata

# Full + HTTP capture（デバッグ用）
mixseek ui --logfire-http
```

### プライバシーモード

| モード | オプション | 内容 |
|--------|-----------|------|
| Full | `--logfire` | プロンプト、応答、メトリクスをすべて記録（開発環境） |
| Metadata only | `--logfire-metadata` | メトリクスのみ記録、プロンプト/応答除外（本番推奨） |
| Full + HTTP | `--logfire-http` | Full + HTTPリクエスト/レスポンスをキャプチャ（デバッグ用） |

### Logfire初期化の確認

Logfireが正常に有効化されると、UIのサイドバーに以下の表示がされます：

- 成功時: `Logfire enabled (full)` または `Logfire enabled (metadata_only)`
- 未インストール時: `Logfire not installed (uv sync --extra logfire)`
- 初期化失敗時: エラーメッセージ

### Logfire未インストール時のセットアップ

```bash
# Logfireエクストラをインストール
uv sync --extra logfire

# Logfire認証（初回のみ）
uv run logfire auth

# プロジェクト作成（初回のみ）
uv run logfire projects new
```

### 環境変数による設定

CLIオプションの代わりに、環境変数でLogfireを有効化することもできます。

```bash
# Logfire有効化
export LOGFIRE_ENABLED=1
export LOGFIRE_PROJECT=your-project-name
export LOGFIRE_PRIVACY_MODE=metadata_only  # full, metadata_only, disabled

# UI起動（環境変数が自動的に適用される）
mixseek ui
```

詳細は[observability.md](observability.md)を参照してください。

## 機能詳細

### 実行ページ

タスクの実行とオーケストレーションの選択を行います。

**操作手順**:

1. オーケストレーション選択ドロップダウンから設定ファイルとオーケストレーションを選択
2. タスクプロンプト欄にタスク内容を入力
3. 「実行」ボタンをクリック

**進行状況表示**: 実行中は"実行中..."と表示され、チーム別の進捗状況がリアルタイムで更新されます。

**実行ログ**: 「実行ログ」セクションでは、オーケストレーション実行中のログをリアルタイムで確認できます。

- 折りたたみ可能なパネルで表示（デフォルトは閉じた状態）
- INFO以上のログレベルのメッセージを表示
- スクロールで過去のログを追跡可能
- 実行完了後もログを参照可能

ログ表示により、エラー発生時の原因特定やデバッグが容易になります。

**完了表示**: 実行完了後、結果サマリーが表示されます。

### 結果ページ

最新の実行結果をリーダーボード形式で表示します。

**表示内容**:
- チーム順位とスコア
- トップサブミッションの詳細
- チーム比較

**操作**:
- 任意のチームをクリックして詳細ビューを表示

### 履歴ページ

過去の実行履歴を一覧表示します。

**表示内容**:
- 実行ID
- プロンプト概要
- 実行日時
- ステータス

**操作**:
- フィルタリング: ステータスや日付で絞り込み
- ソート: 日時、スコアで並べ替え
- 詳細ビュー: 任意の実行をクリックして詳細を表示

### 設定ページ

TOML設定ファイルの管理を行います。

**既存ファイルの編集**:

1. 設定ファイル一覧からファイルを選択
2. TOML内容が編集可能なテキストエリアに表示される
3. 内容を編集
4. 「保存」ボタンをクリック

**新規ファイルの作成**:

1. 「新規作成」ボタンをクリック
2. ファイル名を入力（例: `my_config.toml`）
3. テンプレート構造が自動生成される
4. 内容を編集
5. 「保存」ボタンをクリック

**バリデーション**: TOML構文エラーは保存時に検出され、エラーメッセージが表示されます。

## トラブルシューティング

### `MIXSEEK_WORKSPACE not set`エラー

**症状**: Streamlitアプリ起動時に`ValueError: MIXSEEK_WORKSPACE environment variable is not set`が表示される。

**解決方法**:
1. 環境変数が設定されているか確認: `echo $MIXSEEK_WORKSPACE`
2. 未設定の場合は環境変数を設定
3. Streamlitアプリを再起動

### `configs/`ディレクトリが見つからない

**症状**: 実行ページで「設定ファイルが見つかりません」と表示される。

**解決方法**:
1. ディレクトリが存在するか確認: `ls $MIXSEEK_WORKSPACE/configs/`
2. ディレクトリが存在しない場合は作成: `mkdir -p $MIXSEEK_WORKSPACE/configs`
3. サンプル設定ファイルを作成
4. Streamlitアプリをリロード（ブラウザでF5キー）

### TOML構文エラー

**症状**: 設定ページでファイルを選択すると「構文エラー: ...」が表示される。

**解決方法**:
1. エラーメッセージの行番号を確認
2. TOMLファイルを直接編集して構文を修正
3. TOML構文の確認:
   - キーと値の形式: `key = "value"`
   - セクション: `[[section_name]]`
   - コメント: `# comment`
4. Streamlitアプリをリロード

### `mixseek.db`が見つからない

**症状**: 結果ページまたは履歴ページで「データがありません」と表示される。

**解決方法**:

これは正常な動作です（初回起動時はデータベースが未作成）。実行ページでタスクを実行すると自動的に`mixseek.db`が作成されます。タスク実行後、結果ページ・履歴ページを確認してください。

### 実行ログが表示されない

**症状**: 「実行ログ」セクションに「ログがありません」と表示される。

**解決方法**:

1. ログファイルが存在するか確認: `ls $MIXSEEK_WORKSPACE/logs/mixseek.log`
2. ログディレクトリが存在しない場合は、タスクを実行すると自動作成されます
3. ログレベルがINFO以上であることを確認（DEBUG以下は表示されません）

### ポート8501が既に使用中

**症状**: `OSError: Address already in use`が表示される。

**解決方法**:

別のポートを指定してStreamlitを起動:

```bash
mixseek ui --server.port 8502
```

または、既存のプロセスを終了:

```bash
lsof -i :8501
kill -9 <PID>
```

## 本番環境での実行

ヘッドレスモードで起動（サーバー環境）:

```bash
mixseek ui \
  --server.headless true \
  --server.port 8501 \
  --server.address 0.0.0.0
```

## 複数ワークスペースの使い分け

複数のワークスペースを並行して使用する場合:

```bash
# ワークスペースAで起動
MIXSEEK_WORKSPACE=/path/to/workspace_a mixseek ui --server.port 8501

# ワークスペースBで起動
MIXSEEK_WORKSPACE=/path/to/workspace_b mixseek ui --server.port 8502
```

## リファレンス

### 環境変数

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MIXSEEK_WORKSPACE` | Yes | - | ワークスペースディレクトリのパス。未設定時はエラー終了 |

### ディレクトリ構造

```text
$MIXSEEK_WORKSPACE/
├── configs/             # 設定ファイルディレクトリ（自動作成）
│   ├── example.toml     # サンプル設定ファイル
│   └── my_config.toml   # ユーザー作成の設定ファイル
├── logs/                # ログディレクトリ（実行時に自動作成）
│   └── mixseek.log      # アプリケーションログ
└── mixseek.db           # DuckDBデータベース（実行時に自動作成）
```

### Streamlit設定（オプション）

カスタムStreamlit設定（`.streamlit/config.toml`）:

```toml
[server]
port = 8501
headless = true

[runner]
enforceSerializableSessionState = true

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

## 関連ドキュメント

- [Docker + Streamlit UI統合](ui-docker.md) - Docker環境での実行方法
- [開発者ガイド](developer-guide.md) - 開発環境の詳細
- [クイックスタート](quickstart.md) - Mixseek-Coreの基本的な使い方
