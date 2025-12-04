# MixSeek-Core Docker開発環境

このディレクトリには、MixSeek-Coreプロジェクト用のDockerベース開発環境テンプレートが含まれており、開発、CI/CD、本番ステージ全体で標準化された再現可能な環境を提供します。

## 🏗️ アーキテクチャ概要

```
dockerfiles/
├── Makefile.common          # 共有ユーティリティと共通ターゲット
├── dev/                     # 開発環境
│   ├── Dockerfile          # AIツール付きフル開発環境
│   ├── Makefile           # 開発ワークフローコマンド
│   └── .env.dev.template  # 開発環境変数テンプレート
├── ci/                      # CI/CD環境
│   ├── Dockerfile          # 最小テスト環境
│   ├── Makefile           # CIパイプラインコマンド
│   └── .env.ci.template   # CI環境変数テンプレート
└── prod/                    # 本番環境
    ├── Dockerfile          # セキュア・最小ランタイム環境
    ├── Makefile           # 本番デプロイメントコマンド
    └── .env.prod.template # 本番環境変数テンプレート
```

## 🚀 クイックスタート

### 前提条件

- Docker Engine 20.10以降
- Docker Compose 2.0以降（オプション）
- Make 4.0以降
- Git 2.30以降
- 最低3GBの空きディスク容量

### 1. 環境セットアップ

```bash
# 開発環境の設定ファイルをコピー・設定
cp dockerfiles/dev/.env.dev.template .env.dev
vim .env.dev  # APIキーと設定を記述

# Dockerが動作していることを確認
docker info
```

### 2. 開発環境の起動

```bash
# 開発コンテナをビルド・起動
make -C dockerfiles/dev build
make -C dockerfiles/dev run

# 開発コンテナに接続
make -C dockerfiles/dev bash

# コンテナ内で動作確認
python --version  # Python 3.12.x
node --version    # Node.js 22.20.0
uv --version      # uvパッケージマネージャー
claude-code --version  # AI開発ツール
```

### 3. テストの実行

```bash
# 完全なテストスイートを実行
make -C dockerfiles/dev unittest

# コード品質チェック
make -C dockerfiles/dev lint
make -C dockerfiles/dev format
```

## 📋 環境比較表

| 機能 | 開発環境 | CI環境 | 本番環境 |
|------|----------|-------|----------|
| **ベースイメージ** | uv:0.8.24-python3.12 | uv:0.8.24-python3.12 | python:3.12-slim |
| **Pythonツール** | フル（uv, pytest, ruff, debugpy, mypy） | テスト（uv, pytest, ruff, coverage） | ランタイムのみ |
| **Node.js** | ✅ 22.20.0 | ❌ | ❌ |
| **AIツール** | ✅ Claude Code, Codex, Gemini CLI | ❌ | ❌ |
| **デバッグサポート** | ✅ ポート5678 | ❌ | ❌ |
| **セキュリティ強化** | 基本 | 中程度 | 最大 |
| **ボリュームマウント** | 読み書き | 読み取り専用 | なし |
| **マルチステージビルド** | ❌ | ❌ | ✅ |
| **イメージサイズ** | ~1.2GB | ~600MB | ~300MB |

## 🛠️ 開発ワークフロー

### 日常の開発作業

```bash
# 開発セッションを開始
make -C dockerfiles/dev build && make -C dockerfiles/dev run
make -C dockerfiles/dev bash

# コンテナ内での一般的なワークフロー
make lint          # コード品質チェック
make format        # コードフォーマット
make unittest      # テスト実行
make claude-code ARG="--help"  # AIアシスタントを使用

# スクリプトのデバッグ
make -C dockerfiles/dev debug ARG="src/main.py"
```

### AI開発ツール

開発環境には3つのAIコーディングアシスタントが含まれています：

```bash
# Claude Code（Anthropic）
make -C dockerfiles/dev claude-code ARG="analyze src/main.py"

# OpenAI Codex
make -C dockerfiles/dev codex ARG="generate function to parse JSON"

# Google Gemini CLI
make -C dockerfiles/dev gemini ARG="review src/main.py"
```

### ホットリロード開発

```bash
# ファイル監視による自動リロードを有効化
make -C dockerfiles/dev watch
```

## 🧪 CI/CDパイプライン

### ローカルCIテスト

```bash
# CI環境をビルド
make -C dockerfiles/ci build

# 完全なCIパイプラインを実行
make -C dockerfiles/ci pipeline

# 特定のCIタスクを実行
make -C dockerfiles/ci test-full        # 完全なテストスイート
make -C dockerfiles/ci coverage         # カバレッジレポート
make -C dockerfiles/ci security-scan    # セキュリティ脆弱性
make -C dockerfiles/ci quality-gate     # すべての品質チェック
```

### CIレポート

すべてのCI実行は以下にレポートを生成します：
- `test-reports/` - テスト結果とJUnit XML
- `coverage-reports/` - コードカバレッジ（XML/HTML）
- `security-reports/` - セキュリティスキャン結果

## 🚀 本番デプロイメント

### 本番ビルド

```bash
# 本番イメージをビルド
make -C dockerfiles/prod build

# 本番環境へデプロイ
make -C dockerfiles/prod deploy

# デプロイメントの監視
make -C dockerfiles/prod health-check
make -C dockerfiles/prod monitoring
```

### ブルーグリーンデプロイメント

```bash
# ゼロダウンタイムデプロイメントを実行
make -C dockerfiles/prod deploy-blue-green

# 必要に応じてロールバック
make -C dockerfiles/prod rollback PREV_TAG=2025-10-14-abc123
```

### 本番監視

```bash
# リアルタイム監視
make -C dockerfiles/prod logs-follow
make -C dockerfiles/prod metrics
make -C dockerfiles/prod health-check

# メンテナンスモード
make -C dockerfiles/prod maintenance-on
make -C dockerfiles/prod maintenance-off
```

## 🔐 セキュリティ機能

### 開発環境
- 非rootユーザーでの実行
- ホットリロード用ボリュームマウント
- デバッグポート公開（5678）
- 環境変数によるAPIキー管理

### CI環境
- 読み取り専用ファイルシステム
- セキュリティケーパビリティドロップ（`--cap-drop=ALL`）
- `/tmp`用一時ファイルシステム
- 非特権ユーザー実行
- セキュリティスキャン（Bandit、Safety、pip-audit）

### 本番環境
- 攻撃対象面を最小化するマルチステージビルド
- 読み取り専用ルートファイルシステム
- 開発ツールやデバッグ機能なし
- `no-new-privileges`によるセキュリティ強化
- ヘルスチェックと監視
- コンテナリソース制限

## 📊 環境変数

各環境はセキュアなテンプレートベース設定を使用します：

### 開発環境（`.env.dev`）
- AIツールAPIキー（Claude、OpenAI、Gemini）
- 開発用データベース接続
- デバッグとログ設定
- クラウドプロバイダー認証情報

### CI環境（`.env.ci`）
- テストデータベース設定
- カバレッジ閾値
- セキュリティスキャン設定
- アーティファクト保存設定

### 本番環境（`.env.prod`）
- 本番データベース接続（Dockerシークレット経由）
- キャッシュ設定
- 監視エンドポイント
- セキュリティ設定

## 🐞 トラブルシューティング

### よくある問題

#### Dockerビルドが失敗する場合
```bash
# Dockerデーモンの確認
sudo systemctl status docker

# ビルドキャッシュをクリア
docker system prune -a
make -C dockerfiles/dev build
```

#### 権限エラーの場合
```bash
# UID/GID同期の確認
id
make -C dockerfiles/dev build  # 正しい権限で再ビルド
```

#### ポート競合エラーの場合
```bash
# ポート使用状況の確認
sudo lsof -i :5678

# 既存のコンテナを停止
make -C dockerfiles/dev stop
make -C dockerfiles/dev rm
```

#### AIツールが動作しない場合
```bash
# APIキーの確認
cat .env.dev | grep API_KEY

# コンテナの再起動
make -C dockerfiles/dev restart
```

### 環境のリセット

完全な環境リセット：
```bash
# すべてのコンテナを停止
make -C dockerfiles/dev cleanup
make -C dockerfiles/ci cleanup
make -C dockerfiles/prod cleanup

# 環境ファイルを削除
rm .env.dev .env.ci .env.prod

# 最初からやり直し
cp dockerfiles/dev/.env.dev.template .env.dev
# 設定を記述...
make -C dockerfiles/dev build
```

## 📚 高度な使用方法

### カスタムAI開発ワークフロー
```bash
# AI支援付きで開発を開始
make -C dockerfiles/dev run
make -C dockerfiles/dev bash

# コンテナ内で
claude-code analyze . --output suggestions.md
codex generate --description "ユーザー管理用REST APIエンドポイント"
gemini-cli review src/ --format markdown
```

### 並行開発
```bash
# 複数の開発者が同時に作業可能
USER1: make -C dockerfiles/dev run   # コンテナ: mixseek-core-dev
USER2: CONTAINER_NAME=mixseek-core-dev-2 make -C dockerfiles/dev run
```

### CI統合
```bash
# CI/CDパイプラインでの使用例（.github/workflows/ci.yml）
- name: CIパイプラインの実行
  run: |
    cp dockerfiles/ci/.env.ci.template .env.ci
    make -C dockerfiles/ci pipeline

- name: アーティファクトの収集
  run: make -C dockerfiles/ci collect-artifacts
```

## 🔄 メンテナンス

### 定期的なタスク

```bash
# ベースイメージの更新（月次）
docker pull ghcr.io/astral-sh/uv:0.8.24-python3.12-bookworm-slim
make -C dockerfiles/dev build --no-cache

# セキュリティアップデート
make -C dockerfiles/ci security-scan
make -C dockerfiles/prod security-audit

# 未使用リソースのクリーンアップ
docker system prune -a
```

### バージョン管理

```bash
# 利用可能なバージョンの一覧表示
make -C dockerfiles/prod list-versions

# アップデート前のバックアップ作成
make -C dockerfiles/prod backup-image

# リリースのタグ付け
docker tag mixseek-core/prod:latest mixseek-core/prod:v1.0.0
```

## 📖 ドキュメント

- [Dockerファイルインターフェース契約](../specs/003-dockerfiles/contracts/dockerfile-interface.md)
- [Makefileインターフェース契約](../specs/003-dockerfiles/contracts/makefile-interface.md)
- [環境テンプレート契約](../specs/003-dockerfiles/contracts/environment-template.md)
- [クイックスタートガイド](../specs/003-dockerfiles/quickstart.md)
- [データモデル](../specs/003-dockerfiles/data-model.md)

## 🎯 使用例とベストプラクティス

### 新規プロジェクト開始時
```bash
# 1. 環境テンプレートをコピー
cp dockerfiles/dev/.env.dev.template .env.dev

# 2. 必要なAPIキーを設定
vim .env.dev
# ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
# OPENAI_API_KEY=sk-your-openai-key-here
# GOOGLE_AI_API_KEY=AIza-your-gemini-key-here

# 3. 開発環境をビルド・起動
make -C dockerfiles/dev build
make -C dockerfiles/dev run

# 4. 開発開始
make -C dockerfiles/dev bash
```

### テスト駆動開発のワークフロー
```bash
# 1. テストファイルを作成
vim tests/test_new_feature.py

# 2. テストを実行（失敗することを確認）
make -C dockerfiles/dev unittest

# 3. 実装
vim src/new_feature.py

# 4. テストが通るまで繰り返し
make -C dockerfiles/dev unittest

# 5. コード品質チェック
make -C dockerfiles/dev lint
make -C dockerfiles/dev format
```

### AI支援開発のワークフロー
```bash
# 1. Claude Codeでコード分析
make -C dockerfiles/dev claude-code ARG="analyze src/main.py --suggestions"

# 2. Codexでコード生成
make -C dockerfiles/dev codex ARG="generate --description 'エラーハンドリング付きHTTPクライアント'"

# 3. Gemini CLIでコードレビュー
make -C dockerfiles/dev gemini ARG="review src/ --focus security,performance"

# 4. 生成されたコードの統合・テスト
make -C dockerfiles/dev unittest
```

### チーム開発環境の統一
```bash
# プロジェクトルートに環境セットアップスクリプトを作成
cat > setup-dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 MixSeek-Core開発環境セットアップ"

# 前提条件チェック
if ! command -v docker &> /dev/null; then
    echo "❌ Dockerがインストールされていません"
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "❌ Makeがインストールされていません"
    exit 1
fi

# 環境変数ファイルのセットアップ
if [ ! -f .env.dev ]; then
    echo "📋 開発環境設定ファイルをセットアップ"
    cp dockerfiles/dev/.env.dev.template .env.dev
    echo "⚠️  .env.devファイルを編集してAPIキーを設定してください"
    echo "📝 設定が必要な項目："
    echo "   - ANTHROPIC_API_KEY（Claude Code用）"
    echo "   - OPENAI_API_KEY（Codex用）"
    echo "   - GOOGLE_AI_API_KEY（Gemini CLI用）"
    exit 0
fi

# 開発環境の構築・起動
echo "🔨 開発環境をビルド"
make -C dockerfiles/dev build

echo "🚀 開発環境を起動"
make -C dockerfiles/dev run

echo "✅ セットアップ完了！"
echo "🔗 コンテナに接続: make -C dockerfiles/dev bash"
echo "🧪 テスト実行: make -C dockerfiles/dev unittest"
echo "🔍 コード品質: make -C dockerfiles/dev lint"
EOF

chmod +x setup-dev.sh
```

## 🤝 チーム開発のコツ

### 環境の一貫性確保
```bash
# チーム全体で同じバージョンを使用
echo "dockerfiles/dev Dockerfile のベースイメージバージョンを固定"
# FROM ghcr.io/astral-sh/uv:0.8.24-python3.12-bookworm-slim

# 依存関係のロック
uv lock  # uv.lockファイルを更新
git add uv.lock
git commit -m "Update dependency lock file"
```

### コードレビュー前のチェック
```bash
# プルリクエスト前の品質チェック
make -C dockerfiles/dev lint
make -C dockerfiles/dev format
make -C dockerfiles/dev unittest
make -C dockerfiles/ci quality-gate

# AI支援によるコードレビュー準備
make -C dockerfiles/dev claude-code ARG="review-prep src/ --output review-notes.md"
```

### CI/CD統合のベストプラクティス
```yaml
# .github/workflows/ci.yml の例
name: CI Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Setup CI Environment
      run: |
        cp dockerfiles/ci/.env.ci.template .env.ci
        # 必要に応じてCI用の環境変数を設定

    - name: Run CI Pipeline
      run: make -C dockerfiles/ci pipeline

    - name: Upload Test Reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-reports
        path: |
          test-reports/
          coverage-reports/
          security-reports/
```

## ⚠️ 重要な注意事項

### セキュリティ
- **APIキーの管理**: `.env.dev`ファイルは絶対にgitにコミットしないでください
- **本番環境**: 本番環境では必ずDockerシークレットを使用してください
- **権限管理**: コンテナ内では非rootユーザーで動作します

### パフォーマンス
- **初回ビルド**: 初回は依存関係のダウンロードで時間がかかります（5-10分程度）
- **キャッシュ活用**: `--no-cache`オプションは必要な場合のみ使用してください
- **リソース管理**: 大きなプロジェクトでは十分なメモリ（4GB以上推奨）を確保してください

### トラブル時の連絡先
Docker環境で問題が発生した場合：

1. 上記のトラブルシューティングセクションを確認
2. コンテナログを確認: `make -C dockerfiles/[env] logs`
3. 環境を検証: `make -C dockerfiles/[env] validate`
4. システムリソースを確認: `docker system df`

## 🔄 更新履歴

- **v1.0.0** (2025-10-15): 初期リリース
  - 開発、CI、本番環境の実装
  - AI開発ツールの統合
  - セキュリティ強化とテンプレートシステム

---

**バージョン**: 1.0.0 | **最終更新**: 2025-10-15 | **メンテナンス**: MixSeek-Core開発チーム