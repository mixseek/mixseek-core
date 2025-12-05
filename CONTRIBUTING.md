# Contributing Guidelines

Thank you for contributing to MixSeek-Core. This document describes the development environment setup, development workflow, version management, and release process.

## Environment Setup

For detailed environment setup instructions, please refer to the [Developer Guide](docs/developer-guide.md).

This project recommends using a **Docker-based development environment**. Using Docker ensures a consistent development environment and avoids environment-related issues.

### Detailed Guides

- **[Developer Guide - Environment Setup](docs/developer-guide.md#開発環境のセットアップ)** - Detailed instructions for local and Docker environments
- **[Docker Build Configuration Guide](docs/docker-setup.md)** - Docker-specific user settings and build options

### Quick Start

```bash
# Clone the repository
git clone https://github.com/mixseek/mixseek-core.git
cd mixseek-core

# Docker environment (recommended)
make -C dockerfiles/dev build
make -C dockerfiles/dev run
make -C dockerfiles/dev shell

# Or local environment
uv sync --all-groups
```

> **Note**: We strongly recommend running quality checks and tests in the CI environment (`dockerfiles/ci/Dockerfile`) to ensure consistency with GitHub Actions.

## Development Workflow

This project uses a **develop-based development workflow**.

### Branch Structure

- **main**: Production-ready version (release tags are applied)
- **develop**: Development integration branch (integrates and validates multiple features)
- **feature/\***: Feature development branches

### Development Workflow

```
1. Create a feature branch from develop
   $ git checkout -b feature/your-feature-name develop

2. Implement the feature and commit
   $ git add .
   $ git commit -m "feat: your feature description"

3. Push the feature branch and create a PR
   $ git push origin feature/your-feature-name
   # Create a PR to develop on GitHub

4. Review & Test (conducted on develop branch)
   - Run CI tests
   - Verify integration tests
   - Check interactions between multiple features

5. Merge PR
   - Merge to develop after review approval
   - Conduct further integration tests on develop

6. Release preparation (every 2 weeks)
   - Create release-x.x.x branch from develop
   - Update version with bump2version
   - Manually update CHANGELOG.md (add version section under [Unreleased])
   - Final verification with PR to main
   - Create tag after merging to main
```

## Version Management

This project uses versioning compliant with [PEP 440](https://peps.python.org/pep-0440/).

### Version Format

```
0.1.0a1  → Alpha release (alpha version 1)
0.2.0b1  → Beta release
0.2.0rc1 → Release Candidate
1.0.0    → Stable release
```

### Version Update Method

Version updates are automated using the **bump2version** tool.

#### Updating Version on Release Branch

```bash
# Create a release branch (branched from develop)
$ git checkout -b release-0.2.0 develop

# Update minor version (0.1.0a1 → 0.2.0)
$ uv run bump2version minor

# Or update patch version (0.1.0 → 0.1.1)
$ uv run bump2version patch

# Or major update (0.1.0 → 1.0.0)
$ uv run bump2version major
```

#### Manual Version Update Verification

```bash
# Dry run (no actual changes)
$ uv run bump2version --dry-run --verbose minor

# Actual update
$ uv run bump2version minor
# → Automatically updates pyproject.toml
# → Automatically creates git commit and tag
# Note: CHANGELOG.md must be updated manually
```

### Automatic Actions When Running bump2version

1. Updates the version in **pyproject.toml**
2. Creates a git commit (`release: bump version to x.x.x`)
3. Creates a git tag (`vx.x.x`)

**Note**: CHANGELOG.md is **not** automatically updated by bump2version. You must manually add release notes under the `## [Unreleased]` section before running bump2version.

## Release Process

### Release Preparation (Every 2 Weeks)

```bash
# 1. Verify the latest develop
$ git checkout develop
$ git pull origin develop

# 2. Create release branch
$ git checkout -b release-0.2.0 develop

# 3. Manually update CHANGELOG.md
# Add release notes under ## [Unreleased] section

# 4. Update version (automated with bump2version)
$ uv run bump2version minor
# → Automatically updates pyproject.toml
# → Automatically creates git commit and tag

# 5. Create PR to main
$ git push origin release-0.2.0
# Create PR to main on GitHub
# PR title: "release: bump version to 0.2.0a1"
```

### Release Execution (After Merge)

```bash
# 1. Verify that the PR has been merged to main
$ git checkout main
$ git pull origin main

# 2. Push the tag
$ git push origin v0.2.0a1

# 3. Create GitHub Release
# Current: Manually create GitHub Release
# Future: GitHub Actions will automatically create Release (to be implemented in Issue #16 Phase 1)
#   → Automatically extract the relevant section from CHANGELOG.md
#   → Set it to GitHub Release
```

### After Release

```bash
# Sync develop with the latest state of main (optional)
$ git checkout develop
$ git merge main
$ git push origin develop
```

## Commit Message Conventions

Please write clear commit messages. Reference: [Conventional Commits](https://www.conventionalcommits.org/)

```
feat:     Add new feature
fix:      Bug fix
docs:     Documentation changes
refactor: Code refactoring
test:     Add or modify tests
release:  Version update or release
```

### Examples

```bash
$ git commit -m "feat: add multi-agent orchestration"
$ git commit -m "fix: resolve memory leak in agent cleanup"
$ git commit -m "docs: update getting-started guide"
```

## Running Tests

For detailed testing information, please refer to the [Developer Guide - Running Tests](docs/developer-guide.md#テストの実行).

### Quick Commands

```bash
# Testing in CI environment (recommended - same environment as GitHub Actions)
make -C dockerfiles/ci test-fast      # Fast tests (excluding E2E)
make -C dockerfiles/ci test-full      # Complete test suite

# Local environment testing
pytest                                 # Run all tests
pytest -v -s                          # With verbose output
pytest --cov=src/mixseek              # With coverage
```

## Code Quality Checks

For detailed code quality check information, please refer to the [Developer Guide - Code Quality](docs/developer-guide.md#コード品質).

### Running in CI Environment (Recommended)

**Please run this before creating a PR.** Run quality checks in the same environment as GitHub Actions:

```bash
# All quality checks (lint + format + type-check)
make -C dockerfiles/ci check

# Complete quality gate (tests + quality checks)
make -C dockerfiles/ci quality-gate-fast   # Fast version (recommended)
make -C dockerfiles/ci quality-gate        # Complete version
```

### Running in Local Environment

```bash
# Basic quality checks
uv run ruff check --fix .     # Linting + auto-fix
uv run ruff format .          # Code formatting
uv run mypy src tests         # Type checking
```

> **Important**: We strongly recommend running in the CI environment (`make -C dockerfiles/ci check`). Results may differ between local and CI environments.

## Documentation Updates

Documentation is managed with Sphinx.

```bash
# Build documentation
$ cd docs && uv run sphinx-build -M html . _build

# Open docs/_build/html/index.html in your browser
```

## Security Reporting

If you discover a security vulnerability, please use GitHub's [Private Vulnerability Reporting](https://github.com/mixseek/mixseek-core/security/advisories) instead of creating a public issue.

For details, see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the Apache License 2.0. Contributions are provided under the same license.

## Questions & Support

- **Documentation**: Refer to the [docs/](docs/) directory
- **Issues**: Report bugs or ask questions on [GitHub Issues](https://github.com/mixseek/mixseek-core/issues)
- **Discussions**: General questions on [GitHub Discussions](https://github.com/mixseek/mixseek-core/discussions)

Thank you for your contributions!
