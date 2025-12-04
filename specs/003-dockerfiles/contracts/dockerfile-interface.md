# Dockerfile Interface Contract

**Feature**: Docker開発環境テンプレート
**Created**: 2025-10-15
**Type**: Infrastructure Contract

## 概要

この契約は、各環境タイプのDockerfileが実装すべき標準インターフェースと構造を定義します。

## 環境共通インターフェース

### 必須ビルド引数

すべての環境のDockerfileは以下のビルド引数を受け入れなければならない：

```dockerfile
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000
```

**制約**:
- `USERNAME`: 英数字とアンダースコアのみ許可
- `UID`, `GID`: 1000-65534の範囲内
- デフォルト値は必須

### 必須環境変数

```dockerfile
# Python環境設定
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1

# 仮想環境設定
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:${PATH}"

# uv最適化設定
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/venv
```

### 必須ディレクトリ構造

```dockerfile
# アプリディレクトリと仮想環境ディレクトリを作成
RUN mkdir -p /app /venv && chown -R ${USERNAME}:${USERNAME} /app /venv

WORKDIR /app
```

### 必須ユーザー設定

```dockerfile
# ユーザー/グループ作成
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

# 非root権限に切り替え
USER ${USERNAME}
```

## 環境別実装要件

### 開発環境 (dev) Dockerfile

**ベースイメージ**: `ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim`

**必須システムパッケージ**:
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        git \
        build-essential \
        cmake \
        pkg-config \
        libprotobuf-dev \
        protobuf-compiler && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

**Node.js + AI開発ツール**:
```dockerfile
# nvm環境変数設定
ENV NVM_DIR=$HOME/.nvm
ENV NODE_VERSION=22.20.0

# nvmインストールとNode.jsセットアップ
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    bash -c ". $NVM_DIR/nvm.sh && nvm install $NODE_VERSION && nvm alias default $NODE_VERSION"

# PATH設定
ENV PATH=$NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# AI開発ツールインストール
RUN npm install -g @anthropic-ai/claude-code && \
    npm install -g @openai/codex && \
    npm install -g @google/gemini-cli
```

**Python環境設定**:
```dockerfile
# 仮想環境作成
RUN uv venv /venv

# 依存関係インストール
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen

# デバッグツール用ポート公開
EXPOSE 5678
```

**エントリーポイント**:
```dockerfile
CMD ["sleep", "infinity"]
```

---

### CI環境 (ci) Dockerfile

**ベースイメージ**: `ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim`

**軽量システムパッケージ**:
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

**CI特化Python環境**:
```dockerfile
# 仮想環境作成
RUN uv venv /venv

# 依存関係インストール（テストグループ含む）
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen --group test

# CI用追加ツール
RUN uv add pytest-cov pytest-xdist
```

**テスト実行エントリーポイント**:
```dockerfile
CMD ["pytest", "--cov", "--cov-report=xml", "--junit-xml=test-results.xml"]
```

**制約**:
- Node.js関連ツール一切含まない
- AI開発ツール含まない
- テストとコード品質ツールのみ

---

### 本番環境 (prod) Dockerfile

**マルチステージビルド必須**:

```dockerfile
# ビルドステージ
FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim AS builder

# 必要最小限のビルドツール
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python依存関係ビルド
COPY pyproject.toml uv.lock README.md /app/
WORKDIR /app
RUN uv venv /venv && \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 本番ステージ
FROM python:3.13-slim-bookworm AS runtime

# 必要最小限のランタイム依存関係のみ
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ビルドステージから仮想環境をコピー
COPY --from=builder /venv /venv

# 非root権限設定
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000

RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

# アプリケーションディレクトリ
RUN mkdir -p /app && chown -R ${USERNAME}:${USERNAME} /app
WORKDIR /app

USER ${USERNAME}

# 環境変数設定
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

**制約**:
- 開発ツール一切含まない
- Node.js含まない
- 最小イメージサイズ要求
- 読み取り専用ファイルシステム対応

## ラベル標準

すべてのDockerfileは以下のラベルを含む必要がある：

```dockerfile
LABEL org.opencontainers.image.title="MixSeek-Core ${ENVIRONMENT_TYPE} Environment"
LABEL org.opencontainers.image.description="Docker environment for MixSeek-Core development"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.source="https://github.com/your-org/mixseek-core"
LABEL mixseek.environment.type="${ENVIRONMENT_TYPE}"
LABEL mixseek.node.enabled="${NODE_ENABLED}"
LABEL mixseek.ai-tools.enabled="${AI_TOOLS_ENABLED}"
```

## セキュリティ要件

### 共通セキュリティ制約

```dockerfile
# 非root権限実行必須
USER ${USERNAME}

# 機密情報の除外
# APIキー、パスワード、トークンをDockerfile内にハードコード禁止
# 環境変数または Docker secrets 使用

# 不要な権限の削除
RUN find /usr/bin /usr/local/bin -perm /4000 -exec chmod -s {} + || true
```

### 環境固有セキュリティ

**開発環境**:
- デバッグポート公開許可
- AI開発ツールのネットワークアクセス許可

**本番環境**:
- 読み取り専用ファイルシステム
- 最小権限の原則
- ネットワークアクセス制限

## バリデーション

各Dockerfileは以下の条件を満たす必要がある：

### 構文バリデーション
```bash
# Dockerfile linting
docker run --rm -i hadolint/hadolint < Dockerfile

# 構造バリデーション
docker build --dry-run .
```

### セキュリティバリデーション
```bash
# 脆弱性スキャン
trivy image [IMAGE_NAME]

# セキュリティベンチマーク
docker-bench-security
```

### サイズバリデーション
```bash
# イメージサイズ制限
dev: < 1.2GB
ci: < 600MB
prod: < 300MB
```

## テストインターフェース

各Dockerfileは対応するテストを持つ必要がある：

```python
# tests/docker/test_[ENV]_dockerfile.py
def test_build_success():
    """Dockerfileが正常にビルドされる"""
    pass

def test_user_permissions():
    """非root権限で実行される"""
    pass

def test_required_tools():
    """必要なツールがインストールされている"""
    pass

def test_environment_variables():
    """環境変数が正しく設定されている"""
    pass
```

## 互換性マトリックス

| Feature | dev | ci | prod | Notes |
|---------|-----|----|----- |-------|
| Python 3.13+ | ✅ | ✅ | ✅ | 全環境必須 |
| uv package manager | ✅ | ✅ | ✅ | 全環境必須 |
| Node.js 22.20.0 | ✅ | ❌ | ❌ | 開発環境のみ |
| AI Development Tools | ✅ | ❌ | ❌ | 開発環境のみ |
| pytest + ruff | ✅ | ✅ | ❌ | テスト環境で使用 |
| Debug tools | ✅ | ❌ | ❌ | 開発環境のみ |
| Multi-stage build | ❌ | ❌ | ✅ | 本番環境のみ |

この契約に準拠することで、環境間の一貫性とセキュリティが保証され、開発者エクスペリエンスが向上します。