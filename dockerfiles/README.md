# MixSeek-Core Docker Development Environment

This directory contains the Docker-based development environment templates for the MixSeek-Core project, providing standardized, reproducible environments across development, CI/CD, and production stages.

## 🏗️ Architecture Overview

```
dockerfiles/
├── Makefile.common          # Shared utilities and common targets
├── dev/                     # Development environment
│   ├── Dockerfile          # Full development environment with AI tools
│   ├── Makefile           # Development workflow commands
│   └── .env.dev.template  # Development environment variables template
├── ci/                      # CI/CD environment
│   ├── Dockerfile          # Minimal testing environment
│   ├── Makefile           # CI pipeline commands
│   └── .env.ci.template   # CI environment variables template
└── prod/                    # Production environment
    ├── Dockerfile          # Secure, minimal runtime environment
    ├── Makefile           # Production deployment commands
    └── .env.prod.template # Production environment variables template
```

## 🚀 Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional)
- Make 4.0+
- Git 2.30+
- Minimum 3GB free disk space

### 1. Environment Setup

```bash
# Copy and configure development environment
cp dockerfiles/dev/.env.dev.template .env.dev
vim .env.dev  # Configure your API keys and settings

# Verify Docker is running
docker info
```

### 2. Development Environment

```bash
# Build and start development container
make -C dockerfiles/dev build
make -C dockerfiles/dev run

# Connect to development container
make -C dockerfiles/dev bash

# Inside container - verify everything works
python --version  # Python 3.12.x
node --version    # Node.js 22.20.0
uv --version      # uv package manager
claude-code --version  # AI development tools
```

### 3. Run Tests

```bash
# Run full test suite
make -C dockerfiles/dev unittest

# Code quality checks
make -C dockerfiles/dev lint
make -C dockerfiles/dev format
```

## 📋 Environment Comparison

| Feature | Development | CI | Production |
|---------|-------------|----|-----------|
| **Base Image** | uv:0.8.24-python3.12 | uv:0.8.24-python3.12 | python:3.12-slim |
| **Python Tools** | Full (uv, pytest, ruff, debugpy, mypy) | Testing (uv, pytest, ruff, coverage) | Runtime only |
| **Node.js** | ✅ 22.20.0 | ❌ | ❌ |
| **AI Tools** | ✅ Claude Code, Codex, Gemini CLI | ❌ | ❌ |
| **Debug Support** | ✅ Port 5678 | ❌ | ❌ |
| **Security Hardening** | Basic | Medium | Maximum |
| **Volume Mounts** | Read/Write | Read-only | None |
| **Multi-stage Build** | ❌ | ❌ | ✅ |
| **Image Size** | ~1.2GB | ~600MB | ~300MB |

## 🛠️ Development Workflow

### Daily Development

```bash
# Start your development session
make -C dockerfiles/dev build && make -C dockerfiles/dev run
make -C dockerfiles/dev bash

# Inside container - typical workflow
make lint          # Check code quality
make format        # Format code
make unittest      # Run tests
make claude-code ARG="--help"  # Use AI assistant

# Debug a script
make -C dockerfiles/dev debug ARG="src/main.py"
```

### AI Development Tools

The development environment includes three AI coding assistants:

```bash
# Claude Code (Anthropic)
make -C dockerfiles/dev claude-code ARG="analyze src/main.py"

# OpenAI Codex
make -C dockerfiles/dev codex ARG="generate function to parse JSON"

# Google Gemini CLI
make -C dockerfiles/dev gemini ARG="review src/main.py"
```

### Hot Reload Development

```bash
# Enable file watching for automatic reloading
make -C dockerfiles/dev watch
```

## 🧪 CI/CD Pipeline

### Local CI Testing

```bash
# Build CI environment
make -C dockerfiles/ci build

# Run full CI pipeline
make -C dockerfiles/ci pipeline

# Run specific CI tasks
make -C dockerfiles/ci test-full        # Complete test suite
make -C dockerfiles/ci coverage         # Coverage reports
make -C dockerfiles/ci security-scan    # Security vulnerabilities
make -C dockerfiles/ci quality-gate     # All quality checks
```

### CI Reports

All CI runs generate reports in:
- `test-reports/` - Test results and JUnit XML
- `coverage-reports/` - Code coverage (XML/HTML)
- `security-reports/` - Security scan results

## 🚀 Production Deployment

### Production Build

```bash
# Build production image
make -C dockerfiles/prod build

# Deploy to production
make -C dockerfiles/prod deploy

# Monitor deployment
make -C dockerfiles/prod health-check
make -C dockerfiles/prod monitoring
```

### Blue-Green Deployment

```bash
# Perform zero-downtime deployment
make -C dockerfiles/prod deploy-blue-green

# Rollback if needed
make -C dockerfiles/prod rollback PREV_TAG=2025-10-14-abc123
```

### Production Monitoring

```bash
# Real-time monitoring
make -C dockerfiles/prod logs-follow
make -C dockerfiles/prod metrics
make -C dockerfiles/prod health-check

# Maintenance mode
make -C dockerfiles/prod maintenance-on
make -C dockerfiles/prod maintenance-off
```

## 🔐 Security Features

### Development Environment
- Non-root user execution
- Volume mounts for hot reload
- Debug port exposure (5678)
- API key management via environment variables

### CI Environment
- Read-only filesystem
- Security capability dropping (`--cap-drop=ALL`)
- Temporary filesystem for `/tmp`
- Non-privileged user execution
- Security scanning (Bandit, Safety, pip-audit)

### Production Environment
- Multi-stage build for minimal attack surface
- Read-only root filesystem
- No development tools or debug capabilities
- Security hardening with `no-new-privileges`
- Health checks and monitoring
- Container resource limits

## 📊 Environment Variables

Each environment uses secure template-based configuration:

### Development (`.env.dev`)
- AI tool API keys (Claude, OpenAI, Gemini)
- Development database connections
- Debug and logging settings
- Cloud provider credentials

### CI (`.env.ci`)
- Test database configurations
- Coverage thresholds
- Security scan settings
- Artifact storage settings

### Production (`.env.prod`)
- Production database connections (via Docker secrets)
- Cache configurations
- Monitoring endpoints
- Security settings

## 🐞 Troubleshooting

### Common Issues

#### Docker Build Fails
```bash
# Check Docker daemon
sudo systemctl status docker

# Clear build cache
docker system prune -a
make -C dockerfiles/dev build
```

#### Permission Errors
```bash
# Check UID/GID synchronization
id
make -C dockerfiles/dev build  # Rebuilds with correct permissions
```

#### Port Conflicts
```bash
# Check port usage
sudo lsof -i :5678

# Stop existing containers
make -C dockerfiles/dev stop
make -C dockerfiles/dev rm
```

#### AI Tools Not Working
```bash
# Verify API keys
cat .env.dev | grep API_KEY

# Restart container
make -C dockerfiles/dev restart
```

### Environment Reset

Complete environment reset:
```bash
# Stop all containers
make -C dockerfiles/dev cleanup
make -C dockerfiles/ci cleanup
make -C dockerfiles/prod cleanup

# Remove environment files
rm .env.dev .env.ci .env.prod

# Start fresh
cp dockerfiles/dev/.env.dev.template .env.dev
# Configure your settings...
make -C dockerfiles/dev build
```

## 📚 Advanced Usage

### Custom AI Development Workflow
```bash
# Start development with AI assistance
make -C dockerfiles/dev run
make -C dockerfiles/dev bash

# Inside container
claude-code analyze . --output suggestions.md
codex generate --description "REST API endpoint for user management"
gemini-cli review src/ --format markdown
```

### Parallel Development
```bash
# Multiple developers can work simultaneously
USER1: make -C dockerfiles/dev run   # Container: mixseek-core-dev
USER2: CONTAINER_NAME=mixseek-core-dev-2 make -C dockerfiles/dev run
```

### CI Integration
```bash
# In your CI/CD pipeline (.github/workflows/ci.yml)
- name: Run CI Pipeline
  run: |
    cp dockerfiles/ci/.env.ci.template .env.ci
    make -C dockerfiles/ci pipeline

- name: Collect Artifacts
  run: make -C dockerfiles/ci collect-artifacts
```

## 🔄 Maintenance

### Regular Tasks

```bash
# Update base images (monthly)
docker pull ghcr.io/astral-sh/uv:0.8.24-python3.12-bookworm-slim
make -C dockerfiles/dev build --no-cache

# Security updates
make -C dockerfiles/ci security-scan
make -C dockerfiles/prod security-audit

# Cleanup unused resources
docker system prune -a
```

### Version Management

```bash
# List available versions
make -C dockerfiles/prod list-versions

# Create backup before updates
make -C dockerfiles/prod backup-image

# Tag releases
docker tag mixseek-core/prod:latest mixseek-core/prod:v1.0.0
```

## 📖 Documentation

- [Dockerfile Interface Contract](../specs/003-dockerfiles/contracts/dockerfile-interface.md)
- [Makefile Interface Contract](../specs/003-dockerfiles/contracts/makefile-interface.md)
- [Environment Template Contract](../specs/003-dockerfiles/contracts/environment-template.md)
- [Quick Start Guide](../specs/003-dockerfiles/quickstart.md)
- [Data Model](../specs/003-dockerfiles/data-model.md)

## 🤝 Contributing

When modifying the Docker environment:

1. Follow the interface contracts
2. Update environment templates
3. Test all environments
4. Update documentation
5. Verify security compliance

## 📞 Support

For issues with the Docker environment:

1. Check troubleshooting section above
2. Review container logs: `make -C dockerfiles/[env] logs`
3. Validate environment: `make -C dockerfiles/[env] validate`
4. Check system resources: `docker system df`

---

**Version**: 1.0.0 | **Last Updated**: 2025-10-15 | **Maintained by**: MixSeek-Core Development Team