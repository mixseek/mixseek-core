# AGENTS.md

This file provides guidance to Codex (OpenAI GPT-5 via Codex CLI) when working with code in this repository.

## Development Environment

### Package Management
- **Python**: 3.13.9 required
- **Package manager**: `uv` (fast dependency resolution)
- **Build system**: `uv_build >= 0.8.15`

### Installing Dependencies
```bash
# Install all dependencies (recommended)
uv sync

# Install with specific groups
uv sync --group dev
uv sync --group docs

# Install with optional dependencies
uv sync --extra snowflake
uv sync --extra aws
uv sync --extra all
```

### Running Tests
```bash
# Run all tests with pytest
pytest

# Run specific test file
pytest tests/agents/test_claude_agent_client.py

# Run with verbose output
pytest -s -vv --log-cli-level=DEBUG
```

### CI Environment (Docker-based)

For consistent testing environments, use the CI Docker container:

```bash
# Build CI Docker image
make -C dockerfiles/ci build

# Run tests in CI environment
make -C dockerfiles/ci test-fast        # Fast tests (exclude E2E)
make -C dockerfiles/ci test-full        # Full test suite with coverage

# Run code quality checks
make -C dockerfiles/ci lint             # Ruff linting
make -C dockerfiles/ci format-check     # Ruff format check
make -C dockerfiles/ci type-check       # mypy type checking

# Run complete quality gate
make -C dockerfiles/ci quality-gate-fast  # Fast quality checks
make -C dockerfiles/ci quality-gate       # Complete quality gate
```

**Note**: The CI environment matches the GitHub Actions environment and provides reproducible results.

### Code Quality

**Constitution**: This section implements Article 8 (Code Quality Standards) and Article 16 (Type Safety).

```bash
# Lint with ruff
ruff check .

# Format with ruff
ruff format .

# Auto-fix issues
ruff check --fix .

# Type check with mypy
mypy .

# Complete quality check (recommended before commit)
ruff check --fix . && ruff format . && mypy .
```

**Important**: This project uses **Ruff** (not flake8/black/isort) for all linting and formatting, plus **mypy** for static type checking.

Configuration in `pyproject.toml`:
- **Ruff**: Line length 119 chars, target Python 3.13.9, ignored rules E203/W503
- **mypy**: Strict mode enabled, comprehensive type checking required

### Type Safety

**Constitution**: Article 16 mandates strict type safety (non-negotiable).

This project enforces strict type safety requirements:
- All functions, methods, and variables must have type annotations
- mypy static type checking is mandatory before commits
- `Any` types should be avoided in favor of specific types
- Type errors must be resolved, not ignored

## Project Constitution

This project follows strict governance defined in `.specify/memory/constitution.md` (v1.3.0).

**CRITICAL**: Read constitution.md before starting any task and identify applicable Articles.

### Non-Negotiable Principles (絶対遵守)

1. **Article 3 - Test-First Imperative**
   - Write tests BEFORE implementation
   - Get user approval on tests
   - Verify Red phase (tests fail initially)

2. **Article 4 - Documentation Integrity**
   - Implementation MUST match specifications exactly
   - Stop and clarify if specs are ambiguous
   - Get user approval before changing docs

3. **Article 8 - Code Quality Standards**
   - Zero compromise on quality (no exceptions for deadlines)
   - MUST run before commit: `ruff check --fix . && ruff format . && mypy .`
   - All errors must be resolved (see Code Quality section below)

4. **Article 9 - Data Accuracy Mandate**
   - NO hardcoding: magic numbers, fixed strings, embedded credentials
   - NO implicit fallbacks: silent defaults, automatic completion, assumed values
   - NO interpolation based on assumptions
   - Explicit data source specification (environment variables, config files)
   - Proper error propagation with clear messages
   - All fixed values must be named constants or config-managed

5. **Article 10 - DRY Principle**
   - Search existing code BEFORE implementing (use Glob/Grep)
   - Stop if duplication detected, propose refactoring
   - Check specs for redundancy

6. **Article 14 - SpecKit Framework Consistency**
   - All SpecKit commands MUST align with `specs/001-specs`
   - Verify MixSeek-Core architecture (Leader/Member Agents, TUMIX)
   - Stop implementation if spec deviation detected

7. **Article 16 - Python Type Safety Mandate**
   - Comprehensive type annotations required (all functions/methods/variables)
   - mypy strict mode mandatory (see Type Safety section below)
   - Avoid `Any` types

### Core Architecture Principles

- **Article 1 - Library-First**: All features start as standalone libraries (not in app code)
- **Article 2 - CLI Interface Mandate**: All libraries expose CLI (stdin/stdout/stderr, JSON support)
- **Article 6 - Anti-Abstraction**: Use framework features directly (no unnecessary wrappers)
- **Article 11 - Refactoring Policy**: Fix existing code directly (NO V2/V3 classes)

### MixSeek-Specific Constraints

- **Article 15 - Naming Convention**: Use `<number>-mixseek-core-<name>` format
  - Use `.specify/scripts/bash/create-new-feature.sh` for directory creation
  - Example: `002-config`, `003-auth`

### Implementation Checklist

Before starting ANY task:
- [ ] Read `.specify/memory/constitution.md`
- [ ] Identify applicable Articles
- [ ] Search for existing implementations (Article 10)
- [ ] Verify spec clarity (Article 4)
- [ ] Design tests first (Article 3)

For complete governance rules: `.specify/memory/constitution.md`

## Commit Message Conventions

**CRITICAL**: This project requires [Conventional Commits](https://www.conventionalcommits.org/) format for **ALL commits**. This is mandatory for automated version management and CHANGELOG generation via commitizen.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Required Types

- `feat:` - Add new feature (triggers build number bump in alpha: 0.1.0a1 → 0.1.0a2)
- `fix:` - Bug fix (triggers build number bump in alpha: 0.1.0a2 → 0.1.0a3)
- `docs:` - Documentation changes only (no version bump)
- `refactor:` - Code refactoring without functional changes (no version bump)
- `test:` - Add or modify tests (no version bump)
- `release:` - Version update or release (used by commitizen)

### Examples

```bash
# Feature addition
git commit -m "feat: add multi-agent orchestration framework"
git commit -m "feat(cli): add new mixseek exec command"

# Bug fixes
git commit -m "fix: resolve memory leak in agent cleanup"
git commit -m "fix(ui): correct result pagination logic"

# Documentation
git commit -m "docs: update getting-started guide"
git commit -m "docs(api): add docstrings to Agent class"

# Refactoring and tests
git commit -m "refactor: simplify configuration loading logic"
git commit -m "test: add integration tests for team command"

# Breaking changes (for stable releases only)
git commit -m "feat!: redesign API interface"
git commit -m "fix!: change default configuration format

BREAKING CHANGE: Configuration files now use TOML instead of JSON"
```

### Alpha Version Behavior (Current State)

In alpha releases (`prerelease = true` in pyproject.toml):
- `feat:` commits → Build number increment only (0.1.0a1 → 0.1.0a2)
- `fix:` commits → Build number increment only (0.1.0a2 → 0.1.0a3)
- `docs:`, `refactor:`, `test:` → No version impact
- Minor/major bumps → Manual override with `--minor` or `--major` flag

### Important Notes

- **All lowercase**: Type must be lowercase (`feat`, not `Feat`)
- **Colon required**: Must have `:` after type (`feat:`, not `feat`)
- **Scope optional**: Scope is optional but useful (`feat(cli):` or just `feat:`)
- **Subject clarity**: Use imperative mood ("add feature" not "added feature")

### Verification

Before pushing commits, verify format compliance:

```bash
# View recent commits
git log --oneline -5

# Check if commitizen can parse commits and determine next version
uv run cz bump --dry-run --yes
```

For detailed versioning strategy, see [docs/versioning.md](docs/versioning.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Key Development Guidelines

### Code Style
- **Naming**: Classes use PascalCase, functions/variables use snake_case, constants use UPPER_SNAKE_CASE
- **Type hints**: Use Python 3.13.9 type hints extensively
- **Docstrings**: Google-style format with Args, Returns, Raises sections
- **Line length**: Maximum 119 characters
- **Imports**: Auto-sorted by Ruff (stdlib → third-party → local)

### Documentation Standards
This project strongly recommends comprehensive docstring usage:
- Public functions, classes, and modules should have comprehensive docstrings
- Google-style format is recommended (Args, Returns, Raises, Example sections)
- Docstrings should be consistent with type annotations
- Examples are encouraged for complex functions using doctest format

### Testing Strategy
- **pytest** for all testing
- **Unit tests**: Fast, no external dependencies (use mocks)
- **Integration tests**: Medium speed, mocked external services
- **E2E tests**: Real external services, marked with `@pytest.mark.e2e`
- Test markers: `unit`, `integration`, `e2e`, `snowflake`, `s3`

## Documentation

Documentation is built with **Sphinx** + **MyST-Parser** (Markdown support) + **Mermaid** diagrams.

### Building Docs
```bash
cd docs
make html
# Output: docs/_build/html/index.html

# Or using uv directly
uv run sphinx-build -M html docs docs/_build
```

### Documentation Guidelines

**IMPORTANT**: Follow the documentation guidelines defined in `.claude/sphinx.md`.

Key points:
- **MyST syntax**: Write all documentation in [MyST](https://mystmd.org/guide) format
- **Tone**: Avoid exaggerated expressions like "revolutionary", "groundbreaking"
- **Emphasis**: Use `**bold**` sparingly, only when truly necessary
- **Code block highlighting**: Be careful with syntax highlighter errors:
  - ❌ TOML: Don't use `key = null` (use comments instead)
  - ❌ JSON: Don't use ellipsis `...` in arrays/objects
  - ❌ Unknown lexers: Use `text` or `bash` for unsupported file types
  - ❌ Special characters: Avoid arrow symbols in code blocks

**Build command**:
```bash
uv run sphinx-build -M html docs docs/_build
```

For detailed guidelines and common pitfalls, see `.claude/sphinx.md`.

### Documentation
- All docs: `docs/*.md`
- Sphinx config: `docs/conf.py`
- Build system: `docs/Makefile`

## Technology Stack Summary

- **Runtime**: Python 3.13.9
- **Package manager**: uv
- **AI SDKs**: google-adk >=1.5.0, claude-agent-sdk >=0.1.0
- **MCP**: fastmcp >=2.9.0
- **Data**: duckdb >=1.3.1, pandas >=2.3.0, pyarrow >=18.1,<19.0.0
- **Testing**: pytest >=8.3.4, pytest-mock, pytest-asyncio
- **Linting**: ruff >=0.8.4
- **Type checking**: mypy >=1.13.0
- **Docs**: sphinx >=8.2.3, myst-parser >=4.0.1, sphinx-rtd-theme >=3.0.2
