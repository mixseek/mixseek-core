# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/).

## v0.1.0a14 (2026-04-15)

### Fix

- **cli**: exec.pyのステップ番号重複を修正（3重複→4〜10に連番化）
- **logging**: UI側のtype: ignore[arg-type]をcast(LogFormatType/LevelName)に統一
- **logging**: logging_setup.pyのLogfireハンドラエラーログを構造化
- **logging**: evaluator.pyのカスタムメトリクスロードエラーログを構造化
- CLAUDE.mdのリバートとlog-refactor.md計画ファイルの削除
- **logging**: JsonSpanProcessorにtrace_idとeventsを追加
- **config**: config/logging.pyのPR範囲外docstring翻訳を元に戻す
- **config**: constants.pyのPR範囲外コメント翻訳を元に戻す
- **typing**: logfire.pyのAny型をTYPE_CHECKINGガードで具体型に変更
- **logging**: JSONログ出力時の二重エスケープ・Unicodeエスケープを修正
- **typing**: CI mypyエラー34件を修正
- **ui**: ループ内の冗長なimport jsonを削除
- **logging**: extra dictの冗長なtimestampフィールドを削除
- **logging**: copilotレビュー指摘を修正（実装3件+テスト3件）
- **logging**: copilotレビュー指摘2点を修正

### Refactor

- **cli**: setup_logfire_from_cliのmodel_copy 2行を1行に統合
- **examples**: adk_researchのロガーNOTEコメントを1行に短縮
- **cli**: logfire/logging初期化ロジックをCLI共通ヘルパーに統一
- **logging**: _STANDARD_FIELDSをモジュールレベル定数に統一
- **cli**: --log-format オプション追加、setup_logfire シグネチャ対応
- **logging**: root logger → "mixseek" named loggerに統一し4モード対応

## v0.1.0a13 (2026-04-08)

### Feat

- **cli**: add --dry-run flag to exec command with preflight integration
- **config**: add preflight check module for dry-run validation

### Fix

- **test**: update exec tests to use preflight_result.orchestrator_settings
- **config**: change empty teams preflight status from WARN to ERROR
- **evaluator**: use acronym-aware regex for CamelCase to snake_case conversion
- **config**: use LeaderAgentSettings default instead of hardcoded model ID

### Refactor

- **config**: remove | Any union from validator signatures for type safety
- **config**: reuse preflight-loaded settings to eliminate double config load
- **config**: remove unused CheckStatus.WARN and warn_count
- **config**: split preflight.py into package with validators/ subdirectory

## v0.1.0a12 (2026-04-02)

### Fix

- apply ruff format to orchestrator.py
- **cli**: display partial success teams in leaderboard and summary
- **orchestrator**: recover partial results when team fails mid-round
- **cli**: return proper exit codes from exec command based on team results

### Refactor

- **orchestrator**: remove unreachable except PartialTeamFailureError
- extract partial_team_ids property and recovery helper to reduce duplication
- **cli**: simplify exit code logic by removing intermediate variable

## v0.1.0a11 (2026-03-26)

## v0.1.0a10 (2026-03-26)

### Fix

- apply ruff format to orchestrator.py
- **cli**: display partial success teams in leaderboard and summary
- **orchestrator**: recover partial results when team fails mid-round
- **cli**: return proper exit codes from exec command based on team results

### Refactor

- **orchestrator**: remove unreachable except PartialTeamFailureError
- extract partial_team_ids property and recovery helper to reduce duplication
- **cli**: simplify exit code logic by removing intermediate variable

## v0.1.0a9 (2026-02-25)

### Feat

- **evaluator**: add execution_id, team_id, round_number to EvaluationRequest and BaseMetric.evaluate

### Fix

- **evaluator**: fix InvalidMetricNoEvaluate test to return None instead of valid MetricScore

## v0.1.0a8 (2026-01-28)

### Feat

- add Publish PyPI workflow to release.yml

## v0.1.0a7 (2026-01-27)

### Fix

- use key existence check instead of or operator for tool_settings
- tool_settings should be recognized at member level, not only under metadata

## v0.1.0a6 (2026-01-14)

### Feat

- propagate execution_id to Member Agent context

## v0.1.0a5 (2025-12-24)

### Feat

- skip model prefix validation for custom agents

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
- Evaluation system with customizable metrics (Coverage, Relevance, Novelty (LLMPlain-based), Clarity)
- Judgment system for multi-round refinement
- Comprehensive documentation (Getting Started, Advanced Guide, Configuration Reference)
- Docker support for development environments

### Fixed
- Documentation clarity improvements for Python version management
- DuckDB CLI installation guidance in getting-started-advanced.md
