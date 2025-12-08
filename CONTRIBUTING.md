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
   - Run commitizen to update version and CHANGELOG automatically
   - Final verification with PR to main
   - After merge, push tag to trigger GitHub Release creation
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

Version updates are automated using **commitizen** based on [Conventional Commits](https://www.conventionalcommits.org/).

#### Updating Version on Release Branch

```bash
# Create a release branch (branched from develop)
$ git checkout -b release-0.2.0 develop

# Update version (automatically determines version bump from commit messages)
# For alpha releases, use --prerelease alpha to increment build number
$ uv run cz bump --prerelease alpha --yes  # 0.1.0a1 → 0.1.0a2

# For manual version control (if needed)
$ uv run cz bump --prerelease alpha --increment MINOR --yes  # 0.1.0a1 → 0.2.0a1
$ uv run cz bump --prerelease alpha --increment PATCH --yes  # 0.1.0a1 → 0.1.1a1
$ uv run cz bump --prerelease alpha --increment MAJOR --yes  # 0.1.0a1 → 1.0.0a1

# To graduate from alpha to stable (remove prerelease suffix)
$ uv run cz bump --yes  # 0.1.0a1 → 0.1.0
```

#### Manual Version Update Verification

```bash
# Dry run (no actual changes) - for alpha releases
$ uv run cz bump --prerelease alpha --dry-run --yes

# Actual update - for alpha releases
$ uv run cz bump --prerelease alpha --yes
# → Automatically updates pyproject.toml
# → Automatically generates CHANGELOG.md from commit messages
# → Automatically creates git commit and tag
```

### Automatic Actions When Running commitizen

1. Analyzes commit messages (feat, fix, docs, etc.) to determine version bump
2. Updates the version in **pyproject.toml**
3. Generates **CHANGELOG.md** from Conventional Commits
4. Creates a git commit (`release: bump version to x.x.x`)
5. Creates an annotated git tag (`vx.x.x`)

**Important**: All commits MUST follow Conventional Commits format for proper automation.

## Release Process

### Release Preparation (Every 2 Weeks)

```bash
# 1. Verify the latest develop
$ git checkout develop
$ git pull origin develop

# 2. Create release branch
$ git checkout -b release-0.2.0 develop

# 3. Update version with commitizen (automatic version determination)
# For alpha releases, use --prerelease alpha
$ uv run cz bump --prerelease alpha --yes
# → Automatically determines version from commit messages
# → Automatically updates pyproject.toml
# → Automatically generates CHANGELOG.md
# → Automatically creates git commit and tag

# 4. Create PR to main
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
# → GitHub Actions automatically creates GitHub Release
# → Extracts CHANGELOG section for this version
# → Sets prerelease flag for alpha/beta/rc versions
```

### After Release

```bash
# Sync develop with the latest state of main (optional)
$ git checkout develop
$ git merge main
$ git push origin develop
```

## Commit Message Conventions

**IMPORTANT**: This project requires [Conventional Commits](https://www.conventionalcommits.org/) format for ALL commits. This is mandatory for automated version management and CHANGELOG generation.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Required Types

```
feat:     Add new feature (triggers minor version bump in stable, build bump in prerelease)
fix:      Bug fix (triggers patch version bump)
docs:     Documentation changes only
refactor: Code refactoring (no functional changes)
test:     Add or modify tests
release:  Version update or release (used by commitizen)
```

### Examples

```bash
# Feature addition
$ git commit -m "feat: add multi-agent orchestration framework"
$ git commit -m "feat(cli): add new mixseek exec command"

# Bug fixes
$ git commit -m "fix: resolve memory leak in agent cleanup"
$ git commit -m "fix(ui): correct result pagination logic"

# Documentation
$ git commit -m "docs: update getting-started guide"
$ git commit -m "docs(api): add docstrings to Agent class"

# Breaking changes (triggers major version bump in stable releases)
$ git commit -m "feat!: redesign API interface"
$ git commit -m "fix!: change default configuration format

BREAKING CHANGE: Configuration files now use TOML instead of JSON"
```

### Alpha Version Behavior

In alpha releases (current state), version bumps work as follows:
- `feat:` commits → Build number increment (0.1.0a1 → 0.1.0a2)
- `fix:` commits → Build number increment (0.1.0a2 → 0.1.0a3)
- Minor/major bumps → Manual override with `--minor` or `--major` flag

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
