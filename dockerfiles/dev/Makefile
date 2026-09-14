# =============================================================================
# MixSeek-Core Development Environment Makefile
# =============================================================================
# This Makefile provides development-specific commands and workflows for the
# MixSeek-Core project. It extends the common Makefile with development tools,
# debugging support, and AI development tool integration.

# Include common definitions and targets
include ../Makefile.common

# =============================================================================
# DEVELOPMENT ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment identification
IMAGE_NAME := $(APP_NAME)/dev:latest
CONTAINER_NAME := $(APP_NAME)-dev
REPO := $(IMAGE_NAME)
ENV := dev

# Build arguments (inherit MIXSEEK_* variables from Makefile.common)
BUILD_ARGS := \
    --build-arg MIXSEEK_USERNAME=$(MIXSEEK_USERNAME) \
    --build-arg MIXSEEK_UID=$(MIXSEEK_UID) \
    --build-arg MIXSEEK_GID=$(MIXSEEK_GID) \
    --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

# Base Docker runtime options
BASE_DOCKER_OPTS := \
    --name $(CONTAINER_NAME) \
    --hostname $(CONTAINER_NAME) \
    -e TERM=xterm-256color

# Development-specific options
DEV_DOCKER_OPTS := \
    -v $(ROOTDIR):/app \
    -v $(ROOTDIR)/.cache:/home/$(MIXSEEK_USERNAME)/.cache \
    -v $(ROOTDIR)/.config:/home/$(MIXSEEK_USERNAME)/.config \
    --env-file=$(ROOTDIR)/.env.dev

# Combined runtime options
DOCKER_OPTS := $(BASE_DOCKER_OPTS) $(DEV_DOCKER_OPTS)

# Test-specific options
DOCKER_TEST_OPTS := \
    -v $(ROOTDIR)/tests:/app/tests \
    --env-file=$(ROOTDIR)/.env.test

# Debug-specific options
DEBUG_OPTS := \
    -p 5678:5678 \
    -e DEBUGPY_ENABLED=true

# Streamlit-specific options
STREAMLIT_OPTS := \
    -p 8501:8501

# =============================================================================
# CORE CONTAINER LIFECYCLE
# =============================================================================

.PHONY: run
run:
	@echo "🚀 Starting development container: $(CONTAINER_NAME)"
	$(call check_env_file,$(ENV))
	@# ホスト側のディレクトリを事前作成（Dockerがroot所有で作成するのを防ぐ）
	@mkdir -p $(ROOTDIR)/.cache $(ROOTDIR)/.config
	@# もしroot所有の場合は修正
	@if [ "$$(stat -c '%U' $(ROOTDIR)/.cache 2>/dev/null)" = "root" ]; then \
		echo "⚠️  Fixing .cache directory ownership..."; \
		sudo chown -R $(MIXSEEK_USERNAME):$(MIXSEEK_USERNAME) $(ROOTDIR)/.cache; \
	fi
	@if [ "$$(stat -c '%U' $(ROOTDIR)/.config 2>/dev/null)" = "root" ]; then \
		echo "⚠️  Fixing .config directory ownership..."; \
		sudo chown -R $(MIXSEEK_USERNAME):$(MIXSEEK_USERNAME) $(ROOTDIR)/.config; \
	fi
	@docker run $(DOCKER_OPTS) $(STREAMLIT_OPTS) -d $(IMAGE_NAME)
	@echo "✅ Development container started"
	@echo "💡 Connect with: make bash"
	@echo "💡 Start Streamlit UI: make streamlit"
	@echo "🔗 Container name: $(CONTAINER_NAME)"
	@echo "🔗 Exposed ports: 5678 (debug), 8501 (streamlit)"

.PHONY: stop
stop:
	@echo "⏹️  Stopping development container: $(CONTAINER_NAME)"
	@docker stop $(CONTAINER_NAME) 2>/dev/null || echo "ℹ️  Container $(CONTAINER_NAME) not running"

.PHONY: restart
restart: stop rm run
	@echo "✅ Development container restarted"

# =============================================================================
# DEVELOPMENT WORKFLOW COMMANDS
# =============================================================================

.PHONY: lint
lint:
	@echo "🔍 Running code linting with ruff"
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) bash -c "cd /app && ruff check ."

.PHONY: format
format:
	@echo "✨ Formatting code with ruff"
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) bash -c "cd /app && ruff format ."

.PHONY: check
check: lint
	@echo "🔍 Running type checking with mypy"
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) bash -c "cd /app && mypy . --ignore-missing-imports || echo '⚠️  mypy not configured or errors found'"

.PHONY: fix
fix:
	@echo "🔧 Auto-fixing linting issues"
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) bash -c "cd /app && ruff check --fix ."

# =============================================================================
# TESTING COMMANDS
# =============================================================================

.PHONY: unittest
unittest:
	@echo "🧪 Running unit tests with pytest"
	$(call check_env_file,$(ENV))
	@docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) \
		bash -c "cd /app && pytest --log-cli-level=INFO tests/"

.PHONY: only-test
only-test:
	@echo "🧪 Running specific test: $(ARG)"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make only-test ARG=tests/test_example.py"; \
		exit 1; \
	fi
	$(call check_env_file,$(ENV))
	@docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) \
		bash -c "cd /app && pytest -s -vv --log-cli-level=INFO $(ARG)"

.PHONY: test-watch
test-watch:
	@echo "🔄 Running tests in watch mode"
	$(call check_env_file,$(ENV))
	@docker run --rm $(DOCKER_OPTS) $(DOCKER_TEST_OPTS) $(IMAGE_NAME) \
		bash -c "cd /app && pytest-watch -- --log-cli-level=INFO tests/"

# =============================================================================
# DEBUGGING SUPPORT
# =============================================================================

.PHONY: debug
debug:
	@echo "🐛 Starting debug session"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make debug ARG=path/to/script.py"; \
		exit 1; \
	fi
	$(call check_env_file,$(ENV))
	@echo "🔗 Debug server will listen on localhost:5678"
	@echo "💡 Configure your IDE to connect to localhost:5678"
	@docker run --rm $(DOCKER_OPTS) $(DEBUG_OPTS) $(IMAGE_NAME) \
		python -m debugpy --listen 0.0.0.0:5678 --wait-for-client $(ARG)

.PHONY: debug-server
debug-server:
	@echo "🐛 Starting debug server (no script execution)"
	$(call check_env_file,$(ENV))
	@echo "🔗 Debug server listening on localhost:5678"
	@docker run --rm $(DOCKER_OPTS) $(DEBUG_OPTS) $(IMAGE_NAME) \
		python -m debugpy --listen 0.0.0.0:5678 --wait-for-client

# =============================================================================
# AI DEVELOPMENT TOOLS INTEGRATION
# =============================================================================

.PHONY: claude-code
claude-code:
	@echo "🤖 Running Claude Code"
	@if [ -z "$(ARG)" ]; then \
		echo "💡 Usage: make claude-code ARG='--help'"; \
		echo "💡 Example: make claude-code ARG='analyze src/main.py'"; \
	fi
	@docker exec -it $(CONTAINER_NAME) claude $(ARG)

.PHONY: codex
codex:
	@echo "🤖 Running OpenAI Codex"
	@if [ -z "$(ARG)" ]; then \
		echo "💡 Usage: make codex ARG='--help'"; \
		echo "💡 Example: make codex ARG='generate function to parse JSON'"; \
	fi
	@docker exec -it $(CONTAINER_NAME) codex $(ARG)

.PHONY: gemini
gemini:
	@echo "🤖 Running Gemini CLI"
	@if [ -z "$(ARG)" ]; then \
		echo "💡 Usage: make gemini ARG='--help'"; \
		echo "💡 Example: make gemini ARG='code-review src/main.py'"; \
	fi
	@docker exec -it $(CONTAINER_NAME) gemini $(ARG)

# =============================================================================
# CONTAINER MANAGEMENT
# =============================================================================

.PHONY: exec
exec:
	@echo "⚡ Executing command in container: $(ARG)"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make exec ARG='command to execute'"; \
		exit 1; \
	fi
	@docker exec -it $(CONTAINER_NAME) bash -c "cd /app && $(ARG)"

.PHONY: root
root:
	@echo "🔐 Connecting as root user (for system administration)"
	@docker exec -it --user root $(CONTAINER_NAME) bash

.PHONY: ps
ps:
	@echo "📋 Container processes"
	@docker exec $(CONTAINER_NAME) ps aux

.PHONY: top
top:
	@echo "📈 Container resource usage"
	@docker exec -it $(CONTAINER_NAME) top

# =============================================================================
# DEVELOPMENT UTILITIES
# =============================================================================

.PHONY: install
install:
	@echo "📦 Installing additional Python package: $(ARG)"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make install ARG='package-name'"; \
		exit 1; \
	fi
	@docker exec -it $(CONTAINER_NAME) bash -c "cd /app && uv add $(ARG)"

.PHONY: pip-list
pip-list:
	@echo "📋 Installed Python packages"
	@docker exec $(CONTAINER_NAME) bash -c "cd /app && uv pip list"

.PHONY: node-list
node-list:
	@echo "📋 Installed Node.js packages"
	@docker exec $(CONTAINER_NAME) npm list -g --depth=0

.PHONY: env-info
env-info:
	@echo "ℹ️  Development environment information"
	@docker exec $(CONTAINER_NAME) bash -c " \
		echo \"🐍 Python: $$(python --version)\" && \
		echo \"📦 uv: $$(uv --version)\" && \
		echo \"🟢 Node.js: $$(node --version)\" && \
		echo \"📦 npm: $$(npm --version)\" && \
		echo \"🤖 Claude Code: $$(claude --version 2>/dev/null || echo not available)\" && \
		echo \"🤖 Codex: $$(codex --version 2>/dev/null || echo not available)\" && \
		echo \"🤖 Gemini CLI: $$(gemini --version 2>/dev/null || echo not available)\" && \
		echo \"🐙 GitHub CLI: $$({ gh --version 2>/dev/null || echo not available; } | head -1)\" \
	"

# =============================================================================
# HOT RELOAD AND FILE WATCHING
# =============================================================================

.PHONY: watch
watch:
	@echo "👀 Starting file watcher for hot reload"
	@docker exec -it $(CONTAINER_NAME) bash -c " \
		if command -v watchmedo >/dev/null 2>&1; then \
			watchmedo auto-restart --directory=/app --pattern='*.py' --recursive -- python /app/main.py; \
		else \
			echo '⚠️  watchdog not installed. Install with: make install ARG=watchdog'; \
		fi"

# =============================================================================
# DEVELOPMENT SERVER SHORTCUTS
# =============================================================================

.PHONY: server
server:
	@echo "🌐 Starting development server"
	@docker exec -it $(CONTAINER_NAME) bash -c "cd /app && python -m http.server 8000"

.PHONY: streamlit
streamlit:
	@echo "🎨 Starting Streamlit UI (Feature 076-ui)"
	@if [ -z "$$MIXSEEK_WORKSPACE" ]; then \
		echo "❌ MIXSEEK_WORKSPACE environment variable not set"; \
		echo "💡 Example: export MIXSEEK_WORKSPACE=/path/to/workspace"; \
		exit 1; \
	fi
	@echo "🔗 Streamlit will be available at http://localhost:8501"
	@echo "💡 Make sure container was started with: docker run -p 8501:8501 ..."
	@docker exec -it $(CONTAINER_NAME) bash -c "cd /app && uv run mixseek ui --server.address 0.0.0.0"

.PHONY: jupyter
jupyter:
	@echo "📓 Starting Jupyter notebook server"
	@docker exec -it $(CONTAINER_NAME) bash -c " \
		if command -v jupyter >/dev/null 2>&1; then \
			jupyter notebook --ip=0.0.0.0 --port=8888 --allow-root --no-browser; \
		else \
			echo '⚠️  Jupyter not installed. Install with: make install ARG=jupyter'; \
		fi"

# =============================================================================
# HELP AND STATUS
# =============================================================================

.PHONY: status
status:
	@echo "📊 Development environment status"
	@echo "Container: $(CONTAINER_NAME)"
	@if docker ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q $(CONTAINER_NAME); then \
		echo "✅ Status: Running"; \
		docker ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
	else \
		echo "❌ Status: Not running"; \
	fi
	@echo ""
	@echo "Image: $(IMAGE_NAME)"
	@if docker images --filter "reference=$(IMAGE_NAME)" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | tail -n +2 | head -1 | grep -q .; then \
		echo "✅ Image: Available"; \
		docker images --filter "reference=$(IMAGE_NAME)" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"; \
	else \
		echo "❌ Image: Not built"; \
		echo "💡 Build with: make build"; \
	fi

.PHONY: dev-help
dev-help:
	@echo "🚀 MixSeek-Core Development Environment Commands"
	@echo ""
	@echo "🏗️  Build & Run:"
	@echo "  build              Build development image"
	@echo "  run                Start development container"
	@echo "  stop               Stop development container"
	@echo "  restart            Restart development container"
	@echo "  status             Show container and image status"
	@echo ""
	@echo "🐚 Shell Access:"
	@echo "  bash               Connect to container bash shell"
	@echo "  root               Connect as root user"
	@echo "  exec ARG='cmd'     Execute custom command"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  unittest           Run all tests"
	@echo "  only-test ARG=path Run specific test file"
	@echo "  test-watch         Run tests in watch mode"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint               Run code linting (ruff)"
	@echo "  format             Format code (ruff)"
	@echo "  check              Type checking (mypy)"
	@echo "  fix                Auto-fix linting issues"
	@echo ""
	@echo "🐛 Debugging:"
	@echo "  debug ARG=script   Start debug session"
	@echo "  debug-server       Start debug server only"
	@echo ""
	@echo "🤖 AI Development Tools:"
	@echo "  claude-code ARG=   Use Claude Code AI assistant"
	@echo "  codex ARG=         Use OpenAI Codex"
	@echo "  gemini ARG=        Use Google Gemini CLI"
	@echo ""
	@echo "📦 Package Management:"
	@echo "  install ARG=pkg    Install Python package"
	@echo "  pip-list           List Python packages"
	@echo "  node-list          List Node.js packages"
	@echo ""
	@echo "🔧 Development Utilities:"
	@echo "  watch              Start file watcher"
	@echo "  server             Start development HTTP server"
	@echo "  streamlit          Start Streamlit UI server (076-ui)"
	@echo "  jupyter            Start Jupyter notebook"
	@echo "  env-info           Show environment information"
	@echo ""
	@echo "📖 Examples:"
	@echo "  make build && make run"
	@echo "  make bash"
	@echo "  make unittest"
	@echo "  make claude-code ARG='--help'"
	@echo "  make debug ARG='src/main.py'"

# Default target shows help
help: dev-help

# =============================================================================
# VALIDATION TARGETS
# =============================================================================

.PHONY: validate
validate:
	@echo "🔍 Validating development environment setup"
	@echo "Checking Docker daemon..."
	$(call check_docker)
	@echo "Checking environment file..."
	$(call check_env_file,$(ENV))
	@echo "Checking build arguments..."
	$(call validate_build_args)
	@echo "✅ Environment validation completed"