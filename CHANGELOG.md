# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/).

## v0.1.0a5 (2025-12-24)

### Feat

- skip model prefix validation for custom agents

### Fix

- separate empty model and missing colon error messages

## v0.1.0a4 (2025-12-23)

### Feat

- **orchestrator**: add on_round_complete callback parameter

## v0.1.0a3 (2025-12-16)

### Breaking Changes

- **evaluator**: Score constraints removed from `MetricScore.score` and `EvaluationResult.overall_score`
  - Custom metrics can now use any real-number values (negative, above 100, etc.)
  - **Migration**: Existing databases must be either recreated or migrated according to the procedure documented in [PR #55](https://github.com/mixseek/mixseek-core/pull/55)
  - Existing `BaseLLMEvaluation.score` field remains constrained to 0-100 for LLM output compatibility

### Feat

- **evaluator**: remove score constraints to support unlimited range (#55)
- **storage**: remove score constraints from AggregationStore

### Fix

- address code review feedback from gemini-code-assist
- Propagate MemberAgentResult.status to MemberSubmission (#59)
- **docs**: change deploy trigger from push to release and manual

## v0.1.0a2 (2025-12-08)

### Feat

- adopt commitizen for automated version management with PEP 440 compliance

### Fix

- replace result.stderr with result.stdout in CLI tests
- use streamlit in-process launch for uv tool install compatibility (#24)
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
