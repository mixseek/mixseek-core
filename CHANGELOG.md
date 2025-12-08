# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/).

## v0.1.0a2 (2025-12-08)

### Feat

- migrate from python-semantic-release to commitizen for PEP 440 compliance
- migrate from bump2version to python-semantic-release
- implement automated version management with bump2version (Issue #17)

### Fix

- replace result.stderr with result.stdout in CLI tests
- remove docs/refactor/test from patch_tags to match documentation
- use conventional parser instead of deprecated angular parser
- use streamlit in-process launch for uv tool install compatibility (#24)
- remove CHANGELOG.md from bump2version management
- improve CHANGELOG.md update robustness in bump2version config
- Use field-based filtering instead of env_prefix filtering
- Filter dotenv variables by env_prefix (Issue #2)

### Refactor

- address code review feedback for PR #25

## v0.1.0a1 (2025-12-04)

### Added
- Initial alpha release of MixSeek-Core
- Multi-agent orchestration framework with Leader/Member agent hierarchy
- Core CLI commands: `mixseek team`, `mixseek exec`, `mixseek init`, `mixseek config init`
- Configuration management system (TOML + environment variables)
- Streamlit-based web UI for orchestration execution and result visualization
- DuckDB integration for execution result storage and analysis
- Support for multiple AI models (Gemini, Grok)
- Multi-perspective search capability with 3 specialized teams (General, SNS, Academic)
- Evaluation system with customizable metrics (Coverage, Relevance, Novelty, Clarity)
- Judgment system for multi-round refinement
- Comprehensive documentation (Getting Started, Advanced Guide, Configuration Reference)
- Docker support for development environments

### Fixed
- Documentation clarity improvements for Python version management
- DuckDB CLI installation guidance in getting-started-advanced.md
