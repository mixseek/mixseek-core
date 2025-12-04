# クイックスタートガイド: Docker開発環境テンプレート

**機能**: Docker開発環境テンプレート
**作成日**: 2025-10-15
**推定セットアップ時間**: 10分以内

## 概要

このガイドは、Docker開発環境テンプレートを使用してmixseek-coreプロジェクトの開発環境を迅速にセットアップする手順を説明します。

## 前提条件

### 必須要件

- **Docker Engine**: 20.10以降
- **Docker Compose**: 2.0以降（オプション）
- **Git**: 2.30以降
- **Make**: GNU Make 4.0以降
- **十分なディスク容量**: 最低3GB（全環境構築の場合）

### システム要件確認

```bash
# Docker確認
docker --version
docker info

# Make確認
make --version

# Git確認
git --version

# ディスク容量確認
df -h .
```

**期待される出力例**:
```
Docker version 24.0.0
GNU Make 4.3
git version 2.39.0
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       50G   20G   28G  42% /
```

## 開発環境セットアップ (推定5分)

### ステップ1: リポジトリクローン (30秒)

```bash
# リポジトリをクローン
git clone [REPOSITORY_URL] mixseek-core
cd mixseek-core
```

### ステップ2: 環境変数設定 (2分)

```bash
# 開発環境テンプレートをコピー
cp dockerfiles/templates/.env.dev.template .env.dev

# エディタで設定ファイルを編集
vim .env.dev
```

**必須設定項目**:
```bash
# 基本設定
TZ=Asia/Tokyo                              # お住いのタイムゾーン
DEBUG=true                                 # 開発モードを有効

# AI開発ツール（使用する場合のみ）
ANTHROPIC_API_KEY=sk-ant-api03-...         # Claude CodeのAPIキー
OPENAI_API_KEY=sk-...                      # OpenAI CodexのAPIキー
GOOGLE_AI_API_KEY=AIza...                  # Gemini CLIのAPIキー

# データベース（プロジェクトが使用する場合）
DATABASE_URL=postgresql://user:pass@localhost:5432/mixseek_dev
```

**設定ファイル例**:
```bash
# システム設定
TZ=Asia/Tokyo
DEBUG=true
LOG_LEVEL=DEBUG
PYTHONDONTWRITEBYTECODE=1

# AI開発ツール
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-3-sonnet
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4

# 開発ツール設定
HOT_RELOAD_ENABLED=true
DEBUGPY_PORT=5678
DEBUGPY_ENABLED=false
```

### ステップ3: 開発環境構築 (3分)

```bash
# Dockerネットワーク作成
make -C dockerfiles/dev create_network

# 開発コンテナビルド
make -C dockerfiles/dev build

# ビルド完了確認
docker images | grep mixseek-core/dev
```

**代替方法（ディレクトリ移動）**:
```bash
cd dockerfiles/dev
make create_network
make build
cd ../..  # プロジェクトルートに戻る
```

**期待される出力**:
```
mixseek-core/dev   latest   abc123def456   2 minutes ago   1.1GB
```

### ステップ4: 開発コンテナ起動 (30秒)

```bash
# 開発コンテナを起動（バックグラウンド）
make -C dockerfiles/dev run

# 起動確認
docker ps | grep mixseek-core-dev

# コンテナに接続
make -C dockerfiles/dev bash
```

**コンテナ内で確認**:
```bash
# Python環境確認
python --version
which python

# uv確認
uv --version

# Node.js確認
node --version
npm --version

# AI開発ツール確認
claude-code --version
codex --version
gemini-cli --version

# 作業ディレクトリ確認
pwd
ls -la
```

**期待される出力**:
```
Python 3.13.9
/venv/bin/python
uv 0.8.24
v22.20.0
10.x.x
claude-code 1.x.x
codex 2.x.x
gemini-cli 1.x.x
/app
```

## 開発ワークフローテスト (推定2分)

### コード品質チェック

```bash
# リント実行
make -C dockerfiles/dev lint

# フォーマット実行
make -C dockerfiles/dev format

# 型チェック実行（mypyが設定されている場合）
make -C dockerfiles/dev check
```

### テスト実行

```bash
# 全テスト実行
make -C dockerfiles/dev unittest

# 特定のテストファイル実行
make -C dockerfiles/dev only-test ARG=tests/test_example.py

# テスト結果確認
echo $?  # 0が成功、非0がエラー
```

### AI開発ツール動作確認

```bash
# Claude Code動作確認
make -C dockerfiles/dev claude-code ARG="--help"

# デバッグモード起動（別ターミナルで）
make -C dockerfiles/dev debug ARG="python/example_script.py"
```

## トラブルシューティング

### よくある問題と解決策

#### 1. Docker ビルドエラー

**症状**: `make -C dockerfiles/dev build`でエラーが発生
```
ERROR [internal] load build definition from Dockerfile
```

**解決策**:
```bash
# Docker daemon状態確認
sudo systemctl status docker

# Docker daemon再起動
sudo systemctl restart docker

# ビルドキャッシュクリア
docker system prune -a
make -C dockerfiles/dev build
```

#### 2. ポート競合エラー

**症状**: コンテナ起動時にポートエラー
```
Error: bind: address already in use
```

**解決策**:
```bash
# 使用中のポート確認
sudo lsof -i :5678

# 既存コンテナ停止
make -C dockerfiles/dev stop
make -C dockerfiles/dev rm

# 再起動
make -C dockerfiles/dev run
```

#### 3. UID/GID権限エラー

**症状**: ファイル編集時に権限エラー
```
Permission denied
```

**解決策**:
```bash
# ホストUID/GID確認
id

# コンテナ再ビルド（UID/GID同期）
make -C dockerfiles/dev rm
make -C dockerfiles/dev build
make -C dockerfiles/dev run
```

#### 4. AI開発ツールAPIエラー

**症状**: Claude Code/Codex実行時にAPIエラー
```
API key not found
```

**解決策**:
```bash
# 環境変数確認
docker exec mixseek-core-dev env | grep API_KEY

# .env.devファイル確認
cat .env.dev | grep API_KEY

# コンテナ再起動
make -C dockerfiles/dev restart
```

#### 5. Node.js/npmエラー

**症状**: AI開発ツールインストール失敗
```
npm: command not found
```

**解決策**:
```bash
# コンテナ内でNode.js確認
make -C dockerfiles/dev bash
node --version
npm --version

# PATH確認
echo $PATH

# nvmロード
source $NVM_DIR/nvm.sh
nvm use 22.20.0
```

### 環境リセット

完全に環境をリセットする場合：

```bash
# すべてのコンテナ停止・削除
make -C dockerfiles/dev stop
make -C dockerfiles/dev rm

# イメージ削除
docker rmi mixseek-core/dev:latest

# 環境設定削除
rm .env.dev

# ネットワーク削除
docker network rm mixseek-core-network

# 最初からセットアップ
cp dockerfiles/templates/.env.dev.template .env.dev
# （環境変数を再設定）
make -C dockerfiles/dev create_network
make -C dockerfiles/dev build
make -C dockerfiles/dev run
```

## 追加環境セットアップ

### CI環境セットアップ (推定2分)

```bash
# CI環境テンプレート設定
cp dockerfiles/templates/.env.ci.template .env.ci

# CI環境ビルド
make -C dockerfiles/ci build

# テスト実行
make -C dockerfiles/ci test-full
```

### 本番環境セットアップ (推定3分)

```bash
# 本番環境テンプレート設定
cp dockerfiles/templates/.env.prod.template .env.prod
vim .env.prod  # 本番設定を入力

# 本番環境ビルド
make -C dockerfiles/prod build

# セキュリティスキャン
make -C dockerfiles/prod security-scan
```

## 次のステップ

### 開発開始

環境が正常にセットアップされたら：

1. **コード編集**: ホスト側でコードを編集（ホットリロード有効）
2. **テスト駆動開発**: `make -C dockerfiles/dev unittest`でテスト実行
3. **コード品質維持**: `make -C dockerfiles/dev lint && make -C dockerfiles/dev format`で品質チェック
4. **AI支援開発**: Claude Code、Codex、Gemini CLIを活用

### 設定カスタマイズ

プロジェクトのニーズに応じて：

1. **環境変数追加**: `.env.dev`にプロジェクト固有の設定を追加
2. **ポート設定**: `dockerfiles/dev/Makefile`でポートマッピング調整
3. **追加ツール**: Dockerfileに必要なツールを追加

### チーム展開

チーム全体での使用時：

1. **ドキュメント共有**: このクイックスタートガイドをチームに共有
2. **テンプレート標準化**: 環境変数テンプレートをプロジェクト要件に合わせて調整
3. **CI/CD統合**: CI環境をパイプラインに統合

## パフォーマンスメトリクス

### セットアップ時間目標

| 段階 | 目標時間 | 実測時間 |
|------|----------|----------|
| 環境変数設定 | 2分 | ___分 |
| Docker build | 3分 | ___分 |
| コンテナ起動 | 30秒 | ___秒 |
| 動作確認 | 2分 | ___分 |
| **合計** | **10分以内** | **___分** |

### リソース使用量

```bash
# ビルド完了後のリソース確認
docker images | grep mixseek-core
docker stats mixseek-core-dev --no-stream
```

**期待される値**:
- **開発イメージサイズ**: < 1.2GB
- **メモリ使用量**: < 512MB（アイドル時）
- **CPU使用率**: < 5%（アイドル時）

これで、mixseek-coreプロジェクトの開発環境セットアップが完了です！問題が発生した場合は、トラブルシューティングセクションを参照してください。