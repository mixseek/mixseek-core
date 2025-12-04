# Tasks: Google ADK検索エージェントサンプル

**Feature Branch**: `134-custom-member-adk`
**Input**: Design documents from `/specs/020-custom-member-adk/`
**Prerequisites**: plan.md, spec.md

**Implementation Location**: `examples/custom_agents/adk_research/` - NO changes to `src/mixseek/`

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for ADK Research Agent sample

- [x] T001 Create directory structure `examples/custom_agents/adk_research/`
- [x] T002 [P] Create `examples/custom_agents/adk_research/__init__.py` with module exports
- [x] T003 [P] Verify `google-adk >= 1.19.0` in pyproject.toml dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure that MUST be complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create `ADKAgentConfig` Pydantic model in `examples/custom_agents/adk_research/models.py`
  - Fields: gemini_model, temperature, max_output_tokens, search_result_limit, researcher_count, timeout_seconds
  - Article 9 compliant validators
  - Full type annotations (Article 16)

- [x] T005 [P] Create `SearchResult` Pydantic model in `examples/custom_agents/adk_research/models.py`
  - Fields: url, title, snippet, timestamp
  - Used for source tracking (FR-004)

- [x] T006 [P] Create `ResearchReport` Pydantic model in `examples/custom_agents/adk_research/models.py`
  - Fields: summary, key_findings, sources, patterns, recommendations
  - Used for Deep Research output

- [x] T007 Create `ADKRunnerWrapper` class in `examples/custom_agents/adk_research/runner.py`
  - `__init__(agent, app_name)`: Initialize InMemoryRunner
  - `run(user_id, message)`: Execute with session management
  - `cleanup()`: Clean up session resources
  - Use latest ADK API: `from google.adk.runners import InMemoryRunner`

- [x] T008 Create TOML configuration `examples/custom_agents/adk_research/adk_research_agent.toml`
  - `[agent]` section: type="custom", name, model="google-gla:gemini-2.5-flash"
  - `[agent.plugin]` section: path, agent_class="ADKResearchAgent"
  - `[agent.metadata.tool_settings.adk_research]` section: all ADK settings
  - Article 9 compliant (no hardcoding)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Web検索と情報要約 (Priority: P1) 🎯 MVP

**Goal**: google_searchツールを使用したWeb検索クエリの実行と要約提供

**Independent Test**: LlmAgentを単独で呼び出し、検索結果取得と要約が正常動作することを確認

**FR Coverage**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008

### Implementation for User Story 1

- [x] T009 [US1] Create `ADKResearchAgent` class skeleton in `examples/custom_agents/adk_research/agent.py`
  - Extend `BaseMemberAgent`
  - `__init__(config: MemberAgentConfig)`: Extract config from metadata
  - Validate with `ADKAgentConfig.model_validate()`

- [x] T010 [US1] Implement `_create_researcher()` method in `agent.py`
  - Create single `LlmAgent` with `google_search` tool
  - Use latest API: `from google.adk.agents import LlmAgent`
  - Use: `from google.adk.tools import google_search`
  - Model: configurable from `ADKAgentConfig.gemini_model` (default: gemini-2.5-flash)
  - Set `output_key` for state sharing

- [x] T011 [US1] Implement `_parse_sources()` method in `agent.py`
  - Extract URLs/titles from ADK response (groundingMetadata)
  - Return list of `SearchResult` for `MemberAgentResult.metadata`
  - FR-004: 100% source tracking

- [x] T012 [US1] Implement `_handle_error()` method in `agent.py`
  - Classify errors: AUTH_ERROR, RATE_LIMIT, TIMEOUT, NETWORK_ERROR, SEARCH_NO_RESULTS
  - Generate structured error info in metadata (FR-006)
  - Return `MemberAgentResult` with error status

- [x] T013 [US1] Implement `execute()` method in `agent.py` (basic search mode)
  - Create single researcher LlmAgent
  - Run via `ADKRunnerWrapper`
  - Parse response content to Markdown (FR-002)
  - Extract sources to metadata (FR-004)
  - Handle errors with `_handle_error()` (FR-005, FR-006)
  - Return `MemberAgentResult`

- [x] T014 [US1] Update `__init__.py` exports
  - Export: ADKResearchAgent, ADKAgentConfig, SearchResult, ResearchReport

**Checkpoint**: User Story 1完了 - 単一検索クエリの実行と要約が独立してテスト可能

---

## Phase 4: User Story 2 - Deep Research パイプライン実行 (Priority: P2)

**Goal**: ParallelAgent + SequentialAgentによる並列検索・統合要約パイプライン

**Independent Test**: 3並列のリサーチエージェントと要約エージェントのパイプライン全体をテスト

**FR Coverage**: FR-003

### Implementation for User Story 2

- [x] T015 [US2] Implement `_create_summarizer()` method in `agent.py`
  - Create summarizer `LlmAgent` for result synthesis
  - Instruction: Analyze parallel results, extract patterns, generate structured report
  - No tools (synthesis only)
  - Set `output_key` for final output

- [x] T016 [US2] Implement `_build_pipeline()` method in `agent.py`
  - Create 3 researcher `LlmAgent` with different focus areas
  - Wrap in `ParallelAgent`: `from google.adk.agents import ParallelAgent`
  - Create summarizer `LlmAgent`
  - Combine with `SequentialAgent`: `from google.adk.agents import SequentialAgent`
  - Return pipeline agent

- [x] T017 [US2] Extend `execute()` method for Deep Research mode
  - Detect query complexity or explicit deep_research flag in context
  - Build and run pipeline via `ADKRunnerWrapper`
  - Parse `ResearchReport` structure from response
  - Extract all sources from parallel agents
  - Return comprehensive `MemberAgentResult`

- [x] T018 [US2] Add partial failure handling
  - Handle case where some parallel agents fail
  - Generate partial report from successful results
  - Document failures in metadata

**Checkpoint**: User Story 2完了 - Deep Researchパイプラインが独立してテスト可能

---

## Phase 5: User Story 3 - テストとデバッグ (Priority: P3)

**Goal**: 単体テスト・統合テスト・E2Eテストによる品質保証

**Independent Test**: テストスイート自体が実行可能

**FR Coverage**: FR-009

### Test Implementation for User Story 3

- [x] T019 [P] [US3] Create `examples/custom_agents/adk_research/tests/__init__.py`

- [x] T020 [P] [US3] Create test fixtures in `examples/custom_agents/adk_research/tests/conftest.py`
  - Mock fixtures for ADK components (LlmAgent, ParallelAgent, SequentialAgent)
  - Mock for InMemoryRunner
  - Sample ADKAgentConfig fixture
  - Sample response fixtures
  - Sample error fixtures

- [x] T021 [P] [US3] Create model tests in `examples/custom_agents/adk_research/tests/test_models.py`
  - Test `ADKAgentConfig` validation (valid/invalid inputs)
  - Test `SearchResult` parsing
  - Test `ResearchReport` structure
  - Test Article 9 compliance (no defaults without explicit config)

- [x] T022 [US3] Create unit tests in `examples/custom_agents/adk_research/tests/test_agent.py`
  - Test `__init__` with valid config
  - Test `__init__` with missing config (should raise)
  - Test `execute()` success path (mocked ADK)
  - Test `execute()` error paths (AUTH_ERROR, RATE_LIMIT, TIMEOUT, etc.)
  - Test `_build_pipeline()` structure
  - Test `_parse_sources()` extraction
  - Test `_handle_error()` error code mapping
  - Target: 80% coverage (SC-005)

- [x] T023 [US3] Create E2E tests in `examples/custom_agents/adk_research/tests/test_e2e.py`
  - Mark with `@pytest.mark.e2e`
  - Test real Gemini API call (requires GOOGLE_API_KEY)
  - Test google_search tool execution
  - Test full pipeline execution
  - Verify response time (SC-001: 10s, SC-002: 30s)

- [x] T024 [US3] Create integration test for MixSeek-Core loader
  - Test TOML loading via dynamic loader
  - Verify agent instantiation from config
  - Verify `MemberAgentResult` compatibility (SC-007)

**Checkpoint**: User Story 3完了 - テストカバレッジ80%以上達成

---

## Phase 6: Polish & Documentation

**Purpose**: Documentation and final cleanup

- [x] T025 [P] Create `examples/custom_agents/adk_research/README.md`
  - Purpose and architecture overview
  - Prerequisites (GOOGLE_API_KEY, google-adk >= 1.19.0)
  - Quick start guide
  - Configuration reference (TOML options)
  - Error code reference
  - Testing instructions

- [x] T026 [P] Add type stubs/annotations review
  - Ensure all functions have type annotations
  - Run mypy strict mode
  - Fix any type errors

- [x] T027 Run code quality checks
  - `ruff check --fix examples/custom_agents/adk_research/`
  - `ruff format examples/custom_agents/adk_research/`
  - `mypy examples/custom_agents/adk_research/`

- [x] T028 Run full test suite and verify coverage
  - `pytest examples/custom_agents/adk_research/tests/ --cov`
  - Verify 80% coverage target

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (extends execute() method)
- **User Story 3 (Phase 5)**: Depends on User Stories 1 & 2 (tests implementation)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - MVP機能
- **User Story 2 (P2)**: Depends on US1 (extends the agent) - 高度なパイプライン
- **User Story 3 (P3)**: Depends on US1 & US2 (tests full implementation)

### Within Each User Story

- Models before services
- Helper methods before main execute()
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

Within Phase 2 (Foundational):
```bash
# These can run in parallel (different models in same file):
Task: T004 "Create ADKAgentConfig model"
Task: T005 "Create SearchResult model"
Task: T006 "Create ResearchReport model"
```

Within Phase 5 (Testing):
```bash
# These can run in parallel (different test files):
Task: T019 "Create tests/__init__.py"
Task: T020 "Create conftest.py"
Task: T021 "Create test_models.py"
```

Within Phase 6 (Polish):
```bash
# These can run in parallel:
Task: T025 "Create README.md"
Task: T026 "Add type stubs review"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test single search query
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP!
3. Add User Story 2 → Test Deep Research → Enhanced version
4. Add User Story 3 → Full test coverage → Production ready
5. Polish → Documentation complete

---

## FR to Task Mapping

| FR | Description | Tasks |
|----|-------------|-------|
| FR-001 | LlmAgent + google_search | T009, T010, T013 |
| FR-002 | Markdown要約 | T013 |
| FR-003 | Deep Research (ParallelAgent, SequentialAgent) | T015, T016, T017 |
| FR-004 | ソース情報metadata | T011, T013 |
| FR-005 | エラーハンドリング | T012, T013 |
| FR-006 | 構造化エラー情報 | T012 |
| FR-007 | TOML/環境変数設定 | T008 |
| FR-008 | BaseMemberAgent準拠 | T009 |
| FR-009 | テスト提供 | T019-T024 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Implementation location: `examples/custom_agents/adk_research/` のみ
- `src/mixseek/` への変更は行わない
- Latest ADK API only: `google.adk.agents`, `google.adk.tools`, `google.adk.runners`
- Default model: gemini-2.5-flash
- google-adk version: >= 1.19.0
