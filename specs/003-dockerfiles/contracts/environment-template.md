# Environment Template Contract

**Feature**: Docker開発環境テンプレート
**Created**: 2025-10-15
**Type**: Configuration Contract

## 概要

この契約は、環境変数テンプレートファイルの構造、セキュリティ要件、および各環境での使用方法を定義します。

## ファイル構造

```
dockerfiles/templates/
├── .env.dev.template      # 開発環境テンプレート
├── .env.ci.template       # CI環境テンプレート
└── .env.prod.template     # 本番環境テンプレート
```

## 共通テンプレート形式

### ファイルヘッダー

すべてのテンプレートファイルは以下のヘッダーを含む：

```bash
# =============================================================================
# MixSeek-Core Environment Configuration Template
# Environment: [DEV|CI|PROD]
# Created: YYYY-MM-DD
# Description: [Environment-specific description]
# =============================================================================

# IMPORTANT: This is a TEMPLATE file. Copy to .env.[environment] and fill in actual values.
# DO NOT commit actual secrets to version control.

# Usage:
#   1. Copy this file to project root as .env.[environment]
#   2. Replace [VALUE] placeholders with actual values
#   3. Ensure .env.[environment] is in .gitignore
#   4. For production, consider using Docker secrets or external secret management
```

### 変数分類システム

```bash
# =============================================================================
# SECTION: [SECTION_NAME]
# Description: [Purpose of this section]
# Security Level: [PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED]
# =============================================================================

# [VARIABLE_NAME]
# Type: [string|integer|boolean|url|path|json]
# Required: [yes|no]
# Description: [Variable purpose and usage]
# Example: [Example value or format]
# Security: [Notes about security considerations]
[VARIABLE_NAME]=[PLACEHOLDER_VALUE]
```

## 開発環境テンプレート (.env.dev.template)

### 基本システム設定

```bash
# =============================================================================
# SECTION: System Configuration
# Description: Basic system and runtime settings
# Security Level: PUBLIC
# =============================================================================

# Timezone Configuration
# Type: string
# Required: yes
# Description: System timezone for logging and scheduling
# Example: Asia/Tokyo, UTC, America/New_York
TZ=Asia/Tokyo

# Debug Mode
# Type: boolean
# Required: yes
# Description: Enable debug logging and development features
# Example: true, false
DEBUG=true

# Log Level
# Type: string
# Required: yes
# Description: Logging verbosity level
# Example: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=DEBUG

# Python Configuration
# Type: boolean
# Required: no
# Description: Prevent Python from writing .pyc files
# Example: 1 (enabled), 0 (disabled)
PYTHONDONTWRITEBYTECODE=1
```

### AI開発ツール設定

```bash
# =============================================================================
# SECTION: AI Development Tools
# Description: Configuration for Claude Code, Codex, and Gemini CLI
# Security Level: CONFIDENTIAL
# =============================================================================

# Claude Code Configuration
# Type: string
# Required: yes (for Claude Code usage)
# Description: API key for Claude Code authentication
# Example: sk-ant-api03-...
# Security: Store securely, rotate regularly, monitor usage
ANTHROPIC_API_KEY=[CLAUDE_API_KEY]

# Type: string
# Required: no
# Description: Preferred Claude model for code assistance
# Example: claude-3-sonnet, claude-3-haiku
ANTHROPIC_MODEL=claude-3-sonnet

# OpenAI Codex Configuration
# Type: string
# Required: yes (for Codex usage)
# Description: API key for OpenAI Codex authentication
# Example: sk-...
# Security: Store securely, monitor token usage, set usage limits
OPENAI_API_KEY=[OPENAI_API_KEY]

# Type: string
# Required: no
# Description: Preferred OpenAI model for code generation
# Example: gpt-4, gpt-3.5-turbo
OPENAI_MODEL=gpt-4

# Google Gemini Configuration
# Type: string
# Required: yes (for Gemini usage)
# Description: API key for Google Gemini authentication
# Example: AIza...
# Security: Store securely, configure quota limits
GOOGLE_AI_API_KEY=[GEMINI_API_KEY]

# Type: string
# Required: no
# Description: Preferred Gemini model
# Example: gemini-pro, gemini-pro-vision
GOOGLE_AI_MODEL=gemini-pro
```

### クラウドプロバイダー設定

```bash
# =============================================================================
# SECTION: Cloud Provider Configuration
# Description: Authentication and configuration for cloud services
# Security Level: RESTRICTED
# =============================================================================

# AWS Configuration
# Type: string
# Required: no
# Description: AWS access key for development resources
# Example: AKIA...
# Security: Use IAM roles in production, temporary credentials preferred
AWS_ACCESS_KEY_ID=[AWS_ACCESS_KEY]
AWS_SECRET_ACCESS_KEY=[AWS_SECRET_KEY]
AWS_DEFAULT_REGION=ap-northeast-1

# GCP Configuration
# Type: path
# Required: no
# Description: Path to GCP service account credentials file
# Example: /app/.cred/gcp_credentials.json
# Security: Mount as Docker secret in production
GOOGLE_APPLICATION_CREDENTIALS=/app/.cred/gcp_credentials.json

# Type: string
# Required: no
# Description: GCP project ID for development
# Example: my-project-dev
GOOGLE_CLOUD_PROJECT=[GCP_PROJECT_ID]
```

### 開発ツール設定

```bash
# =============================================================================
# SECTION: Development Tools
# Description: Configuration for development and debugging tools
# Security Level: INTERNAL
# =============================================================================

# Hot Reload Configuration
# Type: boolean
# Required: no
# Description: Enable automatic code reloading during development
# Example: true, false
HOT_RELOAD_ENABLED=true

# Type: string
# Required: no
# Description: File patterns to watch for changes (comma-separated)
# Example: **/*.py,**/*.yaml,**/*.json
WATCH_PATTERNS=**/*.py,**/*.yaml,**/*.json,**/*.md

# Debugger Configuration
# Type: integer
# Required: no
# Description: Port for remote Python debugger (debugpy)
# Example: 5678
DEBUGPY_PORT=5678

# Type: boolean
# Required: no
# Description: Enable remote debugging on container start
# Example: true, false
DEBUGPY_ENABLED=false
```

### データベース設定

```bash
# =============================================================================
# SECTION: Database Configuration
# Description: Database connections for development
# Security Level: INTERNAL
# =============================================================================

# PostgreSQL Configuration
# Type: string
# Required: no
# Description: PostgreSQL connection URL for development
# Example: postgresql://user:pass@localhost:5432/dbname
# Security: Use environment-specific credentials
DATABASE_URL=postgresql://[DB_USER]:[DB_PASSWORD]@localhost:5432/[DB_NAME]_dev

# Redis Configuration
# Type: string
# Required: no
# Description: Redis connection URL for caching
# Example: redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0
```

## CI環境テンプレート (.env.ci.template)

### CI特化設定

```bash
# =============================================================================
# MixSeek-Core Environment Configuration Template
# Environment: CI
# Created: 2025-10-15
# Description: Continuous Integration environment configuration
# =============================================================================

# =============================================================================
# SECTION: CI System Configuration
# Description: Basic CI environment settings
# Security Level: PUBLIC
# =============================================================================

# Environment Identification
# Type: string
# Required: yes
# Description: Identifies current environment for conditional logic
# Example: ci, test, staging
ENVIRONMENT=ci

# CI Mode
# Type: boolean
# Required: yes
# Description: Enables CI-specific optimizations and logging
# Example: true, false
CI=true

# Timezone
# Type: string
# Required: yes
# Description: System timezone for test timestamps
TZ=UTC

# Python Configuration
# Type: boolean
# Required: yes
# Description: Prevent .pyc file generation in CI
PYTHONDONTWRITEBYTECODE=1

# Type: boolean
# Required: yes
# Description: Force unbuffered Python output for real-time logs
PYTHONUNBUFFERED=1

# Logging Configuration
# Type: string
# Required: yes
# Description: Log level for CI execution
LOG_LEVEL=INFO

# Type: boolean
# Required: yes
# Description: Enable structured logging for CI tooling
STRUCTURED_LOGGING=true
```

### テスト設定

```bash
# =============================================================================
# SECTION: Testing Configuration
# Description: Test execution and reporting settings
# Security Level: INTERNAL
# =============================================================================

# Test Database
# Type: string
# Required: yes
# Description: Test database connection string
# Example: sqlite:///test.db, postgresql://test:test@localhost/test_db
DATABASE_URL=sqlite:///test.db

# Test Parallelization
# Type: integer
# Required: no
# Description: Number of parallel test workers
# Example: 4, auto
PYTEST_WORKERS=auto

# Coverage Reporting
# Type: boolean
# Required: yes
# Description: Enable code coverage collection
COVERAGE_ENABLED=true

# Type: integer
# Required: no
# Description: Minimum required code coverage percentage
COVERAGE_THRESHOLD=80

# Test Output Format
# Type: string
# Required: yes
# Description: Output format for test results
# Example: junit, json, html
TEST_OUTPUT_FORMAT=junit
```

### セキュリティスキャン設定

```bash
# =============================================================================
# SECTION: Security Configuration
# Description: Security scanning and validation settings
# Security Level: INTERNAL
# =============================================================================

# Security Scan
# Type: boolean
# Required: yes
# Description: Enable security vulnerability scanning
SECURITY_SCAN_ENABLED=true

# Type: string
# Required: no
# Description: Security scan severity threshold
# Example: HIGH, MEDIUM, LOW
SECURITY_THRESHOLD=MEDIUM

# Dependency Check
# Type: boolean
# Required: yes
# Description: Enable dependency vulnerability checking
DEPENDENCY_CHECK_ENABLED=true
```

## 本番環境テンプレート (.env.prod.template)

### 本番システム設定

```bash
# =============================================================================
# MixSeek-Core Environment Configuration Template
# Environment: PROD
# Created: 2025-10-15
# Description: Production environment configuration
# =============================================================================

# =============================================================================
# SECTION: Production System Configuration
# Description: Production runtime settings
# Security Level: RESTRICTED
# =============================================================================

# Environment Identification
# Type: string
# Required: yes
# Description: Production environment identifier
ENVIRONMENT=production

# Debug Mode
# Type: boolean
# Required: yes
# Description: Debug mode MUST be disabled in production
DEBUG=false

# Log Level
# Type: string
# Required: yes
# Description: Production logging level
LOG_LEVEL=WARNING

# Timezone
# Type: string
# Required: yes
# Description: Production timezone
TZ=UTC

# Python Configuration
# Type: boolean
# Required: yes
# Description: Production Python settings
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

### セキュリティ設定

```bash
# =============================================================================
# SECTION: Security Configuration
# Description: Production security settings
# Security Level: RESTRICTED
# =============================================================================

# Secret Key
# Type: string
# Required: yes
# Description: Application secret key for cryptographic operations
# Example: Use 32+ character random string
# Security: Generate unique key per environment, rotate regularly
SECRET_KEY=[PRODUCTION_SECRET_KEY]

# HTTPS Configuration
# Type: boolean
# Required: yes
# Description: Force HTTPS for all connections
FORCE_HTTPS=true

# Security Headers
# Type: boolean
# Required: yes
# Description: Enable security headers
SECURITY_HEADERS_ENABLED=true

# CORS Settings
# Type: string
# Required: yes
# Description: Allowed origins for CORS (comma-separated)
# Example: https://app.example.com,https://admin.example.com
ALLOWED_ORIGINS=[PRODUCTION_ORIGINS]
```

### 外部サービス設定

```bash
# =============================================================================
# SECTION: External Services Configuration
# Description: Production external service connections
# Security Level: RESTRICTED
# =============================================================================

# Database Configuration
# Type: string
# Required: yes
# Description: Production database connection string
# Security: Use connection pooling, SSL connections, read replicas
DATABASE_URL=[PRODUCTION_DATABASE_URL]

# Type: integer
# Required: no
# Description: Database connection pool size
DATABASE_POOL_SIZE=10

# Cache Configuration
# Type: string
# Required: yes
# Description: Production Redis/cache connection
CACHE_URL=[PRODUCTION_CACHE_URL]

# Monitoring and Observability
# Type: string
# Required: no
# Description: Application monitoring service URL
MONITORING_URL=[MONITORING_SERVICE_URL]

# Type: string
# Required: no
# Description: Log aggregation service endpoint
LOG_ENDPOINT=[LOG_SERVICE_ENDPOINT]
```

## セキュリティ要件

### 機密情報管理

1. **テンプレートファイル**: プレースホルダー値のみ含む、実際の秘密情報を含まない
2. **実際の設定ファイル**: `.gitignore`で除外、実際の秘密情報を含む
3. **本番環境**: Docker secretsまたは外部シークレット管理システム使用

### プレースホルダー命名規則

```bash
# 形式: [DESCRIPTOR]
# 例:
DATABASE_URL=[DATABASE_CONNECTION_STRING]
API_KEY=[SERVICE_NAME_API_KEY]
SECRET=[PURPOSE_SECRET_VALUE]
```

### バリデーション

```bash
# テンプレート完整性チェック
validate_template() {
    local template_file="$1"
    local required_vars="$2"

    # プレースホルダー形式チェック
    if grep -q "=.*[^[].*[^]]$" "$template_file"; then
        echo "Error: Non-placeholder values found in template"
        return 1
    fi

    # 必須変数存在チェック
    for var in $required_vars; do
        if ! grep -q "^$var=" "$template_file"; then
            echo "Error: Required variable $var missing from template"
            return 1
        fi
    done
}
```

## 使用ワークフロー

### 開発者セットアップ

```bash
# 1. テンプレートをコピー
cp dockerfiles/templates/.env.dev.template .env.dev

# 2. 実際の値を設定
vim .env.dev  # プレースホルダーを実際の値に置換

# 3. .gitignoreで除外されていることを確認
grep -q "^\.env\." .gitignore || echo ".env.*" >> .gitignore

# 4. 環境変数を検証
make validate-env ENV=dev
```

### CI/CD統合

```bash
# CI環境での使用例
envsubst < dockerfiles/templates/.env.ci.template > .env.ci
docker run --env-file .env.ci [IMAGE]
```

### 本番デプロイメント

```bash
# Docker secretsを使用
echo "$DATABASE_URL" | docker secret create db_url -
echo "$API_KEY" | docker secret create api_key -

# シークレットをマウント
docker run \
  --secret db_url \
  --secret api_key \
  [PRODUCTION_IMAGE]
```

このテンプレート契約により、環境間の一貫性とセキュリティが確保され、開発チーム全体で統一された設定管理が実現されます。