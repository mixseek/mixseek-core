# Makefile Interface Contract

**Feature**: Docker開発環境テンプレート
**Created**: 2025-10-15
**Type**: Infrastructure Contract

## 概要

この契約は、Makefileベースのワークフロー管理システムの標準インターフェースを定義します。全環境で一貫したコマンド体系を提供し、複雑なDockerオペレーションを抽象化します。

## 階層構造

```
dockerfiles/
├── Makefile.common          # 共通タスクとユーティリティ
├── dev/Makefile            # 開発環境固有のタスク
├── ci/Makefile             # CI環境固有のタスク
└── prod/Makefile           # 本番環境固有のタスク
```

## Makefile.common - 共通インターフェース

### 必須変数

```makefile
# アプリケーション識別
APP_NAME := mixseek-core
NETWORK := $(APP_NAME)-network
ROOTDIR := $(shell cd "$(dirname $(CURDIR))" &>/dev/null && cd ../../ && pwd -P)

# Gitベースタグ生成
TAG := $(shell git log -1 --date=short --format="%ad-%h")

# ホスト環境情報（UID/GID同期用）
HOST_USERNAME := $(shell whoami)
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)

# AWS設定（オプション）
AWS_ACCOUNT := $(or $(AWS_ACCOUNT_ID),)
AWS_REGION := $(or $(AWS_DEFAULT_REGION),ap-northeast-1)
```

### 必須ターゲット

#### Network Management

```makefile
.PHONY: create_network
create_network:
	@if docker network inspect ${NETWORK} >/dev/null 2>/dev/null ; then \
		echo "network ${NETWORK} exists"; \
	else \
		docker network create ${NETWORK}; \
	fi
```

**制約**:
- 冪等性保証 (複数回実行しても同じ結果)
- エラー出力抑制

#### Build Operations

```makefile
.PHONY: build
build:
	cd $(ROOTDIR) && \
	docker build --no-cache -t $(IMAGE_NAME) . -f $(CURDIR)/Dockerfile $(BUILD_ARGS)

.PHONY: xbuild
xbuild:
	cd $(ROOTDIR) && \
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME) . -f $(CURDIR)/Dockerfile $(BUILD_ARGS)
```

**制約**:
- `BUILD_ARGS`は各環境で定義
- ビルドコンテキストは必ずROOTDIR
- クリーンビルド (`--no-cache`) をデフォルトとする

#### Container Operations

```makefile
.PHONY: bash sh
bash:
	docker exec -it $(CONTAINER_NAME) bash

sh:
	docker exec -it $(CONTAINER_NAME) sh

.PHONY: rm
rm:
	-docker rm -f $(CONTAINER_NAME)

.PHONY: logs
logs:
	docker logs -f --tail 30 $(CONTAINER_NAME)
```

**制約**:
- `rm`ターゲットはエラーを無視 (`-` プレフィックス)
- インタラクティブモード (`-it`) 必須
- `CONTAINER_NAME`は環境固有で定義

#### Registry Operations (オプション)

```makefile
.PHONY: push pull
push: build
	docker tag $(IMAGE_NAME) $(REGISTRY)/$(REPO):$(TAG)
	docker tag $(IMAGE_NAME) $(REGISTRY)/$(REPO):latest
	docker push $(REGISTRY)/$(REPO):$(TAG)
	docker push $(REGISTRY)/$(REPO):latest

pull:
	docker pull $(REGISTRY)/$(REPO):latest
```

## 環境固有Makefile契約

### 共通include

すべての環境固有Makefileは共通定義をincludeする：

```makefile
include ../Makefile.common
```

### 必須変数定義

```makefile
# 環境固有の識別子
IMAGE_NAME := $(APP_NAME)/[ENV]:latest
CONTAINER_NAME := $(APP_NAME)-[ENV]
REPO := $(IMAGE_NAME)

# ビルド引数（HOST_*変数はMakefile.commonから継承）
BUILD_ARGS := \
    --build-arg USERNAME=$(HOST_USERNAME) \
    --build-arg UID=$(HOST_UID) \
    --build-arg GID=$(HOST_GID) \
    $(ADDITIONAL_BUILD_ARGS)

# Docker実行オプション
DOCKER_OPTS := \
    $(BASE_DOCKER_OPTS) \
    $(ENV_SPECIFIC_OPTS)
```

### 必須ターゲット

#### Runtime Operations

```makefile
.PHONY: run
run: create_network
	docker run $(DOCKER_OPTS) -d --name $(CONTAINER_NAME) $(IMAGE_NAME)

.PHONY: stop
stop:
	-docker stop $(CONTAINER_NAME)

.PHONY: restart
restart: stop rm run
```

**制約**:
- `run`は`create_network`に依存
- デタッチモード (`-d`) 必須
- `restart`は段階的実行

## 開発環境 (dev/Makefile) 仕様

### 環境固有設定

```makefile
include ../Makefile.common

# 開発環境識別子
IMAGE_NAME := $(APP_NAME)/dev:latest
CONTAINER_NAME := $(APP_NAME)-dev
REPO := $(IMAGE_NAME)

# ビルド引数
BUILD_ARGS := \
    --build-arg USERNAME=$(HOST_USERNAME) \
    --build-arg UID=$(HOST_UID) \
    --build-arg GID=$(HOST_GID)

# 実行時オプション
DOCKER_OPTS := \
    -v $(ROOTDIR):/app \
    --env-file=$(ROOTDIR)/.env.dev \
    --network $(NETWORK)

# テスト時追加オプション
DOCKER_TEST_OPTS := \
    -v $(ROOTDIR)/tests:/app/tests \
    --env-file=$(ROOTDIR)/.env.test
```

### 開発固有ターゲット

#### Debug Support

```makefile
.PHONY: debug
debug: create_network
	docker run $(DOCKER_OPTS) -p 5678:5678 --rm $(IMAGE_NAME) \
		python -m debugpy --listen 0.0.0.0:5678 --wait-for-client $(ARG)
```

**制約**:
- デバッグポート5678固定
- `--wait-for-client`で接続待機
- `ARG`変数でスクリプト指定

#### Testing

```makefile
.PHONY: unittest only-test
unittest: create_network
	docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) \
		pytest --log-cli-level=INFO /app/tests/

only-test: create_network
	docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) \
		pytest -s -vv --log-cli-level=INFO $(ARG)
```

#### Code Quality

```makefile
.PHONY: lint format check
lint:
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) ruff check /app

format:
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) ruff format /app

check: lint
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) mypy /app
```

#### AI Development Tools

```makefile
.PHONY: claude-code codex gemini
claude-code:
	docker exec -it $(CONTAINER_NAME) claude-code $(ARG)

codex:
	docker exec -it $(CONTAINER_NAME) codex $(ARG)

gemini:
	docker exec -it $(CONTAINER_NAME) gemini-cli $(ARG)
```

**制約**:
- 実行中のコンテナ必須 (`docker exec`)
- 引数は`ARG`変数経由

## CI環境 (ci/Makefile) 仕様

### 環境固有設定

```makefile
include ../Makefile.common

# CI環境識別子
IMAGE_NAME := $(APP_NAME)/ci:latest
CONTAINER_NAME := $(APP_NAME)-ci
REPO := $(IMAGE_NAME)

# ビルド引数（固定ユーザー）
BUILD_ARGS := \
    --build-arg USERNAME=ciuser \
    --build-arg UID=1001 \
    --build-arg GID=1001

# 実行時オプション（最小構成）
DOCKER_OPTS := \
    -v $(ROOTDIR):/app:ro \
    --env-file=$(ROOTDIR)/.env.ci \
    --network $(NETWORK)

# CI特化オプション
CI_OPTS := \
    --cap-drop=ALL \
    --read-only \
    --tmpfs /tmp:noexec,nosuid,size=1G
```

### CI固有ターゲット

#### Testing Pipeline

```makefile
.PHONY: test-full coverage security-scan
test-full: create_network
	docker run --rm $(DOCKER_OPTS) $(CI_OPTS) $(IMAGE_NAME) \
		pytest --cov --cov-report=xml --junit-xml=test-results.xml /app/tests/

coverage: test-full
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		coverage report --show-missing

security-scan:
	docker run --rm -v $(ROOTDIR):/app:ro \
		aquasec/trivy fs --security-checks vuln /app
```

#### Quality Gates

```makefile
.PHONY: quality-gate
quality-gate: lint coverage security-scan
	@echo "All quality gates passed"

.PHONY: pipeline
pipeline: build test-full quality-gate
	@echo "CI pipeline completed successfully"
```

## 本番環境 (prod/Makefile) 仕様

### 環境固有設定

```makefile
include ../Makefile.common

# 本番環境識別子
IMAGE_NAME := $(APP_NAME)/prod:$(TAG)
CONTAINER_NAME := $(APP_NAME)-prod
REPO := $(IMAGE_NAME)

# ビルド引数（固定ユーザー）
BUILD_ARGS := \
    --build-arg USERNAME=appuser \
    --build-arg UID=1000 \
    --build-arg GID=1000 \
    --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

# セキュアな実行オプション
DOCKER_OPTS := \
    --read-only \
    --tmpfs /tmp:noexec,nosuid,size=256M \
    --cap-drop=ALL \
    --cap-add=NET_BIND_SERVICE \
    --security-opt=no-new-privileges \
    --user 1000:1000 \
    --network $(NETWORK)

# ヘルスチェック
HEALTH_CHECK := \
    --health-cmd="python -c 'import sys; sys.exit(0)'" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3
```

### 本番固有ターゲット

#### Secure Deployment

```makefile
.PHONY: deploy health-check rollback
deploy: build
	docker run -d $(DOCKER_OPTS) $(HEALTH_CHECK) \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

health-check:
	@docker inspect --format='{{.State.Health.Status}}' $(CONTAINER_NAME)

rollback:
	docker stop $(CONTAINER_NAME)
	docker run -d $(DOCKER_OPTS) $(HEALTH_CHECK) \
		--name $(CONTAINER_NAME)-rollback \
		$(IMAGE_NAME):previous
```

#### Production Monitoring

```makefile
.PHONY: stats monitor backup
stats:
	docker stats $(CONTAINER_NAME)

monitor:
	docker logs -f --since=1h $(CONTAINER_NAME)

backup:
	docker export $(CONTAINER_NAME) > backup-$(TAG).tar
```

## エラーハンドリング標準

### 必須エラーチェック

```makefile
# Dockerデーモン稼働確認
check-docker:
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running" && exit 1)

# 必要な環境変数チェック
check-env:
	@test -n "$(APP_NAME)" || (echo "APP_NAME is not set" && exit 1)
	@test -f "$(ROOTDIR)/.env.$(ENV)" || (echo "Environment file not found" && exit 1)
```

### エラー処理パターン

```makefile
# 安全な停止
safe-stop:
	-docker stop --time=30 $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)

# 条件付きクリーンアップ
cleanup:
	docker ps -q --filter "name=$(CONTAINER_NAME)" | xargs -r docker stop
	docker ps -aq --filter "name=$(CONTAINER_NAME)" | xargs -r docker rm
	docker images -q --filter "reference=$(IMAGE_NAME)" | xargs -r docker rmi
```

## パフォーマンス最適化

### 並列実行サポート

```makefile
# 並列ビルド
.PHONY: build-parallel
build-parallel:
	$(MAKE) -j$(shell nproc) build-deps

build-deps: base-build python-deps node-deps

base-build:
	docker build --target base -t $(IMAGE_NAME):base .

python-deps:
	docker build --target python -t $(IMAGE_NAME):python .

node-deps:
	docker build --target node -t $(IMAGE_NAME):node .
```

### キャッシュ最適化

```makefile
# BuildKit cache
BUILDKIT_OPTS := \
    --cache-from type=registry,ref=$(REGISTRY)/cache:$(IMAGE_NAME) \
    --cache-to type=registry,ref=$(REGISTRY)/cache:$(IMAGE_NAME),mode=max

build-cached:
	DOCKER_BUILDKIT=1 docker build $(BUILDKIT_OPTS) -t $(IMAGE_NAME) .
```

## 検証とテスト

### Makefile文法検証

```bash
# 各Makefileの文法チェック
make -n -f Makefile.common
make -n -f dev/Makefile
make -n -f ci/Makefile
make -n -f prod/Makefile
```

### インターフェース整合性テスト

```python
def test_makefile_targets():
    """全環境で共通ターゲットが実装されているか確認"""
    required_targets = ['build', 'run', 'stop', 'rm', 'logs']
    for env in ['dev', 'ci', 'prod']:
        makefile_path = f"dockerfiles/{env}/Makefile"
        targets = extract_makefile_targets(makefile_path)
        for target in required_targets:
            assert target in targets, f"{env}/Makefile missing target: {target}"
```

この契約により、一貫したコマンドラインインターフェースと環境間のportabilityが保証されます。