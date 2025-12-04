# dockerfiles仕様書

## 概要

dockerfilesディレクトリは、mixseek-coreプロジェクトのDocker開発環境を定義します。現在は開発環境（dev）のみが定義されており、将来的に本番環境やCI環境の追加が想定されています。

### 設計目標

- **再現性**: uvとDockerによる完全に再現可能な開発環境
- **パフォーマンス**: uvのコンパイル済みバイトコードとコピーモードによる高速化
- **権限管理**: ホストとコンテナのUID/GID同期による権限問題の回避
- **開発効率**: ボリュームマウントによるホットリロード対応

## ディレクトリ構造

```text
dockerfiles/
├── Makefile.common      # 全環境共通のMakeタスク定義
└── dev/
    ├── Dockerfile       # 開発環境用Dockerイメージ定義
    └── Makefile         # 開発環境固有のMakeタスク定義
```

将来的には以下の環境追加が想定されます：

```text
dockerfiles/
├── Makefile.common
├── dev/               # 開発環境
├── prod/              # 本番環境（想定）
└── ci/                # CI/CD環境（想定）
```

## Makefile.common仕様

全環境で共通的に使用されるMakeタスクを定義します。

### 定義済み変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `APP_NAME` | アプリケーション名 | `mixseek-core` |
| `NETWORK` | Dockerネットワーク名 | `$(APP_NAME)-network` |
| `TAG` | イメージタグ（Gitログから自動生成） | `$(git log -1 --date=short --format="%ad-%h")` |
| `ROOTDIR` | プロジェクトルートディレクトリ | 自動検出 |
| `HOST_USERNAME` | ホストのユーザー名 | `$(shell whoami)` |
| `HOST_UID` | ホストのユーザーID | `$(shell id -u)` |
| `HOST_GID` | ホストのグループID | `$(shell id -g)` |

**ホスト環境情報（HOST_*）について**:

これらの変数は、dev環境やci環境（将来）でコンテナ内ユーザーをホストのUID/GIDに同期するために使用されます。これにより、ボリュームマウントしたファイルの権限問題を回避できます。

本番環境では通常、固定ユーザー（例: `appuser:1000:1000`）を使用するため、これらの変数を使用せず独自の値を`BUILD_ARGS`で設定します。

### 共通タスク

#### create_network

Dockerネットワークを作成します（冪等性あり）。

```bash
make create_network
```

#### build

Dockerイメージをビルドします（キャッシュなし）。

```bash
make build
```

- プロジェクトルートをビルドコンテキストとして使用
- `$(CURDIR)/Dockerfile`を指定
- `--no-cache`オプションでクリーンビルド

#### xbuild

クロスプラットフォームビルド（linux/amd64）を実行します。

```bash
make xbuild
```

#### bash / sh

実行中のコンテナにシェル接続します。

```bash
make bash  # bashシェル
make sh    # shシェル
```

#### rm

コンテナを強制削除します（エラー無視）。

```bash
make rm
```

#### logs

コンテナログを表示します（最新30行をフォロー）。

```bash
make logs
```

## dev環境仕様

### dev/Makefile

開発環境固有のタスクとオプションを定義します。

#### 環境固有変数

| 変数名 | 説明 | 値 |
|--------|------|-----|
| `IMAGE_NAME` | イメージ名 | `$(APP_NAME)/dev:latest` |
| `CONTAINER_NAME` | コンテナ名 | `$(APP_NAME)-dev` |
| `REPO` | リポジトリ名 | `$(IMAGE_NAME)` |

**注**: `HOST_USERNAME`, `HOST_UID`, `HOST_GID`は`Makefile.common`で定義されており、dev環境で継承して使用します。

#### ビルド引数

ホストのユーザー情報（`Makefile.common`で定義）をビルド引数として渡し、コンテナ内で同一のUID/GIDを使用します。

```makefile
BUILD_ARGS := \
    --build-arg USERNAME=$(HOST_USERNAME) \
    --build-arg UID=$(HOST_UID) \
    --build-arg GID=$(HOST_GID)
```

#### Dockerオプション

**実行時オプション** (`DOCKER_OPTS`):

```makefile
DOCKER_OPTS=\
    -v $(CURDIR)/../../:/app\
    --env-file=$(CURDIR)/../../.env.dev
```

- プロジェクトルートを`/app`にマウント
- `.env.dev`から環境変数を読み込み

**テスト時追加オプション** (`DOCKER_TEST_OPTS`):

```makefile
DOCKER_TEST_OPTS=\
    -v $(CURDIR)/../../tests:/app/tests\
    --env-file=$(CURDIR)/../../.env.test
```

#### 開発タスク

**build**: Dockerイメージをビルド

```bash
make build
```

**run**: 開発コンテナを起動（デタッチドモード）

```bash
make run
```

**debug**: デバッガー待受モードで実行

```bash
make debug ARG=/path/to/script.py
```

- ポート5678でdebugpyが待受
- VSCodeなどからリモートデバッグ可能

**unittest**: 全テストを実行

```bash
make unittest
```

**only-test**: 特定のテストを実行

```bash
make only-test ARG=tests/agents/test_claude_agent_client.py
```

**only-codecheck**: コード品質チェック

```bash
make only-codecheck
```

```makefile
only-codecheck:
    docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) ruff check /app
```

## Dockerfile詳細仕様

### ベースイメージ

```dockerfile
FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim
```

- **uv**: 高速Pythonパッケージマネージャ（バージョン0.8.24）
- **Python**: 3.13.9
- **OS**: Debian Bookworm Slim

### パフォーマンス最適化

```dockerfile
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
```

- `UV_COMPILE_BYTECODE=1`: インストール時に.pycファイルを生成し、起動時間を短縮
- `UV_LINK_MODE=copy`: シンボリックリンクではなくコピーを使用（互換性向上）

### ビルド時引数

```dockerfile
ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000
```

デフォルト値は定義されていますが、通常はホストの値で上書きされます。

### システムパッケージ

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

**インストールパッケージ**:

- **curl**: nvmインストールスクリプトのダウンロードに必要
- **git**: バージョン管理
- **build-essential, cmake, pkg-config**: Pythonパッケージのネイティブ拡張ビルド用
- **libprotobuf-dev, protobuf-compiler**: Protocol Buffers対応（一部のパッケージで必要）

**Node.js/npmについて**: システムパッケージとしてインストールせず、nvmを使用して一般ユーザー権限でインストールします（後述）。

### ユーザー管理

```dockerfile
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}
```

ホストと同一のUID/GIDでユーザーを作成することで、以下の問題を回避：

- ボリュームマウントしたファイルの権限問題
- コンテナ内で作成したファイルがホストでroot所有になる問題

### ディレクトリ構成

```dockerfile
RUN mkdir -p /app /venv && chown -R ${USERNAME}:${USERNAME} /app /venv
```

- `/app`: アプリケーションコード（ボリュームマウント）
- `/venv`: Python仮想環境

### nvmとNode.jsのインストール

一般ユーザー権限でnvmを使用してNode.jsをインストールします。

```dockerfile
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
```

**設計のポイント**:

- **nvm v0.40.3**: バージョンを固定して再現性を確保
- **Node.js 22.20.0**: 具体的なバージョンを指定（`nvm install 22`だと最新版になり再現性が低い）
- **一般ユーザー権限**: root権限でのNode.jsインストールを回避
- **ENV NVM_DIR**: `$HOME`を使用してポータブルなパス指定
- **bash -c**: nvmコマンドを同一シェル内で実行するために必要

**従来の方法との違い**:

| 項目 | 従来（apt） | 現在（nvm） |
|------|------------|-------------|
| インストール方法 | `apt install nodejs npm` | nvmスクリプト経由 |
| 実行権限 | root | 一般ユーザー |
| バージョン管理 | システム固定 | nvm経由で柔軟 |
| Node.jsバージョン | Debian提供版 | 22.20.0（公式） |

### Python仮想環境

```dockerfile
ENV VIRTUAL_ENV=/venv
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PATH="/venv/bin:${PATH}"

WORKDIR /app
RUN uv venv /venv
```

- `/venv`に仮想環境を作成
- `UV_PROJECT_ENVIRONMENT`でuvの仮想環境パスを明示

### 依存関係インストール

```dockerfile
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock README.md /app/
RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen
```

- `--mount=type=cache`: ビルドキャッシュでインストール高速化
- `--frozen`: uv.lockを厳密に遵守（バージョン変動を防止）

**注意**: アプリケーションコードはコメントアウトされています。これは開発時にボリュームマウントを使用するためです。

### 環境変数

```dockerfile
ENV PYTHONPATH="/app"
```

- `/app`をPythonモジュール検索パスに追加

### エントリーポイント

```dockerfile
CMD ["sleep", "infinity"]
```

開発用コンテナとして、無限にスリープすることで起動状態を維持します。

## 環境変数と設定

### .env.dev

開発環境の設定を定義します。以下の主要カテゴリーに分類されます。

#### クラウドプロバイダー認証情報

**GCP**:

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_APPLICATION_CREDENTIALS=.cred/gcp_credentials.json
GOOGLE_CLOUD_PROJECT=stg-cpipe
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_SECRET=...
GEMINI_2_5_THINKING_BUDGET=0
```

**Snowflake**:

```bash
SNOWFLAKE_ACCOUNT=UCXDMYO-ALPACA_TECH
SNOWFLAKE_USER=DRILLER@ALPACA-TECH.AI
SNOWFLAKE_PRIVATE_KEY=...
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=...
SNOWFLAKE_ROLE=STG_DATA_READER
SNOWFLAKE_WAREHOUSE=DSEEK_WH
```

#### LLM API認証情報

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### システム設定

```bash
TZ=Asia/Tokyo
LOCAL=true
PYTHONDONTWRITEBYTECODE=1
LOG_LEVEL=DEBUG
ENABLE_LLM_LOG=1
LLM_LOG_OUTPUT_DIR=/logs
```

### セキュリティ上の重大な問題

**.env.devの機密情報漏洩リスク**:

1. `.gitignore`で`.env.dev`を無視するよう定義されている
2. しかし、実際には`.env.dev`ファイルがリポジトリに存在する可能性がある
3. Snowflake、各種API keyなどの機密情報が平文で含まれている

**推奨される対策**:

1. `.env.dev`をリポジトリから完全に削除（`git rm --cached .env.dev`）
2. `.env.dev.template`を作成し、サンプル値（または空値）で記述
3. 開発者は各自のローカル環境で`.env.dev.template`をコピーして`.env.dev`を作成
4. 環境変数管理ツール（Vault、SOPS等）の活用を検討

## ビルド・実行ワークフロー

### 初回セットアップ

```bash
# 1. Dockerイメージをビルド
cd dockerfiles/dev
make build

# 2. Dockerネットワークを作成
make create_network

# 3. 開発コンテナを起動
make run

# 4. コンテナに接続
make bash
```

### 開発ワークフロー

コンテナ起動後、以下のワークフローで開発を進めます。

**コンテナ内での作業**:

```bash
# コンテナに接続
make bash

# テスト実行
uv run pytest

# コード品質チェック
uv run ruff check .
uv run ruff format .

# アプリケーション実行
uv run python python/dseek/...
```

**ホストからの操作**:

```bash
# テスト実行（コンテナ外から）
make unittest

# 特定のテストを実行
make only-test ARG=tests/agents/test_claude_agent_client.py

# ログ確認
make logs

# コンテナ再起動
make rm
make run
```

### デバッグワークフロー

VSCodeなどでリモートデバッグを行う場合：

```bash
# デバッガー待受モードで起動
make debug ARG=/path/to/script.py
```

VSCodeの`.vscode/launch.json`設定例：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        }
    ]
}
```

## 既知の問題点と改善提案

### 実施済みの改善

以下の改善が既に実装されています：

#### ✅ nvmを使った一般ユーザーでのNode.jsインストール

**改善内容**:
- システムパッケージ（apt）でのnodejs/npmインストールを廃止
- nvmを使用した一般ユーザー権限でのNode.js 22.20.0インストール
- ARG USERNAMEをENVに変換し、ENV命令内で使用可能に

**メリット**:
- root権限でのNode.jsインストールが不要
- Node.jsのバージョン管理が容易
- より標準的で保守性の高い方法

#### ✅ ホスト環境変数の共通化

**改善内容**:
- `HOST_USERNAME`, `HOST_UID`, `HOST_GID`を`Makefile.common`に移動
- dev/MakefileからHOST_*変数の定義を削除（Makefile.commonから継承）
- `BUILD_ARGS`は各環境で定義（環境ごとのカスタマイズを可能に）

**メリット**:
- DRY原則: 変数定義の重複を削減
- 保守性向上: ホスト環境情報を一箇所で管理
- 柔軟性確保: 各環境でBUILD_ARGSを独自にカスタマイズ可能
- 将来のci/prod環境追加時の準備

### 重大な問題

| 問題 | 影響 | 優先度 | 対策 |
|------|------|--------|------|
| .env.devの機密情報漏洩 | セキュリティリスク | 最高 | リポジトリから削除し、.env.dev.templateを作成 |

### 中程度の問題

| 問題 | 影響 | 優先度 | 対策 |
|------|------|--------|------|
| .env.testファイルが存在しない | テストタスクの失敗 | 中 | .env.testを作成、または.env.devを使用 |
| toolsディレクトリが存在しない | log2html、ndjson2ipynbタスクの失敗 | 中 | toolsディレクトリと必要なスクリプトを実装、または該当タスクを削除 |

### 改善提案

#### 1. .env.test の作成

テストタスクを機能させるため、`.env.test`を作成：

```bash
# .env.devをベースに作成
cp .env.dev .env.test

# テスト専用の設定を追加
echo "LOG_LEVEL=DEBUG" >> .env.test
echo "ENABLE_LLM_LOG=0" >> .env.test
```

または、Makefileを修正して`.env.dev`を使用：

```makefile
DOCKER_TEST_OPTS=\
    -v $(CURDIR)/../../tests:/app/tests\
    --env-file=$(CURDIR)/../../.env.dev
```

## 将来の拡張計画

### 本番環境（prod）

```text
dockerfiles/prod/
├── Dockerfile          # マルチステージビルド、最小イメージ
└── Makefile           # デプロイ、ヘルスチェック等
```

**特徴**:

- マルチステージビルドで最小イメージサイズ
- 開発ツール（claude-code等）を含まない
- ヘルスチェックとメトリクス収集機能
- イミュータブルなイメージ（ボリュームマウント不使用）

### CI/CD環境（ci）

```text
dockerfiles/ci/
├── Dockerfile          # テスト実行環境
└── Makefile           # CI専用タスク
```

**特徴**:

- テストとリンター実行に最適化
- カバレッジレポート生成
- 並列テスト実行サポート
- アーティファクト生成とアップロード

### Docker Compose導入

複数コンテナの連携が必要になった場合、Docker Composeの導入を検討：

```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: dockerfiles/dev/Dockerfile
    volumes:
      - .:/app
    env_file:
      - .env.dev

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: mixseek_dev
      POSTGRES_USER: mixseek
      POSTGRES_PASSWORD: dev_password
```

## まとめ

dockerfilesディレクトリは、mixseek-coreプロジェクトの再現可能な開発環境を提供する重要なコンポーネントです。

### 実施済みの改善（2025年10月）

以下の改善が実装されました：

1. **nvmを使った一般ユーザーでのNode.jsインストール**: root権限でのnodejs/npmインストールを廃止し、nvmによる標準的な方法に移行
2. **ARG/ENV変数の適切な管理**: ENV命令内でビルド時引数を使用可能に
3. **ホスト環境変数の共通化**: HOST_USERNAME/UID/GIDをMakefile.commonに集約し、DRY原則を適用

### 残存する改善課題

**即座に対応すべき事項**:

1. .env.devの機密情報漏洩リスクへの対応

**段階的に改善すべき事項**:

1. 存在しないファイル・ディレクトリへの参照の削除または実装
2. 本番環境とCI環境の実装

これらの継続的な改善により、より堅牢で保守性の高いDocker環境が実現されます。
