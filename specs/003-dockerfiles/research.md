# Research Report: Docker環境テンプレート実装

**Date**: 2025-10-15
**Status**: Complete
**Context**: Phase 0 research for Docker development environment template implementation

## Research Areas

### 1. マルチ環境Dockerコンテナ設計

#### Decision: マルチステージビルド戦略による環境別最適化

**Rationale**:
- **60-80%のイメージサイズ削減**: マルチステージビルドにより本番イメージのサイズを大幅に削減可能
- **セキュリティ向上**: 本番環境からビルドツールや開発ツールを除外し、攻撃面を最小化
- **環境別最適化**: 開発環境はフル機能、CI環境は基本ツール、本番環境はランタイムのみの構成が可能
- **ビルドキャッシュ効率**: 各ステージが独立してキャッシュされ、変更のないレイヤーは再利用される
- **BuildKit統合**: Docker BuildKitの並列ビルド機能により、使用されないステージは効率的にスキップ

**Implementation Pattern**:
```dockerfile
# Stage 1: Base with common dependencies
FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim AS base
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Stage 2: Builder stage for development
FROM base AS dev
# Install full development toolchain
RUN apt-get update && apt-get install -y \
    curl git build-essential cmake pkg-config \
    libprotobuf-dev protobuf-compiler
# Install Node.js and AI development tools
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
RUN npm install -g @anthropic-ai/claude-code

# Stage 3: CI stage
FROM base AS ci
# Install only Python testing tools
RUN apt-get update && apt-get install -y git
# Install pytest, ruff, coverage only

# Stage 4: Production stage
FROM base AS prod
# Copy only runtime dependencies
# No development or build tools
COPY --from=builder /venv /venv
```

**Alternatives Considered**:
- **単一Dockerfileアプローチ**: 拒否理由 - 本番イメージが不必要に肥大化し、セキュリティリスクが増加
- **完全分離Dockerfile**: 拒否理由 - 共通レイヤーが再利用されず、メンテナンス負荷が高い
- **実行時条件分岐**: 拒否理由 - イメージサイズ削減が不可能で、セキュリティポリシー違反

**Key Benefits for 2025**:
- BuildKitの並列実行により、複数ステージを同時ビルド可能
- レジストリベースの外部キャッシュでCI/CD間でキャッシュ共有可能
- `--target`フラグで環境別ビルドを明示的に指定可能

---

### 2. Node.js + Python統合環境

#### Decision: uvパッケージマネージャーとnvm/npmの統合パターン

**Rationale**:
- **uv採用による40%のCI/CD高速化**: Rustベースのuvは従来のpipより圧倒的に高速
- **マルチ言語コンテナの確立パターン**: Node.jsとPythonの共存は実績のある手法
- **開発環境専用構成**: 本番・CI環境ではNode.jsを除外し、不要な依存関係を排除
- **一般ユーザー権限での実行**: nvmによりroot権限なしでNode.jsとAI開発ツールをインストール可能
- **バージョン管理の柔軟性**: nvmによるNode.jsバージョン切り替えが容易

**Implementation Pattern**:
```dockerfile
# Python 3.13.9+ with uv package manager
FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim

# Non-root user setup
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

USER ${USERNAME}

# Install Node.js with nvm (non-root)
ENV NVM_DIR=$HOME/.nvm
ENV NODE_VERSION=22.20.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    bash -c ". $NVM_DIR/nvm.sh && nvm install $NODE_VERSION"

ENV PATH=$NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# Install AI development tools
RUN npm install -g @anthropic-ai/claude-code

# Python environment setup with uv
ENV VIRTUAL_ENV=/venv
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PATH="/venv/bin:${PATH}"

WORKDIR /app
RUN uv venv /venv

# Optimize dependency installation with cache mounts
COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen --no-install-project
```

**Key uv Optimizations**:
- **UV_COMPILE_BYTECODE=1**: .pycファイル生成により実行時パフォーマンス向上
- **UV_PROJECT_ENVIRONMENT=/venv**: システムPython環境を指定し、追加仮想環境作成を回避
- **--mount=type=cache**: uvキャッシュの永続化により再ビルド時のダウンロードを削減
- **--no-install-project**: 依存関係とプロジェクトコードを分離し、レイヤーキャッシュを最適化

**Alternatives Considered**:
- **pip + requirements.txt**: 拒否理由 - uvに比べて依存関係解決が遅く、現代的なプロジェクト管理に不適合
- **Poetry**: 拒否理由 - uvより遅く、Dockerコンテナ内での使用に最適化されていない
- **Conda**: 拒否理由 - イメージサイズが大きく、軽量コンテナ設計に不適
- **Dockerネイティブツール分離**: 拒否理由 - 開発ワークフローが分断され、開発者体験が低下

**Security Considerations**:
- 一般ユーザー権限でのnpmグローバルインストール
- UID/GIDの明示的な指定によるホストとの権限同期
- AI開発ツールの開発環境専用インストール

---

### 3. 環境変数管理戦略

#### Decision: 環境別専用テンプレートファイル + .gitignore方式

**Rationale**:
- **機密情報の完全分離**: テンプレートファイルはバージョン管理、実際の値は.gitignoreで保護
- **環境別最適化**: .env.dev.template、.env.ci.template、.env.prod.templateで環境固有設定を管理
- **Docker Compose統合**: env_fileディレクティブで環境変数ファイルを読み込み可能
- **セキュリティベストプラクティス準拠**: 環境変数ではなくファイルベースのシークレット管理を推奨（2025年標準）
- **開発者体験の向上**: テンプレートから実際の設定ファイルを生成する明確なワークフロー

**Implementation Pattern**:

**テンプレートファイル構造**:
```
templates/
├── .env.dev.template       # 開発環境用テンプレート
├── .env.ci.template        # CI環境用テンプレート
└── .env.prod.template      # 本番環境用テンプレート
```

**テンプレート例 (.env.dev.template)**:
```bash
# Python環境設定
PYTHONPATH=/app
PYTHON_ENV=development

# AI SDK設定（開発環境用）
ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_API_KEY_HERE>
GOOGLE_ADK_API_KEY=<YOUR_GOOGLE_ADK_API_KEY_HERE>

# データベース設定（開発用ローカル）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mixseek_dev

# ログレベル
LOG_LEVEL=DEBUG
```

**Docker Compose統合**:
```yaml
version: '3.8'
services:
  dev:
    build:
      context: .
      dockerfile: dockerfiles/dev/Dockerfile
    env_file:
      - .env.dev  # Generated from template
    volumes:
      - .:/app
    secrets:
      - db_password
      - api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

**セットアップワークフロー**:
```makefile
.PHONY: setup-env
setup-env:
	@if [ ! -f .env.dev ]; then \
		cp templates/.env.dev.template .env.dev; \
		echo "Created .env.dev from template. Please edit with your values."; \
	fi
```

**.gitignore設定**:
```gitignore
# Environment files (actual values)
.env
.env.*
!.env.*.template

# Secrets directory
secrets/
*.secret
```

**Alternatives Considered**:
- **環境変数のみのアプローチ**: 拒否理由 - 機密情報が誤ってログに出力されるリスク、プロセス間で共有される
- **Docker Secrets単独**: 拒否理由 - Docker Swarmモード必須で、開発環境での使用が複雑化
- **外部シークレット管理システム（Vault等）**: 拒否理由 - 小規模プロジェクトには過剰、追加インフラが必要
- **ハードコード設定**: 拒否理由 - セキュリティリスク、バージョン管理での機密情報公開

**Security Best Practices for 2025**:
- **ファイルベースシークレット**: `/run/secrets/<secret_name>`にマウントされ、環境変数として公開されない
- **短命認証情報**: 可能な限り短命なトークンを使用し、定期的なローテーション実施
- **ログフィルタリング**: シークレット値がログに出力されないようサニタイズ機構を実装
- **実行時シークレット注入**: Phase CLIやDoppler等のツールでdocker-composeプロセスに実行時注入

---

### 4. Makefile駆動のワークフロー統合

#### Decision: 共通Makefile + 環境別Makefileの階層構造

**Rationale**:
- **一貫したコマンドインターフェース**: すべてのプロジェクトで`make build`、`make run`等の統一コマンド
- **環境間での設定抽象化**: 環境固有の詳細をMakefileに隠蔽し、開発者は環境差異を意識不要
- **CI/CD統合の容易性**: MakefileをCI/CDパイプラインのエントリーポイントとして使用
- **ドキュメントとしての実行可能スクリプト**: Makefileが実行可能なドキュメントとして機能
- **Docker + Makefileの確立されたベストプラクティス**: 2025年現在の業界標準パターン

**Implementation Pattern**:

**ディレクトリ構造**:
```
dockerfiles/
├── Makefile.common          # 全環境共通タスク
├── dev/
│   ├── Dockerfile
│   └── Makefile            # 開発環境固有タスク
├── ci/
│   ├── Dockerfile
│   └── Makefile            # CI環境固有タスク
└── prod/
    ├── Dockerfile
    └── Makefile            # 本番環境固有タスク
```

**Makefile.common (共通タスク定義)**:
```makefile
.PHONY: build run rm logs bash

APP_NAME := mixseek-core
NETWORK := $(APP_NAME)-network
TAG := $(shell git log -1 --date=short --format="%ad-%h")
ROOTDIR := $(shell cd "$(dirname $(CURDIR))" &>/dev/null && cd ../../ && pwd -P)

# ホスト環境情報（UID/GID同期用）
HOST_USERNAME := $(shell whoami)
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

# Dockerネットワーク作成
create_network:
	@if docker network inspect ${NETWORK} >/dev/null 2>/dev/null; then \
		echo "Network ${NETWORK} exists"; \
	else \
		docker network create ${NETWORK}; \
	fi

# イメージビルド（BuildKitキャッシュ有効化）
build:
	cd $(ROOTDIR) && \
	DOCKER_BUILDKIT=1 docker build \
		--build-arg USERNAME=$(HOST_USERNAME) \
		--build-arg UID=$(HOST_UID) \
		--build-arg GID=$(HOST_GID) \
		--target $(BUILD_TARGET) \
		-t $(IMAGE_NAME):$(TAG) \
		-t $(IMAGE_NAME):latest \
		-f $(CURDIR)/Dockerfile \
		.

# キャッシュ無効ビルド
build-no-cache:
	cd $(ROOTDIR) && \
	DOCKER_BUILDKIT=1 docker build --no-cache \
		--build-arg USERNAME=$(HOST_USERNAME) \
		--build-arg UID=$(HOST_UID) \
		--build-arg GID=$(HOST_GID) \
		--target $(BUILD_TARGET) \
		-t $(IMAGE_NAME):$(TAG) \
		-f $(CURDIR)/Dockerfile \
		.

# コンテナ接続
bash:
	docker exec -it $(CONTAINER_NAME) bash

# コンテナ削除
rm:
	docker rm -f $(CONTAINER_NAME) || echo "Container not found"

# ログ表示
logs:
	docker logs -f --tail 50 $(CONTAINER_NAME)
```

**dockerfiles/dev/Makefile (開発環境固有)**:
```makefile
include ../Makefile.common

IMAGE_NAME := $(APP_NAME)-dev
CONTAINER_NAME := $(APP_NAME)-dev-container
BUILD_TARGET := dev

# 開発コンテナ起動（ボリュームマウント）
run: create_network
	docker run -d \
		--name $(CONTAINER_NAME) \
		--network $(NETWORK) \
		-v $(ROOTDIR):/app \
		-v /app/.venv \
		--env-file $(ROOTDIR)/.env.dev \
		-p 8000:8000 \
		$(IMAGE_NAME):latest

# 開発ワークフロータスク
unittest:
	docker exec $(CONTAINER_NAME) pytest tests/ -v

lint:
	docker exec $(CONTAINER_NAME) ruff check .

format:
	docker exec $(CONTAINER_NAME) ruff format .

# Claude Codeデバッグモード
claude-debug:
	docker exec -it $(CONTAINER_NAME) claude --dangerously-skip-permissions
```

**dockerfiles/ci/Makefile (CI環境固有)**:
```makefile
include ../Makefile.common

IMAGE_NAME := $(APP_NAME)-ci
CONTAINER_NAME := $(APP_NAME)-ci-container
BUILD_TARGET := ci

# CIテスト実行（一時コンテナ）
run-tests:
	docker run --rm \
		--name $(CONTAINER_NAME) \
		--env-file $(ROOTDIR)/.env.ci \
		$(IMAGE_NAME):latest \
		pytest tests/ --cov=src --cov-report=xml --cov-report=term

# コードカバレッジレポート生成
coverage:
	docker run --rm \
		-v $(ROOTDIR)/coverage:/app/coverage \
		$(IMAGE_NAME):latest \
		coverage report
```

**dockerfiles/prod/Makefile (本番環境固有)**:
```makefile
include ../Makefile.common

IMAGE_NAME := $(APP_NAME)-prod
CONTAINER_NAME := $(APP_NAME)-prod-container
BUILD_TARGET := prod
AWS_ACCOUNT := 822754592070
AWS_REGION := ap-northeast-1

# 本番コンテナ起動（読み取り専用ファイルシステム）
run: create_network
	docker run -d \
		--name $(CONTAINER_NAME) \
		--network $(NETWORK) \
		--read-only \
		--tmpfs /tmp \
		--env-file $(ROOTDIR)/.env.prod \
		--restart unless-stopped \
		-p 8080:8080 \
		$(IMAGE_NAME):latest

# ECRへのプッシュ
ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin \
		$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com

push: ecr-login
	docker tag $(IMAGE_NAME):$(TAG) \
		$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(APP_NAME):$(TAG)
	docker tag $(IMAGE_NAME):latest \
		$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(APP_NAME):latest
	docker push $(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(APP_NAME):$(TAG)
	docker push $(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(APP_NAME):latest
```

**Alternatives Considered**:
- **Docker Composeのみ**: 拒否理由 - 複雑なビルド依存関係や条件分岐の表現が困難
- **シェルスクリプト**: 拒否理由 - 依存関係管理が不明確で、メンテナンス性が低い
- **タスクランナー（Just、Task等）**: 拒否理由 - Makeは広く普及し、学習コスト不要
- **npmスクリプト**: 拒除理由 - Node.js環境必須で、Python中心プロジェクトに不適

**Key Benefits for 2025**:
- **一貫性**: すべての環境で同じコマンドセットを使用
- **移植性**: 新しい開発者が直感的に操作可能
- **CI/CD統合**: GitLab CI、GitHub Actions等で`make test`等を直接実行
- **ドキュメント価値**: Makefile自体が実行可能な使用ガイド

---

### 5. パフォーマンス最適化

#### Decision: BuildKit + キャッシュマウント + レイヤー最適化戦略

**Rationale**:
- **BuildKitによる並列ビルド**: 独立したステージを並列実行し、ビルド時間を大幅短縮
- **レジストリベースキャッシュ**: CI/CD環境間でキャッシュを共有し、初回ビルドも高速化
- **依存関係レイヤー分離**: 頻繁に変更されるコードと静的な依存関係を分離しキャッシュヒット率向上
- **ZStandard圧縮**: Docker Desktop 4.19+で利用可能な高速圧縮でイメージ転送を高速化
- **マルチステージビルド**: 50%のイメージサイズ削減により、プル・プッシュ時間を短縮

**Implementation Pattern**:

**1. BuildKit有効化とキャッシュマウント**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim AS base

# パフォーマンス最適化環境変数
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 依存関係レイヤー（頻繁に変更されない）
COPY pyproject.toml uv.lock README.md /app/
WORKDIR /app

# キャッシュマウント活用（BuildKit機能）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv sync --frozen --no-install-project

# アプリケーションコードレイヤー（頻繁に変更される）
COPY src/ /app/src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
```

**2. レイヤー順序最適化**:
```dockerfile
# ❌ 悪い例: すべてを一度にコピー
COPY . /app
RUN uv sync

# ✅ 良い例: 依存関係を先にインストール
COPY pyproject.toml uv.lock /app/
RUN uv sync --no-install-project
COPY src/ /app/src/
RUN uv sync
```

**3. 外部キャッシュ統合（CI/CD用）**:
```bash
# GitHub Actions / GitLab CI での使用例

# キャッシュ付きビルド
docker buildx build \
  --cache-from type=registry,ref=myregistry.com/mixseek-core:buildcache \
  --cache-to type=registry,ref=myregistry.com/mixseek-core:buildcache,mode=max \
  --target dev \
  -t mixseek-core:dev \
  .

# mode=max: すべての中間レイヤーをキャッシュとして保存
# mode=min: 最終イメージのレイヤーのみキャッシュ（デフォルト）
```

**4. マルチプラットフォームビルド最適化**:
```makefile
# Apple Siliconでx86_64イメージをビルド
xbuild:
	cd $(ROOTDIR) && \
	docker buildx build \
		--platform linux/amd64 \
		--cache-from type=registry,ref=$(IMAGE_NAME):buildcache \
		--cache-to type=registry,ref=$(IMAGE_NAME):buildcache,mode=max \
		-t $(IMAGE_NAME) \
		-f $(CURDIR)/Dockerfile \
		.
```

**5. イメージプリロードとウォームアップ**:
```bash
# CI/CDパイプライン起動時にベースイメージをプリロード
docker pull ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim

# 依存関係キャッシュをプリロード
docker pull myregistry.com/mixseek-core:buildcache
```

**6. 軽量ベースイメージ選択**:
```dockerfile
# イメージサイズ比較:
# python:3.13            -> 1.2GB
# python:3.13-slim       -> 180MB
# python:3.13-alpine     -> 50MB (互換性問題あり)
# uv:0.8.24-bookworm-slim -> 200MB (uv含む)

# 推奨: uv公式イメージ（最適化済み）
FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim
```

**Performance Metrics (Expected)**:
- **初回ビルド時間**: 5分以内（キャッシュなし）
- **再ビルド時間（コード変更のみ）**: 30秒以内（依存関係キャッシュヒット）
- **再ビルド時間（依存関係変更）**: 2分以内（uv高速解決）
- **イメージサイズ**:
  - 開発環境: 800MB-1.2GB（AI開発ツール含む）
  - CI環境: 400-600MB（テストツール含む）
  - 本番環境: 200-300MB（ランタイムのみ）

**Alternatives Considered**:
- **従来のdocker buildコマンド**: 拒否理由 - BuildKitの並列実行や高度なキャッシュ機能が利用不可
- **キャッシュなし戦略**: 拒否理由 - 毎回フルビルドで時間とコストが増大
- **ローカルキャッシュのみ**: 拒否理由 - CI/CD環境で初回ビルドが常に遅い
- **Docker Layer Caching (DLC)**: 検討済み - クラウドCI（GitLab、CircleCI）では有効だが、セルフホストでは外部キャッシュが優位

**BuildKit Key Features for 2025**:
- **並列依存関係解決**: 独立したビルドステップを自動的に並列実行
- **自動未使用ステージスキップ**: `--target`指定時に不要なステージをビルドしない
- **効率的なコンテキスト転送**: `.dockerignore`に基づいて最小限のファイルのみ転送
- **シークレット管理**: `--secret`フラグでビルド時シークレットを安全に注入（イメージに残らない）

**Monitoring and Profiling**:
```bash
# ビルド時間の詳細プロファイル
docker buildx build --progress=plain . 2>&1 | tee build.log

# レイヤーサイズ分析
docker history mixseek-core:dev --no-trunc

# 不要ファイル検出
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest mixseek-core:dev
```

---

## 追加調査項目

### 6. AI開発ツールの統合

#### Decision: Claude Code公式DevContainer方式の採用

**Rationale**:
- **Anthropic公式サポート**: Claude Codeの公式DevContainer実装が利用可能
- **セキュリティ分離**: コンテナ内実行により、ホスト環境とコードを完全分離
- **環境一貫性**: Claude Codeが開発環境と同じPython interpreter、パッケージ、環境変数を使用
- **チーム標準化**: 新メンバーが数分で完全に設定された開発環境を取得可能
- **CI/CD統合**: DevContainer設定をCI/CDパイプラインでも利用可能

**Implementation Pattern**:
```dockerfile
# Claude Code統合（開発環境専用）
FROM base AS dev

# ... 前述の開発環境セットアップ ...

# Claude Code用セキュリティ設定
RUN mkdir -p /home/${USERNAME}/.anthropic && \
    chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.anthropic

# Claude Code実行スクリプト
COPY --chown=${USERNAME}:${USERNAME} scripts/claude-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/claude-entrypoint.sh

# Claude Code用環境変数
ENV CLAUDE_CODE_WORKSPACE=/app
ENV CLAUDE_CODE_CONFIG=/home/${USERNAME}/.anthropic/config.json

# 開発コンテナ起動コマンド
CMD ["sleep", "infinity"]
```

**Security Considerations**:
- ホストとの分離により、Claude Codeの実行がホストシステムに影響を与えない
- ファイアウォール設定で外部通信を制限（npm registry、GitHub、Claude API等のみ許可）
- `--dangerously-skip-permissions`フラグは信頼されたコンテナ環境でのみ使用

---

### 7. ユーザー権限管理

#### Decision: 非rootユーザー実行 + UID/GID同期方式

**Rationale**:
- **セキュリティベストプラクティス**: OWASP Docker Security Sheets、CIS Docker Benchmarkで推奨
- **コンテナエスケープ対策**: 攻撃者がコンテナを脱出してもホストroot権限を取得不可
- **ファイル所有権問題解決**: ホストとコンテナのUID/GIDを同期し、ボリュームマウント時の権限問題を回避
- **本番環境セキュリティ**: read-onlyファイルシステムと組み合わせて攻撃面を最小化
- **User Namespaces対応**: Docker 1.10+のUser Namespace機能と互換性あり

**Implementation Pattern**:
```dockerfile
# ビルド時引数でホストのUID/GIDを受け取る
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000

# グループとユーザーを明示的なID指定で作成
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

# アプリケーションディレクトリの所有権設定
RUN mkdir -p /app /venv && \
    chown -R ${USERNAME}:${USERNAME} /app /venv

# 非rootユーザーに切り替え
USER ${USERNAME}

# 以降のすべてのコマンドは非rootで実行
WORKDIR /app
```

**Makefile統合**:
```makefile
# ホスト環境のUID/GIDを自動取得してビルド
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)
HOST_USERNAME := $(shell whoami)

build:
	docker build \
		--build-arg USERNAME=$(HOST_USERNAME) \
		--build-arg UID=$(HOST_UID) \
		--build-arg GID=$(HOST_GID) \
		-t $(IMAGE_NAME) \
		.
```

**本番環境追加セキュリティ**:
```dockerfile
# 本番環境: read-onlyファイルシステム
FROM base AS prod
USER appuser
COPY --chown=appuser:appuser --from=builder /venv /venv
COPY --chown=appuser:appuser src/ /app/src/

# read-only実行（一時ファイルは/tmpのみ）
CMD ["python", "-m", "src.main"]

# docker runでのread-only強制
# docker run --read-only --tmpfs /tmp mixseek-core:prod
```

**Alternatives Considered**:
- **rootユーザー実行**: 拒否理由 - セキュリティリスク、業界標準違反
- **実行時ユーザー指定（-u flag）**: 拒否理由 - Dockerfileに記載されず、実行方法に依存
- **User Namespaces単独**: 検討中 - Docker Daemon設定が必要で、ホスト環境への依存が増加
- **Rootlessモード**: 将来検討 - Docker Daemon自体を非root実行するが、現時点では機能制限あり

**File System Permission Handling**:
```dockerfile
# ユーザー切り替え後のファイル権限調整
USER ${USERNAME}

# 一般ユーザーが書き込み可能なディレクトリ
RUN mkdir -p /app/logs /app/tmp && \
    chmod 755 /app/logs /app/tmp

# 設定ファイルは読み取り専用
COPY --chown=${USERNAME}:${USERNAME} --chmod=444 config/ /app/config/

# 実行ファイルは実行権限付与
COPY --chown=${USERNAME}:${USERNAME} --chmod=555 scripts/ /app/scripts/
```

---

## 実装依存関係

### Required Tools and Versions
```toml
[dependencies]
# Python
python = ">=3.13.9"
uv = ">=0.8.15"

# Node.js (開発環境のみ)
node = "22.20.0"
npm = ">=10.0.0"
nvm = "0.40.3"

# Docker
docker = ">=24.0.0"
docker-buildx = ">=0.11.0"
docker-compose = ">=2.20.0"

# AI Development Tools (開発環境のみ)
@anthropic-ai/claude-code = "latest"
# Additional AI tools TBD (Codex, Gemini CLI)
```

### Base Images
- **開発環境**: `ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim` + Node.js 22.20.0
- **CI環境**: `ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim`
- **本番環境**: `ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim`

---

## リスク軽減策

### 高リスク項目

#### 1. マルチ言語環境の複雑性
- **リスク**: Node.js + Python統合により依存関係の衝突や予期しない動作
- **軽減策**:
  - マルチステージビルドで環境を明確に分離
  - CI環境でNode.jsを除外し、必要最小限の構成を維持
  - 統合テストで両言語の連携動作を検証

#### 2. コンテナビルド時間の増加
- **リスク**: AI開発ツールのインストールによりビルド時間が5分を超過
- **軽減策**:
  - BuildKitキャッシュマウントで依存関係ダウンロードを最小化
  - レジストリベースキャッシュでCI/CD間で共有
  - 開発環境ビルドは夜間バッチで事前実行

#### 3. UID/GID同期の失敗
- **リスク**: 異なるホスト環境でUID/GIDが一致せず、ファイル所有権問題
- **軽減策**:
  - Makefile自動取得により明示的な指定を不要化
  - ドキュメントで手動指定方法を明記
  - チーム内でUID/GID範囲を標準化（1000-1999推奨）

#### 4. 機密情報の誤コミット
- **リスク**: 開発者が実際の.envファイルを誤ってgitにコミット
- **軽減策**:
  - .gitignoreで`.env`、`.env.*`を確実に除外（`!.env.*.template`で例外）
  - pre-commitフックで機密情報スキャン
  - テンプレートファイルのみバージョン管理

#### 5. AI開発ツールのライセンスとコスト
- **リスク**: Claude Code、Codex等のAPI使用料が予算を超過
- **軽減策**:
  - 開発環境でのみインストールし、CI/本番環境では除外
  - API使用量モニタリングとアラート設定
  - ローカルLLMオプションの検討（Ollama等）

---

## 次のステップ

### Phase 1: デザインと契約定義
1. **データモデル設計**: 環境設定スキーマ、コンテナイメージメタデータ定義
2. **契約定義**: Dockerfile、Makefile、docker-compose.ymlの標準インターフェース
3. **クイックスタートガイド**: 10分以内のセットアップ手順書

### Phase 2: 実装
1. **マルチステージDockerfile作成**: 開発、CI、本番環境の3ステージ
2. **Makefile統合**: 共通Makefile + 環境別Makefile実装
3. **環境変数テンプレート**: .env.*.template作成とドキュメント化
4. **CI/CD統合**: GitHub Actions/GitLab CIでのビルドキャッシュ設定

### Phase 3: テストと検証
1. **Dockerビルドテスト**: 各環境のビルド成功を自動検証
2. **ワークフロー統合テスト**: make build、make run、make testの動作確認
3. **AI開発ツールテスト**: Claude Code等のコンテナ内動作検証
4. **クロスプラットフォームテスト**: Linux、macOS、Windows Dockerでの検証

**GATE結果**: ✅ Phase 0研究完了 - Phase 1デザインに進行可能
