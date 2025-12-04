# Docker + Streamlit UI 統合ガイド

## 概要

このガイドでは、Docker環境でMixseek Streamlit UIを実行する方法を説明します。

### Docker環境の利点

- 依存関係の自動管理
- 環境の一貫性
- ホストシステムの汚染を回避
- 本番環境デプロイの簡素化

### 対象読者

- Docker開発環境を使用する開発者
- Docker環境でMixseek UIをデプロイする運用担当者
- CI/CD統合を行うDevOpsエンジニア

## 前提条件

- Docker Engine 20.10以降
- Make 4.0以降
- Git（ソースコード取得用）

## セットアップ

### Step 1: 環境設定ファイルの準備

環境変数ファイル`.env.dev`を作成します:

```bash
cp dockerfiles/dev/.env.dev.template .env.dev
```

`.env.dev`を編集して必要な環境変数を設定:

```bash
# Mixseek Workspace
MIXSEEK_WORKSPACE=/workspace

# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_GEMINI_API_KEY=your-google-api-key

# Optional: Logfire
LOGFIRE_TOKEN=your-logfire-token
```

### Step 2: Dockerイメージのビルド

開発用Dockerイメージをビルドします:

```bash
cd dockerfiles/dev
make build
```

ビルドには5-10分程度かかります。以下が含まれます:
- Python 3.13.9 + uv
- Node.js 22.20.0
- AI開発ツール（Claude Code, Codex, Gemini CLI）
- Mixseek-Core依存関係（streamlit, plotly, duckdb含む）

### Step 3: コンテナの起動

バックグラウンドでコンテナを起動します:

```bash
make run
```

起動メッセージ:

```text
🚀 Starting development container: mixseek-core-dev
✅ Development container started
💡 Connect with: make bash
💡 Start Streamlit UI: make streamlit
🔗 Container name: mixseek-core-dev
🔗 Exposed ports: 5678 (debug), 8501 (streamlit)
```

`make run`は以下を自動的に行います:
- ポート5678（デバッグ）と8501（Streamlit）の公開
- プロジェクトディレクトリの`/app`へのマウント
- `.cache`と`.config`ディレクトリのマウント
- `.env.dev`の環境変数読み込み

### Step 4: Streamlit UIの起動

コンテナ内でStreamlitを起動します:

```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
make streamlit
```

出力:

```text
🎨 Starting Streamlit UI (Feature 076-ui)
🔗 Streamlit will be available at http://localhost:8501
💡 Make sure container was started with: docker run -p 8501:8501 ...
```

ブラウザで`http://localhost:8501`にアクセスします。

## Makefileターゲット

### コンテナライフサイクル

```bash
make run       # コンテナを起動（バックグラウンド）
make stop      # コンテナを停止
make restart   # コンテナを再起動
make rm        # コンテナを削除
make status    # コンテナとイメージのステータス表示
```

### シェルアクセス

```bash
make bash      # コンテナ内のbashシェルに接続
make root      # root権限でシェルに接続
make exec ARG='command'  # コンテナ内でコマンド実行
```

### Streamlit UI

```bash
make streamlit # Streamlit UIを起動（対話モード）
```

### 開発ツール

```bash
make lint      # コードリンティング（ruff）
make format    # コードフォーマット（ruff）
make check     # 型チェック（mypy）
make unittest  # ユニットテスト実行
```

## ポートマッピング

### デフォルト公開ポート

`make run`は以下のポートを自動的に公開します:

| ポート | 用途 | 説明 |
|--------|------|------|
| 5678 | デバッグ | debugpy（Python デバッガー） |
| 8501 | Streamlit UI | Streamlit アプリケーション |

### カスタムポートマッピング

手動でポートを追加する場合:

```bash
docker run \
  --name mixseek-core-dev \
  -p 5678:5678 \
  -p 8501:8501 \
  -p 8888:8888 \
  -v $(pwd):/app \
  --env-file=.env.dev \
  -d mixseek-core/dev:latest
```

## ワークスペースの永続化

### ホスト側ディレクトリのマウント

ワークスペースをホスト側にマウントしてデータを永続化:

```bash
docker run \
  --name mixseek-core-dev \
  -p 8501:8501 \
  -v $(pwd):/app \
  -v $HOME/mixseek-workspace:/workspace \
  -e MIXSEEK_WORKSPACE=/workspace \
  --env-file=.env.dev \
  -d mixseek-core/dev:latest
```

この設定により、`$HOME/mixseek-workspace`に保存されたデータは、コンテナを削除しても保持されます。

### `.cache`と`.config`の永続化

`make run`は自動的に以下をマウントします:

```bash
-v $(ROOTDIR)/.cache:/home/appuser/.cache
-v $(ROOTDIR)/.config:/home/appuser/.config
```

これにより、uv依存関係キャッシュと設定ファイルが永続化されます。

## 本番デプロイ

### ヘッドレスモード

本番環境では、Streamlitをヘッドレスモードで起動します:

```bash
mixseek ui \
  --server.headless true \
  --server.port 8501 \
  --server.address 0.0.0.0
```

### Dockerfile例（本番用）

本番環境向けの軽量Dockerfileの例:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV MIXSEEK_WORKSPACE=/workspace
ENV PYTHONUNBUFFERED=1

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit
CMD ["uv", "run", "streamlit", "run", "src/mixseek/ui/app.py", \
     "--server.headless", "true", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0"]
```

### Docker Composeでのデプロイ

`docker-compose.yml`の例:

```yaml
version: '3.8'

services:
  mixseek-ui:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    volumes:
      - ./workspace:/workspace
    environment:
      - MIXSEEK_WORKSPACE=/workspace
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_GEMINI_API_KEY=${GOOGLE_GEMINI_API_KEY}
    env_file:
      - .env.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

起動:

```bash
docker-compose up -d
```

## CI/CD統合

### GitHub Actions例

`.github/workflows/ui-test.yml`:

```yaml
name: UI Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  ui-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          cd dockerfiles/dev
          make build

      - name: Start container
        run: |
          cd dockerfiles/dev
          make run

      - name: Run UI tests
        run: |
          cd dockerfiles/dev
          make exec ARG='pytest tests/ui/ -v'

      - name: Stop container
        if: always()
        run: |
          cd dockerfiles/dev
          make stop
          make rm
```

## トラブルシューティング

### ポート8501が既に使用中

**症状**: コンテナ起動時に`bind: address already in use`エラー。

**解決方法**:

既存のコンテナまたはプロセスを確認:

```bash
docker ps | grep 8501
lsof -i :8501
```

既存のコンテナを停止:

```bash
docker stop <container-id>
```

または、別のポートを使用:

```bash
docker run -p 8502:8501 mixseek-core/dev:latest
```

### ワークスペースマウントエラー

**症状**: `permission denied`または`cannot access /workspace`エラー。

**解決方法**:

ホスト側のディレクトリが存在するか確認:

```bash
ls -la $HOME/mixseek-workspace
```

ディレクトリが存在しない場合は作成:

```bash
mkdir -p $HOME/mixseek-workspace
```

UID/GID一致を確認（`dockerfiles/dev/Makefile`の`MIXSEEK_UID`と`MIXSEEK_GID`）:

```bash
id -u  # ホスト側のUID
id -g  # ホスト側のGID
```

### Streamlit起動失敗

**症状**: `make streamlit`実行時にエラー。

**解決方法**:

コンテナログを確認:

```bash
docker logs mixseek-core-dev
```

コンテナ内で手動実行:

```bash
make bash
mixseek ui --server.address 0.0.0.0
```

環境変数`MIXSEEK_WORKSPACE`が設定されているか確認:

```bash
make exec ARG='echo $MIXSEEK_WORKSPACE'
```

### イメージビルド失敗

**症状**: `make build`時にエラー。

**解決方法**:

キャッシュをクリアして再ビルド:

```bash
make build-no-cache
```

`.env.dev`ファイルが存在するか確認:

```bash
ls -la .env.dev
```

Docker Engineのバージョン確認:

```bash
docker --version
```

## セキュリティ考慮事項

### APIキーの管理

`.env.dev`ファイルをGit管理下に含めないでください:

```bash
echo ".env.dev" >> .gitignore
```

本番環境では、環境変数をDocker Secretsまたは外部シークレット管理サービスで管理します。

### 非rootユーザー

開発用Dockerfileは非rootユーザー（`appuser`）で実行されます。これはセキュリティのベストプラクティスです。

### ネットワーク分離

本番環境では、Streamlit UIをリバースプロキシ（Nginx, Traefik）の背後に配置し、認証を追加することを推奨します。

## パフォーマンス最適化

### uvキャッシュの活用

`make run`は`.cache`ディレクトリをマウントし、uv依存関係キャッシュを再利用します。これにより、コンテナ再起動時の依存関係インストール時間が短縮されます。

### マルチステージビルド

本番用Dockerfileでは、マルチステージビルドを使用してイメージサイズを削減できます:

```dockerfile
# Build stage
FROM python:3.13-slim AS builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Runtime stage
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["streamlit", "run", "src/mixseek/ui/app.py", "--server.headless", "true"]
```

## 関連ドキュメント

- [Mixseek UIガイド](ui-guide.md) - UI操作方法
- [Dockerセットアップ](docker-setup.md) - Docker環境の詳細設定
- [開発者ガイド](developer-guide.md) - 開発環境全般
- [クイックスタート](quickstart.md) - Mixseek-Coreの基本
