# =============================================================================
# MixSeek-Core CI Environment Makefile
# =============================================================================
# This Makefile provides CI-specific commands for testing, validation, and
# quality assurance. It is optimized for continuous integration environments
# with security hardening and minimal resource usage.

# Include common definitions and targets
include ../Makefile.common

# =============================================================================
# CI ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment identification
IMAGE_NAME := $(APP_NAME)/ci:latest
CONTAINER_NAME := $(APP_NAME)-ci
REPO := $(IMAGE_NAME)
ENV := ci

# Build arguments (inherit from Makefile.common for consistency with GitHub Actions)
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

# CI-specific security options (inherit UID/GID from Makefile.common)
CI_SECURITY_OPTS := \
    --cap-drop=ALL \
    --read-only \
    --tmpfs /tmp:noexec,nosuid,size=1G \
    --tmpfs /home/$(MIXSEEK_USERNAME)/.cache:noexec,nosuid,size=512M \
    --security-opt=no-new-privileges \
    --user $(MIXSEEK_UID):$(MIXSEEK_GID)

# CI runtime options
CI_DOCKER_OPTS := \
    -v $(ROOTDIR):/app:ro \
    --env-file=$(ROOTDIR)/.env.ci \
    -v $(ROOTDIR)/test-reports:/app/test-reports \
    -v $(ROOTDIR)/coverage-reports:/app/coverage-reports \
    -v $(ROOTDIR)/security-reports:/app/security-reports

# Combined runtime options
DOCKER_OPTS := $(BASE_DOCKER_OPTS) $(CI_DOCKER_OPTS) $(CI_SECURITY_OPTS)

# Simple one-off execution (no .env.ci required, matches root Makefile ci-check-docker)
# Note: Set GITHUB_ACTIONS=true to skip tests that behave differently in CI
# Note: --user ensures host UID/GID permissions are respected for mounted volumes
# Note: HOME=/tmp ensures cache directories work when running as arbitrary user
DOCKER_RUN_SIMPLE := docker run --rm -v $(ROOTDIR):/app -w /app \
    -e GITHUB_ACTIONS=true \
    -e HOME=/tmp \
    --user $(MIXSEEK_UID):$(MIXSEEK_GID)

# =============================================================================
# CORE CONTAINER LIFECYCLE (CI-Specific)
# =============================================================================

.PHONY: run
run:
	@echo "🔬 Starting CI container: $(CONTAINER_NAME)"
	$(call check_env_file,$(ENV))
	@mkdir -p $(ROOTDIR)/test-reports $(ROOTDIR)/coverage-reports $(ROOTDIR)/security-reports
	@docker run $(DOCKER_OPTS) -d $(IMAGE_NAME) sleep infinity
	@echo "✅ CI container started"
	@echo "💡 Run tests with: make test-full"
	@echo "🔗 Container name: $(CONTAINER_NAME)"

.PHONY: stop
stop:
	@echo "⏹️  Stopping CI container: $(CONTAINER_NAME)"
	@docker stop $(CONTAINER_NAME) 2>/dev/null || echo "ℹ️  Container $(CONTAINER_NAME) not running"

.PHONY: restart
restart: stop rm run
	@echo "✅ CI container restarted"

# =============================================================================
# TESTING PIPELINE
# =============================================================================

.PHONY: test-full
test-full:
	@echo "🧪 Running full test suite in CI environment"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run pytest --cov --cov-report=term-missing tests/
	@echo "✅ Test suite completed"

.PHONY: test-unit
test-unit:
	@echo "🧪 Running unit tests"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run pytest -m "unit" tests/

.PHONY: test-integration
test-integration:
	@echo "🧪 Running integration tests"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run pytest -m "integration" tests/

.PHONY: test-parallel
test-parallel:
	@echo "🧪 Running tests in parallel"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run pytest -n auto --cov tests/

.PHONY: test-fast
test-fast:
	@echo "🚀 Running fast tests only (excluding E2E)"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run pytest -m "not e2e" tests/

# =============================================================================
# CODE COVERAGE
# =============================================================================

.PHONY: coverage
coverage: test-full
	@echo "📊 Generating coverage report"
	@if [ -f "$(ROOTDIR)/coverage-reports/coverage.xml" ]; then \
		echo "✅ Coverage XML report: $(ROOTDIR)/coverage-reports/coverage.xml"; \
	fi
	@if [ -d "$(ROOTDIR)/coverage-reports/html" ]; then \
		echo "✅ Coverage HTML report: $(ROOTDIR)/coverage-reports/html/index.html"; \
	fi

.PHONY: coverage-report
coverage-report:
	@echo "📊 Displaying coverage report"
	$(call check_env_file,$(ENV))
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		coverage report --show-missing

.PHONY: coverage-html
coverage-html:
	@echo "📊 Generating HTML coverage report"
	$(call check_env_file,$(ENV))
	@mkdir -p $(ROOTDIR)/coverage-reports
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		coverage html -d coverage-reports/html
	@echo "✅ HTML coverage report: $(ROOTDIR)/coverage-reports/html/index.html"

# =============================================================================
# SECURITY SCANNING
# =============================================================================

.PHONY: security-scan
security-scan:
	@echo "🔒 Running security vulnerability scan"
	@mkdir -p $(ROOTDIR)/security-reports
	@echo "🔍 Scanning with bandit (Python security linter)"
	@docker run --rm -v $(ROOTDIR):/app:ro \
		--workdir /app \
		python:3.12-slim bash -c " \
			pip install bandit[toml] && \
			bandit -r . -f json -o security-reports/bandit-report.json || true && \
			bandit -r . -f txt -o security-reports/bandit-report.txt || true \
		"
	@echo "🔍 Scanning with safety (Python dependency vulnerabilities)"
	@docker run --rm -v $(ROOTDIR):/app:ro \
		--workdir /app \
		python:3.12-slim bash -c " \
			pip install safety && \
			safety check --json --output security-reports/safety-report.json || true && \
			safety check --output security-reports/safety-report.txt || true \
		"
	@echo "✅ Security scan completed"
	@echo "📋 Security reports: $(ROOTDIR)/security-reports/"

.PHONY: dependency-check
dependency-check:
	@echo "🔍 Checking dependencies for vulnerabilities"
	@mkdir -p $(ROOTDIR)/security-reports
	@docker run --rm -v $(ROOTDIR):/app:ro \
		python:3.12-slim bash -c " \
			pip install pip-audit && \
			cd /app && \
			pip-audit --format=json --output=security-reports/pip-audit.json || true && \
			pip-audit --format=cyclone-dx --output=security-reports/sbom.json || true \
		"
	@echo "✅ Dependency check completed"

.PHONY: license-check
license-check:
	@echo "📜 Checking license compatibility"
	@mkdir -p $(ROOTDIR)/security-reports
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		bash -c " \
			pip install pip-licenses && \
			pip-licenses --format=json --output-file=security-reports/licenses.json && \
			pip-licenses --format=plain --output-file=security-reports/licenses.txt \
		"
	@echo "✅ License check completed"

# =============================================================================
# CODE QUALITY PIPELINE
# =============================================================================

.PHONY: lint
lint:
	@echo "🔍 Running code linting with ruff"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run ruff check .

.PHONY: format-check
format-check:
	@echo "✨ Checking code formatting with ruff"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run ruff format --check .

.PHONY: type-check
type-check:
	@echo "🔍 Running type checking with mypy"
	@$(DOCKER_RUN_SIMPLE) $(IMAGE_NAME) uv run mypy src tests

.PHONY: check
check: lint format-check type-check
	@echo "✅ All CI checks passed"

# =============================================================================
# QUALITY GATES
# =============================================================================

.PHONY: quality-gate
quality-gate: lint format-check type-check test-full coverage security-scan
	@echo "🎯 Running complete quality gate"
	@echo "✅ All quality checks completed"
	@echo "📋 Reports generated:"
	@echo "  - Test reports: $(ROOTDIR)/test-reports/"
	@echo "  - Coverage reports: $(ROOTDIR)/coverage-reports/"
	@echo "  - Security reports: $(ROOTDIR)/security-reports/"

.PHONY: quality-gate-fast
quality-gate-fast: lint format-check test-fast
	@echo "🚀 Running fast quality gate (excluding slow tests and security scans)"
	@echo "✅ Fast quality checks completed"

# =============================================================================
# CI PIPELINE COMMANDS
# =============================================================================

.PHONY: pipeline
pipeline: build quality-gate
	@echo "🏗️  Running complete CI pipeline"
	@echo "✅ CI pipeline completed successfully"
	@$(MAKE) pipeline-summary

.PHONY: pipeline-fast
pipeline-fast: build quality-gate-fast
	@echo "🚀 Running fast CI pipeline"
	@echo "✅ Fast CI pipeline completed successfully"

.PHONY: pipeline-summary
pipeline-summary:
	@echo ""
	@echo "📊 CI Pipeline Summary"
	@echo "===================="
	@echo "Image: $(IMAGE_NAME)"
	@echo "Container: $(CONTAINER_NAME)"
	@echo "Build Date: $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")"
	@echo ""
	@echo "📋 Generated Reports:"
	@ls -la $(ROOTDIR)/test-reports/ 2>/dev/null || echo "  No test reports found"
	@ls -la $(ROOTDIR)/coverage-reports/ 2>/dev/null || echo "  No coverage reports found"
	@ls -la $(ROOTDIR)/security-reports/ 2>/dev/null || echo "  No security reports found"

# =============================================================================
# PERFORMANCE AND BENCHMARKING
# =============================================================================

.PHONY: benchmark
benchmark:
	@echo "⏱️  Running performance benchmarks"
	$(call check_env_file,$(ENV))
	@mkdir -p $(ROOTDIR)/test-reports
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		pytest -m "benchmark" --benchmark-json=test-reports/benchmark.json tests/ || echo "No benchmark tests found"

.PHONY: profile
profile:
	@echo "📈 Running performance profiling"
	$(call check_env_file,$(ENV))
	@mkdir -p $(ROOTDIR)/test-reports
	@docker run --rm $(DOCKER_OPTS) $(IMAGE_NAME) \
		pytest --profile --profile-svg=test-reports/profile.svg tests/ || echo "Profiling tools not available"

# =============================================================================
# ARTIFACT MANAGEMENT
# =============================================================================

.PHONY: collect-artifacts
collect-artifacts:
	@echo "📦 Collecting CI artifacts"
	@mkdir -p $(ROOTDIR)/ci-artifacts
	@if [ -d "$(ROOTDIR)/test-reports" ]; then \
		cp -r $(ROOTDIR)/test-reports $(ROOTDIR)/ci-artifacts/; \
	fi
	@if [ -d "$(ROOTDIR)/coverage-reports" ]; then \
		cp -r $(ROOTDIR)/coverage-reports $(ROOTDIR)/ci-artifacts/; \
	fi
	@if [ -d "$(ROOTDIR)/security-reports" ]; then \
		cp -r $(ROOTDIR)/security-reports $(ROOTDIR)/ci-artifacts/; \
	fi
	@echo "✅ Artifacts collected in: $(ROOTDIR)/ci-artifacts/"

.PHONY: clean-reports
clean-reports:
	@echo "🧹 Cleaning CI reports"
	@rm -rf $(ROOTDIR)/test-reports
	@rm -rf $(ROOTDIR)/coverage-reports
	@rm -rf $(ROOTDIR)/security-reports
	@rm -rf $(ROOTDIR)/ci-artifacts
	@echo "✅ Reports cleaned"

# =============================================================================
# CONTAINER UTILITIES
# =============================================================================

.PHONY: exec
exec:
	@echo "⚡ Executing command in CI container: $(ARG)"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make exec ARG='command to execute'"; \
		exit 1; \
	fi
	@docker exec -it $(CONTAINER_NAME) bash -c "cd /app && $(ARG)"

.PHONY: shell
shell:
	@echo "🐚 Opening shell in CI container (read-only mode)"
	@docker exec -it $(CONTAINER_NAME) bash

# =============================================================================
# STATUS AND MONITORING
# =============================================================================

.PHONY: status
status:
	@echo "📊 CI environment status"
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

# =============================================================================
# HELP AND DOCUMENTATION
# =============================================================================

.PHONY: ci-help
ci-help:
	@echo "🔬 MixSeek-Core CI Environment Commands"
	@echo ""
	@echo "🏗️  Build & Run:"
	@echo "  build              Build CI image"
	@echo "  run                Start CI container"
	@echo "  stop               Stop CI container"
	@echo "  restart            Restart CI container"
	@echo "  status             Show container and image status"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test-full          Run complete test suite with coverage"
	@echo "  test-unit          Run unit tests only"
	@echo "  test-integration   Run integration tests only"
	@echo "  test-parallel      Run tests in parallel"
	@echo "  test-fast          Run fast tests (exclude slow markers)"
	@echo ""
	@echo "📊 Coverage:"
	@echo "  coverage           Generate coverage reports"
	@echo "  coverage-report    Display coverage in terminal"
	@echo "  coverage-html      Generate HTML coverage report"
	@echo ""
	@echo "🔒 Security:"
	@echo "  security-scan      Run security vulnerability scans"
	@echo "  dependency-check   Check dependencies for vulnerabilities"
	@echo "  license-check      Check license compatibility"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint               Run code linting (ruff)"
	@echo "  format-check       Check code formatting"
	@echo "  type-check         Run type checking (mypy)"
	@echo ""
	@echo "🎯 Quality Gates:"
	@echo "  quality-gate       Run complete quality gate"
	@echo "  quality-gate-fast  Run fast quality gate"
	@echo ""
	@echo "🏗️  CI Pipeline:"
	@echo "  pipeline           Run complete CI pipeline"
	@echo "  pipeline-fast      Run fast CI pipeline"
	@echo "  pipeline-summary   Show pipeline summary"
	@echo ""
	@echo "⏱️  Performance:"
	@echo "  benchmark          Run performance benchmarks"
	@echo "  profile            Run performance profiling"
	@echo ""
	@echo "📦 Artifacts:"
	@echo "  collect-artifacts  Collect all CI artifacts"
	@echo "  clean-reports      Clean generated reports"
	@echo ""
	@echo "📖 Examples:"
	@echo "  make build && make pipeline"
	@echo "  make test-fast"
	@echo "  make quality-gate"

# Default target shows help
help: ci-help