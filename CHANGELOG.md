# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

## [0.1.0a1] - 2025-12-04

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
