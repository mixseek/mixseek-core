# Quickstart: Mixseek UI

**Feature**: 076-ui | **Date**: 2025-11-06 | **Phase**: 1 (Design & Contracts)

## Overview

本ドキュメントは、Mixseek UIの初回セットアップとStreamlitアプリケーション起動方法を説明する。開発者と運用管理者を対象とし、環境変数設定からアプリケーション起動、初回設定ファイル作成までの手順を提供する。

---

## Prerequisites

### System Requirements

- **Python**: 3.13.9
- **Package Manager**: uv（既存プロジェクトで使用）
- **OS**: Linux/macOS/Windows（Streamlit対応環境）

### Dependencies

以下の依存関係は`pyproject.toml`に追加される（Phase 2実装時）:

```toml
[project.dependencies]
streamlit = ">=1.51.0"
plotly = ">=6.4.0"
duckdb = ">=1.3.1"
pydantic = ">=2.0"
# Note: tomllib（Python 3.13標準ライブラリ）を使用するため外部パッケージ不要
```

### Workspace Directory

Mixseek UIは環境変数`MIXSEEK_WORKSPACE`で指定されたディレクトリをワークスペースとして使用する。

---

## Installation

### Step 1: Install Dependencies

プロジェクトルートディレクトリで以下を実行:

```bash
uv sync
```

**Note**: `uv sync`は`pyproject.toml`の依存関係を自動的にインストールする。

### Step 2: Set Environment Variable

環境変数`MIXSEEK_WORKSPACE`を設定する。

#### Linux/macOS

```bash
export MIXSEEK_WORKSPACE=/path/to/your/workspace
```

**永続化する場合** (`~/.bashrc` または `~/.zshrc`に追加):

```bash
echo 'export MIXSEEK_WORKSPACE=/path/to/your/workspace' >> ~/.bashrc
source ~/.bashrc
```

#### Windows (PowerShell)

```powershell
$env:MIXSEEK_WORKSPACE = "C:\path\to\your\workspace"
```

**永続化する場合** (システム環境変数に追加):

```powershell
[System.Environment]::SetEnvironmentVariable("MIXSEEK_WORKSPACE", "C:\path\to\your\workspace", "User")
```

#### 環境変数の確認

```bash
echo $MIXSEEK_WORKSPACE
```

**期待される出力**: `/path/to/your/workspace`（設定したパス）

---

## Initial Setup

### Step 3: Create Workspace Directory

ワークスペースディレクトリを作成:

```bash
mkdir -p $MIXSEEK_WORKSPACE/configs
```

**Note**: Mixseek UI起動時に`configs/`ディレクトリが存在しない場合は自動作成されるが、手動で事前作成することも可能。

### Step 4: Create Sample Config File

初回起動前にサンプル設定ファイルを作成する（オプション）:

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
model = "gemini-2.0-flash-exp"
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

---

## Running the Application

### Step 5: Start Streamlit App

プロジェクトルートディレクトリから以下を実行:

```bash
# 推奨: CLIコマンドを使用
mixseek ui

# または、直接Streamlitを実行
uv run streamlit run src/mixseek/ui/app.py
```

**期待される出力**:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

### Step 6: Access the UI

ブラウザで以下のURLにアクセス:

```
http://localhost:8501
```

**初回起動時の画面構成**:
- **ナビゲーション**: 実行、結果、履歴、設定の4ページ
- **サイドバー**: ワークスペースパス表示
- **実行ページ（デフォルト）**: オーケストレーション選択、タスクプロンプト入力

---

## First-Time Configuration

### Step 7: Navigate to Settings Page

ナビゲーションから「設定」ページを開く。

### Step 8: Create or Edit Config File

#### 既存ファイルの編集

1. 設定ファイル一覧から`example.toml`（または既存ファイル）を選択
2. TOML内容が編集可能なテキストエリアに表示される
3. 内容を編集（Member Agent追加、Leader Agent変更など）
4. 「保存」ボタンをクリック

**成功メッセージ**: "example.tomlを保存しました"

#### 新規ファイルの作成

1. 「新規作成」ボタンをクリック
2. ファイル名を入力（例: `my_config.toml`）
3. テンプレート構造が自動生成される
4. 内容を編集
5. 「保存」ボタンをクリック

**成功メッセージ**: "my_config.tomlを保存しました"

---

## Running Your First Task

### Step 9: Execute a Task

1. ナビゲーションから「実行」ページを開く
2. オーケストレーション選択ドロップダウンから`example.toml - research_team`を選択
3. タスクプロンプト欄に以下を入力:

   ```
   What are the key benefits of using multi-agent systems in AI applications?
   ```

4. 「実行」ボタンをクリック

**進行状況表示**: "実行中..."

**完了表示**: "実行完了" + 結果サマリー

### Step 10: View Results

1. ナビゲーションから「結果」ページを開く
2. リーダーボードが表示される（チーム順位、スコア）
3. トップサブミッションのハイライトが表示される
4. 任意のチームをクリックして詳細ビューを確認

### Step 11: Check History

1. ナビゲーションから「履歴」ページを開く
2. 過去の実行履歴が一覧表示される（実行ID、プロンプト概要、日時、ステータス）
3. 任意の実行をクリックして詳細を表示

---

## Troubleshooting

### Issue 1: `MIXSEEK_WORKSPACE not set`エラー

**症状**: Streamlitアプリ起動時に`ValueError: MIXSEEK_WORKSPACE environment variable is not set`が表示される

**解決方法**:
1. 環境変数が設定されているか確認: `echo $MIXSEEK_WORKSPACE`
2. 未設定の場合は Step 2 を実行
3. Streamlitアプリを再起動

### Issue 2: `configs/`ディレクトリが見つからない

**症状**: 実行ページで「設定ファイルが見つかりません」と表示される

**解決方法**:
1. `$MIXSEEK_WORKSPACE/configs/`ディレクトリが存在するか確認:
   ```bash
   ls $MIXSEEK_WORKSPACE/configs/
   ```
2. ディレクトリが存在しない場合は作成:
   ```bash
   mkdir -p $MIXSEEK_WORKSPACE/configs
   ```
3. サンプル設定ファイルを作成（Step 4参照）
4. Streamlitアプリをリロード（ブラウザでF5キー）

### Issue 3: TOML構文エラー

**症状**: 設定ページでファイルを選択すると「構文エラー: ...」が表示される

**解決方法**:
1. エラーメッセージの行番号を確認
2. TOMLファイルを直接編集して構文を修正:
   ```bash
   $EDITOR $MIXSEEK_WORKSPACE/configs/example.toml
   ```
3. TOML構文の確認:
   - キーと値の形式: `key = "value"`
   - セクション: `[[section_name]]`
   - コメント: `# comment`
4. Streamlitアプリをリロード

### Issue 4: `mixseek.db`が見つからない

**症状**: 結果ページまたは履歴ページで「データがありません」と表示される

**解決方法**:
1. これは正常な動作（初回起動時はデータベースが未作成）
2. 実行ページでタスクを実行すると自動的に`mixseek.db`が作成される
3. タスク実行後、結果ページ・履歴ページを確認

### Issue 5: ポート8501が既に使用中

**症状**: `OSError: Address already in use`が表示される

**解決方法**:
1. 別のポートを指定してStreamlitを起動:
   ```bash
   mixseek ui --port 8502
   # または
   uv run streamlit run src/mixseek/ui/app.py --server.port 8502
   ```
2. または、既存のプロセスを終了:
   ```bash
   lsof -i :8501
   kill -9 <PID>
   ```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MIXSEEK_WORKSPACE` | Yes | - | ワークスペースディレクトリのパス。未設定時はエラー終了 |

### Directory Structure

```
$MIXSEEK_WORKSPACE/
├── configs/             # 設定ファイルディレクトリ（自動作成）
│   ├── example.toml     # サンプル設定ファイル
│   └── my_config.toml   # ユーザー作成の設定ファイル
└── mixseek.db           # DuckDBデータベース（実行時に自動作成）
```

### Streamlit Configuration (Optional)

カスタムStreamlit設定（`.streamlit/config.toml`）:

```toml
[server]
port = 8501
headless = true

[runner]
enforceSerializableSessionState = true  # Article 9準拠

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

---

## Advanced Usage

### Running in Production

**推奨設定**:

```bash
# ヘッドレスモードで起動（サーバー環境）
uv run streamlit run src/mixseek/ui/app.py --server.headless true --server.port 8501 --server.address 0.0.0.0
```

### Docker Deployment (Future)

Dockerfileの例（Phase 2以降で実装）:

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install uv
RUN uv sync

ENV MIXSEEK_WORKSPACE=/workspace

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/mixseek/ui/app.py", "--server.headless", "true", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

### Multiple Workspaces

複数のワークスペースを使い分ける:

```bash
# ワークスペースAで起動
MIXSEEK_WORKSPACE=/path/to/workspace_a mixseek ui --port 8501

# ワークスペースBで起動
MIXSEEK_WORKSPACE=/path/to/workspace_b mixseek ui --port 8502
```

---

## Next Steps

### For Developers

1. **Phase 2実装**: `/speckit.tasks`でtasks.mdを生成し、実装タスクを開始
2. **テスト実行**: `pytest tests/ui/`でUIテストを実行
3. **Code Quality**: `ruff check --fix . && ruff format . && mypy .`でコード品質を確保

### For Operators

1. **設定ファイルの追加**: 設定ページで新規`.toml`ファイルを作成
2. **タスク実行**: 実行ページでさまざまなオーケストレーションを試す
3. **履歴分析**: 履歴ページで過去の実行を振り返り、パターンを分析

### For Users

1. **ドキュメント参照**: `docs/`ディレクトリでMixseek-Coreの詳細を確認
2. **フィードバック**: GitHubイシューで機能リクエストやバグ報告を提出
3. **コミュニティ**: 他のユーザーとベストプラクティスを共有

---

## Summary

このQuickstartガイドでは、以下の手順を説明しました:

1. ✅ 依存関係のインストール（`uv sync`）
2. ✅ 環境変数`MIXSEEK_WORKSPACE`の設定
3. ✅ ワークスペースディレクトリと`configs/`の作成
4. ✅ サンプル設定ファイルの作成
5. ✅ Streamlitアプリの起動（`mixseek ui`）
6. ✅ 初回設定（設定ページでファイル作成・編集）
7. ✅ 初回タスク実行（実行ページでタスクを実行）
8. ✅ 結果・履歴の確認

これでMixseek UIを使い始める準備が整いました！
