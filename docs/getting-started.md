# はじめに - 5分でスタート

このガイドでは、MixSeek-Coreを使って5分以内に最初のニュース検索を実行する方法を説明します。

## 前提条件

- **uv がインストール済み** - Pythonパッケージマネージャー（Pythonバージョン管理機能内蔵）
- ターミナル/コマンドプロンプトが使える

### uvのインストール

`uv`は高速なPythonパッケージマネージャーで、Python本体のバージョン管理も行います。必要なPythonバージョンは`uv`が自動的にダウンロード・管理します。

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**パッケージマネージャー経由:**
```bash
# macOS (Homebrew)
brew install uv

# Windows (WinGet)
winget install --id=astral-sh.uv -e

# pipx経由（既存のPython環境がある場合）
pipx install uv
```

詳細は [uv公式インストールガイド](https://docs.astral.sh/uv/getting-started/installation/) を参照してください。

### mixseek-coreのインストール

**方法1: CLIツールとしてインストール（推奨）**

グローバルに`mixseek`コマンドを使えるようにします：

```bash
# uvを最新版にアップデート
uv self update

# CLIツールとしてインストール（必要なPythonバージョンも自動的にダウンロードされます）
uv tool install git+https://github.com/mixseek/mixseek-core.git

# コマンドが使えることを確認
mixseek --version
```

以降、仮想環境を有効化せずに`mixseek`コマンドが使えます。

**方法2: Pythonパッケージとしてインストール**

プログラムから使用するライブラリとしてインストール：

```bash
# pipを使用
pip install git+https://github.com/mixseek/mixseek-core.git

# uvを使用
uv pip install git+https://github.com/mixseek/mixseek-core.git

# プロジェクト依存関係に追加（uv）
uv add git+https://github.com/mixseek/mixseek-core.git
```

> **重要**: 方法2のuvでインストールした場合、コマンド実行時に`uv run`プレフィックスが必要です（例: `uv run mixseek init`）。本ガイドでは方法1を前提に説明します。

## ステップ1: ワークスペースの初期化

MixSeekのワークスペースを作成します。ワークスペースには、設定ファイルとログが保存されます。

```bash
mixseek init --workspace $HOME/mixseek-workspace
```

> **注意**: 方法2でインストールした場合は`uv run mixseek init ...`としてください。

**実行結果**:
```
Workspace initialized successfully at: /Users/username/mixseek-workspace
Created directories: 6
Created files: 7
```

> **補足**: `MIXSEEK_WORKSPACE` 環境変数を設定すると、各コマンドで `--workspace` オプションの指定が不要になります。
>
> ```bash
> export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
> mixseek init  # --workspace オプション不要
> ```

初期化により、以下のファイルが作成されます：

```
mixseek-workspace/
├── configs/
│   ├── search_news.toml                       # シンプルなニュース検索設定
│   ├── search_news_multi_perspective.toml     # 多視点ニュース検索設定
│   ├── agents/
│   │   ├── team_general_researcher.toml       # 汎用調査チーム
│   │   ├── team_sns_researcher.toml           # SNS特化チーム
│   │   └── team_academic_researcher.toml      # 学術特化チーム
│   ├── evaluators/
│   │   └── evaluator_search_news.toml         # 評価設定
│   └── judgment/
│       └── judgment_search_news.toml          # 判定設定
├── logs/                                       # ログファイル保存先
└── templates/                                  # カスタムテンプレート保存先
```

## ステップ2: API認証の設定

Google Gemini APIまたはVertex AIの認証情報を設定します。

### オプションA: Gemini Developer API（個人・プロトタイピング向け）

```bash
export GOOGLE_API_KEY=your-api-key
```

APIキーの取得方法については [Gemini API 公式ドキュメント](https://ai.google.dev/gemini-api/docs/api-key) を参照してください。

### オプションB: Vertex AI（エンタープライズ向け）

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp_credentials.json
```

GCPサービスアカウントのクレデンシャルファイルを指定してください。

## ステップ3: 最初のニュース検索を実行

すぐに使える設定ファイルを使って、ニュース検索を実行します。

```bash
mixseek exec \
  --workspace $HOME/mixseek-workspace \
  --config configs/search_news.toml \
  "ソフトバンクのニュースを調べてください。"
```

> **注意**: 方法2でインストールした場合は`uv run mixseek exec ...`としてください。

**実行内容**:
1. 汎用調査チームがWeb検索を実行
2. 検索結果をまとめて回答を生成
3. 評価システムが回答を評価（Coverage, Relevance, Novelty, Clarity）
   - `Novelty` は `LLMPlain` メトリクスを使ったカスタム評価指標です
4. 結果をコンソールに出力

**実行時間**: 約1分

## 設定ファイルの説明

### `search_news.toml` - シンプルなニュース検索

```toml
[orchestrator]
timeout_per_team_seconds = 180
min_rounds = 1
max_rounds = 2

[[orchestrator.teams]]
config = "configs/agents/team_general_researcher.toml"
```

- **単一チーム**: 汎用調査チームのみを使用
- **高速実行**: 1〜2ラウンドで完了
- **デフォルト評価**: システムデフォルトの評価設定を使用

**参考**: 詳細は [オーケストレーターガイド](./orchestrator-guide.md) を参照

### `team_general_researcher.toml` - 汎用調査チーム

```toml
[team]
team_id = "general-researcher-team"
team_name = "General Research Team"

[team.leader]
model = "google-gla:gemini-2.5-flash"
temperature = 0.7

[[team.members]]
name = "general-searcher"
type = "web_search"
model = "google-gla:gemini-2.5-flash"
```

- **Leader Agent**: チーム全体の調整とまとめを担当
- **Member Agent**: Web検索を実行してニュース情報を収集
- **モデル**: Gemini 2.5 Flash を使用（高速・低コスト）

**参考**: 詳細は [チームガイド](./team-guide.md) を参照

## 次のステップ

### さらに学ぶ

基本的なニュース検索ができたら、次のステップに進みましょう：

- **[はじめに（発展編）](./getting-started-advanced.md)** - 多視点検索、カスタマイズ、Web UIの使い方
- **[オーケストレーターガイド](./orchestrator-guide.md)** - 複数チームの並行実行と評価
- **[チームガイド](./team-guide.md)** - チーム設定の詳細とカスタマイズ方法

## トラブルシューティング

### エラー: "No API key found"

**原因**: Google APIキーが設定されていない

**解決策**:
```bash
export GOOGLE_API_KEY=your-api-key
# または
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### エラー: "Workspace not found"

**原因**: ワークスペースが初期化されていない

**解決策**:
```bash
mixseek init --workspace $HOME/mixseek-workspace
```

### エラー: "Config file not found"

**原因**: 設定ファイルのパスが正しくない

**解決策**:
```bash
# ワークスペース基準の相対パスを使用
mixseek exec \
  --workspace $HOME/mixseek-workspace \
  --config configs/search_news.toml \
  "query"

# または絶対パスを使用
mixseek exec \
  --workspace $HOME/mixseek-workspace \
  --config $HOME/mixseek-workspace/configs/search_news.toml \
  "query"
```

> **注意**: 方法2でインストールした場合は`uv run`プレフィックスを追加してください。

## 関連ドキュメント

### 次のステップ
- [はじめに（発展編）](./getting-started-advanced.md) - 多視点検索とカスタマイズ
- [クイックスタートガイド](./quickstart.md) - 詳細なセットアップガイド

### 詳細ガイド
- [オーケストレーターガイド](./orchestrator-guide.md) - オーケストレーション設定の詳細
- [チームガイド](./team-guide.md) - チーム設定とカスタマイズ
- [UIガイド](./ui-guide.md) - Web UIの使い方

### リファレンス
- [設定リファレンス](./configuration-reference.md) - 全設定項目の詳細
- [設定ガイド](./configuration-guide.md) - 設定ファイルの書き方

---

**Version**: 1.1.0
**Last Updated**: 2025-12-04
