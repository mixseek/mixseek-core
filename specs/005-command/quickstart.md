# Quick Start: mixseek init コマンド

**Date**: 2025-10-16
**Purpose**: このドキュメントは、mixseek initコマンドの基本的な使用方法を説明します。

## 前提条件

- Python 3.12+ がインストールされている
- mixseek-core パッケージがインストールされている（将来的にPyPI経由）
- ターミナル/コマンドプロンプトへのアクセス

## インストール

```bash
# PyPI経由でインストール（将来対応）
pip install mixseek-core

# または、uvを使用
uv pip install mixseek-core
```

## 基本的な使用方法

### 1. 環境変数を使用したワークスペース初期化

```bash
# 環境変数を設定
export MIXSEEK_WORKSPACE=/path/to/your/workspace

# ワークスペースを初期化
mixseek init
```

**出力例**:
```
Workspace initialized successfully at: /path/to/your/workspace
Created directories: 6
Created files: 7
```

### 2. CLIオプションを使用したワークスペース初期化

```bash
# --workspace オプションを使用
mixseek init --workspace /path/to/your/workspace

# 短縮形を使用
mixseek init -w /path/to/your/workspace
```

### 3. 相対パスを使用

```bash
# 現在のディレクトリ配下に作成
mixseek init --workspace ./my-workspace

# 親ディレクトリに作成
mixseek init --workspace ../project-workspace
```

## 作成されるディレクトリ構造

```
your-workspace/
├── logs/                                          # ログファイルを保存するディレクトリ
├── configs/                                       # 設定ファイルを保存するディレクトリ
│   ├── search_news.toml                          # シンプルなニュース検索オーケストレーター
│   ├── search_news_multi_perspective.toml        # 多視点ニュース検索オーケストレーター
│   ├── agents/
│   │   ├── team_general_researcher.toml          # 汎用調査チーム設定
│   │   ├── team_sns_researcher.toml              # SNS特化チーム設定
│   │   └── team_academic_researcher.toml         # 学術特化チーム設定
│   ├── evaluators/
│   │   └── evaluator_search_news.toml            # 評価設定（4メトリクス）
│   └── judgment/
│       └── judgment_search_news.toml             # 判定設定
└── templates/                                     # テンプレートファイルを保存するディレクトリ
```

## すぐに使える設定ファイル

初期化後、すぐにニュース検索を実行できます：

```bash
# シンプルなニュース検索を実行
mixseek exec \
  --workspace $MIXSEEK_WORKSPACE \
  --config configs/search_news.toml \
  "最新のAI技術について調査してください"

# 多視点での詳細調査を実行
mixseek exec \
  --workspace $MIXSEEK_WORKSPACE \
  --config configs/search_news_multi_perspective.toml \
  "最新のAI技術について調査してください"
```

### 評価メトリクス

生成される評価設定には以下の4つのメトリクスが含まれます：

- **Coverage (30%)**: 情報の網羅性
- **Relevance (25%)**: クエリへの関連性
- **Novelty (25%)**: 新規性・意外性（外れ値の評価）
- **ClarityCoherence (20%)**: 明瞭性と一貫性

## よくある使用例

### 例 1: 新規プロジェクトの開始

```bash
# 1. ワークスペースを初期化
mixseek init --workspace ~/my-mixseek-project/workspace

# 2. 生成されたファイルを確認
ls ~/my-mixseek-project/workspace/configs/
# search_news.toml
# search_news_multi_perspective.toml
# agents/
# evaluators/
# judgment/

# 3. すぐにニュース検索を実行
export MIXSEEK_WORKSPACE=~/my-mixseek-project/workspace
mixseek exec \
  --workspace $MIXSEEK_WORKSPACE \
  --config configs/search_news.toml \
  "最新のAI技術について"
```

### 例 2: 環境変数をシェルプロファイルに追加

```bash
# .bashrc または .zshrc に追加
echo 'export MIXSEEK_WORKSPACE=$HOME/mixseek/workspace' >> ~/.bashrc
source ~/.bashrc

# これで、毎回パスを指定する必要がなくなります
mixseek init
```

### 例 3: スペースを含むパスの処理

```bash
# パスをクォートで囲む
mixseek init --workspace "/home/user/My Projects/workspace"

# または、環境変数を使用
export MIXSEEK_WORKSPACE="/home/user/My Projects/workspace"
mixseek init
```

## トラブルシューティング

### エラー: "Workspace path not specified"

**原因**: `--workspace` オプションも `MIXSEEK_WORKSPACE` 環境変数も指定されていない

**解決策**:
```bash
# オプション1: CLIオプションを使用
mixseek init --workspace /path/to/workspace

# オプション2: 環境変数を設定
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek init
```

### エラー: "Parent directory does not exist"

**原因**: 指定されたパスの親ディレクトリが存在しない

**解決策**:
```bash
# 親ディレクトリを作成
mkdir -p /path/to/parent

# 再試行
mixseek init --workspace /path/to/parent/workspace
```

### エラー: "No write permission"

**原因**: 指定されたディレクトリへの書き込み権限がない

**解決策**:
```bash
# オプション1: 権限を変更（適切な場合）
chmod u+w /path/to/parent

# オプション2: ホームディレクトリ配下を使用
mixseek init --workspace ~/workspace
```

### エラー: "Workspace already exists"

**原因**: 指定されたワークスペースが既に存在する

**解決策**:
```bash
# オプション1: 異なるパスを使用
mixseek init --workspace /different/path

# オプション2: 既存のワークスペースを削除
rm -rf /existing/workspace
mixseek init --workspace /existing/workspace

# オプション3: 上書き確認プロンプトで 'y' を選択（将来実装）
mixseek init --workspace /existing/workspace
# Workspace already exists. Overwrite? [y/N] y
```

## ヘルプの表示

```bash
# 詳細なヘルプを表示
mixseek init --help

# または
mixseek init -h
```

## 次のステップ

1. **ニュース検索の実行**: 生成された設定ファイルを使ってすぐに検索を実行
2. **設定のカスタマイズ**: チーム設定や評価メトリクスの重みを調整
3. **新しいチームの追加**: `configs/agents/` に独自のチーム設定を作成
4. **UI の使用**: `mixseek ui` コマンドでWebインターフェースを起動

## 関連ドキュメント

- [機能仕様書](./spec.md) - 詳細な要件と成功基準
- [実装計画](./plan.md) - 技術スタックと設計決定
- [CLI契約](./contracts/cli-interface.md) - CLIインターフェースの詳細仕様
- [データモデル](./data-model.md) - エンティティと検証ルール

## フィードバック

問題や改善提案がある場合は、プロジェクトのIssue Trackerに報告してください。

---

**Version**: 1.0.0
**Last Updated**: 2025-10-16
