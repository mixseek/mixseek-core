FROM ghcr.io/astral-sh/uv:0.8.24-python3.12-bookworm-slim

# パフォーマンス最適化環境変数
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# ビルド時引数（デフォルト値を設定）
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000

# ARGをENVに変換（ENV命令内で${USERNAME}を使用可能にする）
ENV USERNAME=${USERNAME}

# システムパッケージインストール（root）
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

# ユーザー/グループ作成
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}

# アプリディレクトリと仮想環境ディレクトリを作成して所有権設定
RUN mkdir -p /app /venv && chown -R ${USERNAME}:${USERNAME} /app /venv

# ユーザーに切り替え
USER ${USERNAME}

# nvm環境変数設定
ENV NVM_DIR=$HOME/.nvm
ENV NODE_VERSION=22.20.0

# nvmインストールとNode.jsセットアップ
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    bash -c ". $NVM_DIR/nvm.sh && nvm install $NODE_VERSION && nvm alias default $NODE_VERSION"

# PATH設定
ENV PATH=$NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# claude-codeをインストール
RUN npm install -g @anthropic-ai/claude-code

# Python仮想環境作成
ENV VIRTUAL_ENV=/venv
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PATH="/venv/bin:${PATH}"

WORKDIR /app
RUN uv venv /venv

# 依存関係インストール
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen

# アプリケーションコードをコピー
# 開発用なのでコメントアウト（必要に応じてアンコメント）
# COPY --chown=${USERNAME}:${USERNAME} python/ /app/
# COPY --chown=${USERNAME}:${USERNAME} tests/ /app/tests/

ENV PYTHONPATH="/app"

# Keep container running for development
CMD ["sleep", "infinity"]
