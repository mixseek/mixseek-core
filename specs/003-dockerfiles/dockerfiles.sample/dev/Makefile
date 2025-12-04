include ../Makefile.common

IMAGE_NAME := $(APP_NAME)/dev:latest
CONTAINER_NAME := $(APP_NAME)-dev
REPO := $(IMAGE_NAME)

# ビルド引数（HOST_*変数はMakefile.commonで定義）
BUILD_ARGS := \
	--build-arg USERNAME=$(HOST_USERNAME) \
	--build-arg UID=$(HOST_UID) \
	--build-arg GID=$(HOST_GID)


DOCKER_OPTS=\
		-v $(CURDIR)/../../:/app\
		--env-file=$(CURDIR)/../../.env.dev

DOCKER_TEST_OPTS=\
		-v $(CURDIR)/../../tests:/app/tests\
		--env-file=$(CURDIR)/../../.env.test

# Makefile.commonのbuildをオーバーライド
build:
	cd $(ROOTDIR) && \
	docker build $(BUILD_ARGS) --no-cache -t $(IMAGE_NAME) . -f $(CURDIR)/Dockerfile

run:
	docker run $(DOCKER_OPTS) -it -d --name $(CONTAINER_NAME) $(REPO)


debug:
	docker run $(DOCKER_OPTS) -p 5678:5678 --rm $(IMAGE_NAME) \
		python -m debugpy --listen 0.0.0.0:5678 --wait-for-client $(ARG)


unittest:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) pytest --log-cli-level=INFO /app/tests/


only-test:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) pytest -s -vv --log-cli-level=INFO $(ARG)


only-codecheck:
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) flake8 /app


log2html:
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		python tools/html_converter/log2html.py $(ARG)

ndjson2ipynb:
	docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		python tools/html_converter/ndjson2ipynb.py $(ARG)
