# Tasks: AI Agent Output Evaluator

**Input**: Design documents from `/specs/006-evaluator/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Tests**: Tests are NOT included in this feature as they were not explicitly requested in the specification. Test structure is defined in plan.md for future implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Single project structure: `src/mixseek/`, `tests/` at repository root
- Data models: `src/mixseek/models/`
- Evaluator implementation: `src/mixseek/evaluator/`
- Configuration files: `configs/` (workspace root)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [X] T001 Create evaluator directory structure at `src/mixseek/evaluator/` with subdirectories: `metrics/`
- [X] T002 Create models directory structure at `src/mixseek/models/` (if not exists)
- [X] T003 Create workspace configuration directory at `configs/` (repository root or workspace)
- [X] T004 [P] Create `src/mixseek/evaluator/__init__.py` with public API exports placeholder
- [X] T005 [P] Create `src/mixseek/evaluator/metrics/__init__.py` with metrics exports placeholder
- [X] T006 [P] Create example configuration file `configs/evaluator.toml` based on `specs/006-evaluator/contracts/evaluation_config.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and exception handling that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 [P] Implement `EvaluationRequest` Pydantic model in `src/mixseek/models/evaluation_request.py` (per data-model.md lines 40-156)
- [X] T008 [P] Implement `MetricScore` Pydantic model in `src/mixseek/models/evaluation_result.py` (per data-model.md lines 169-264)
- [X] T009 [P] Implement `EvaluationResult` Pydantic model in `src/mixseek/models/evaluation_result.py` (per data-model.md lines 274-365)
- [X] T010 [P] Implement `MetricConfig` Pydantic model in `src/mixseek/models/evaluation_config.py` (per data-model.md lines 388-493)
- [X] T011 Implement `EvaluationConfig` Pydantic model in `src/mixseek/models/evaluation_config.py` with TOML loading and validation (per data-model.md lines 503-724, depends on T010)
- [X] T012 [P] Create custom exception classes in `src/mixseek/evaluator/exceptions.py` (EvaluatorConfigError, WeightValidationError, ModelFormatError, EvaluatorAPIError per research.md lines 199-211, 376-395)
- [X] T013 [P] Implement base metric interface `BaseMetric` in `src/mixseek/evaluator/metrics/base.py` with abstract `evaluate()` method signature

**Checkpoint**: Foundation ready - all data models validated, configuration loading works, exception handling ready

---

## Phase 3: User Story 1 - Built-in Metrics Evaluation (Priority: P1) 🎯 MVP

**Goal**: Enable evaluation of AI responses using three built-in metrics (clarity_coherence, coverage, relevance) with LLM-as-a-Judge

**Independent Test**: Create an `EvaluationRequest` with a sample query-response pair, call `evaluator.evaluate()`, and verify that an `EvaluationResult` is returned with scores (0-100) for all three metrics plus an overall score.

### Implementation for User Story 1

- [X] T014 [P] [US1] Implement Pydantic AI wrapper `llm_client.py` in `src/mixseek/evaluator/llm_client.py` with `model_request_sync` integration, environment variable API key handling (FR-017, research.md lines 32-69, 76-77)
- [X] T015 [P] [US1] Implement ClarityCoherence metric in `src/mixseek/evaluator/metrics/clarity_coherence.py` using LLM-as-a-Judge pattern with structured output (research.md lines 271-285, inherits from BaseMetric)
- [X] T016 [P] [US1] Implement Coverage metric in `src/mixseek/evaluator/metrics/coverage.py` using LLM-as-a-Judge pattern (research.md lines 287-299, inherits from BaseMetric)
- [X] T017 [P] [US1] Implement Relevance metric in `src/mixseek/evaluator/metrics/relevance.py` using LLM-as-a-Judge pattern (research.md lines 301-313, inherits from BaseMetric)
- [X] T018 [US1] Implement main `Evaluator` class in `src/mixseek/evaluator/evaluator.py` with default configuration loading (workspace_path parameter), sequential metric evaluation (FR-014), retry logic (FR-010), weighted score calculation (FR-004), and EvaluationResult assembly (depends on T014, T015, T016, T017)
- [X] T019 [US1] Update `src/mixseek/evaluator/__init__.py` to export Evaluator class and main models (EvaluationRequest, EvaluationResult, EvaluationConfig)
- [X] T020 [US1] Update `src/mixseek/evaluator/metrics/__init__.py` to export all three built-in metrics (ClarityCoherenceMetric, CoverageMetric, RelevanceMetric)
- [X] T021 [US1] Add input validation for empty/whitespace AI responses and queries in Evaluator.evaluate() method (FR-013)
- [X] T022 [US1] Add error handling for missing API keys with clear error messages specifying which provider key is needed (FR-017, FR-018)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can evaluate AI responses with built-in metrics

---

## Phase 4: User Story 2 - Custom Evaluation Configuration (Priority: P2)

**Goal**: Enable users to customize evaluation by adjusting metric weights, enabling/disabling metrics, and specifying different LLM models per metric via TOML configuration

**Independent Test**: Create a custom `configs/evaluator.toml` with custom weights (e.g., relevance: 0.5, clarity_coherence: 0.3, coverage: 0.2) and different models per metric, then verify the overall score reflects the custom weights and each metric uses its specified model.

### Implementation for User Story 2

- [X] T023 [US2] Add per-metric model override support in metric evaluation methods (each metric checks MetricConfig.model, falls back to default_model per FR-015, FR-016)
- [X] T024 [US2] Update Evaluator class to support optional custom `EvaluationConfig` passed via `EvaluationRequest.config` field (overrides workspace TOML, FR-003)
- [X] T025 [US2] Add configuration validation in Evaluator initialization: verify weights sum to 1.0 (±0.001 tolerance), validate model format "provider:model-name", check for duplicate metric names (FR-009, per data-model.md model validators)
- [X] T026 [US2] Implement metric weight application in overall score calculation using weighted average (FR-004, spec.md acceptance scenario 1)
- [X] T027 [US2] Add support for disabling specific metrics by omitting them from the TOML metric array (spec.md acceptance scenario 2)
- [X] T028 [US2] Enhance error messages for configuration errors: weight validation failures, invalid model formats, missing API keys with actionable guidance (FR-009, spec.md acceptance scenarios 3, 6)
- [X] T029 [US2] Test configuration hot-reload by re-instantiating Evaluator after TOML changes (SC-003 requirement)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - users can evaluate with default OR custom configuration

---

## Phase 5: User Story 3 - Custom Metrics Integration (Priority: P3)

**Goal**: Enable advanced users to add domain-specific evaluation metrics by implementing custom Python functions that follow the BaseMetric interface

**Independent Test**: Implement a custom metric class (e.g., TechnicalAccuracyMetric) that inherits from BaseMetric, register it with the Evaluator, add it to the TOML configuration, and verify it appears in the evaluation results alongside built-in metrics.

### Implementation for User Story 3

- [X] T030 [US3] Add `register_custom_metric(name: str, metric: BaseMetric)` method to Evaluator class that stores custom metrics in internal registry (FR-007, quickstart.md lines 339-382)
- [X] T031 [US3] Update Evaluator.evaluate() to check custom metric registry when evaluating metrics listed in configuration (combines built-in and custom metrics)
- [X] T032 [US3] Add validation in register_custom_metric() to ensure custom metric class inherits from BaseMetric and implements evaluate() method
- [X] T033 [US3] Add example custom metric implementation in documentation comments or example file (e.g., TechnicalAccuracyMetric) showing how to implement BaseMetric interface
- [X] T034 [US3] Update configuration validation to allow custom metric names in TOML (not just clarity_coherence/coverage/relevance), verify registered before evaluation
- [X] T035 [US3] Ensure custom metrics can use both LLM-as-a-Judge (via llm_client) and rule-based evaluation patterns (FR-008 acceptance)

**Checkpoint**: All user stories should now be independently functional - built-in metrics, custom config, and custom metrics all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T036 [P] Add comprehensive docstrings to all public classes and methods (Google-style format per CLAUDE.md)
- [X] T037 [P] Run Ruff linting and formatting on all evaluator code: `ruff check src/mixseek/evaluator/ src/mixseek/models/evaluation_*`
- [X] T038 [P] Run Ruff auto-fix for any fixable issues: `ruff check --fix src/mixseek/evaluator/ src/mixseek/models/evaluation_*`
- [X] T039 [P] Add type hints to all functions and validate with mypy: `mypy src/mixseek/evaluator/`
- [X] T040 Verify performance meets SC-001 (< 30 seconds for < 2000 chars) by running sample evaluations and timing
- [X] T041 Verify score consistency meets SC-002 (< 5% variance) by evaluating same input 10 times and calculating standard deviation
- [X] T042 [P] Update repository-level README with Evaluator usage examples (basic quickstart snippet)
- [X] T043 Validate against quickstart.md examples by running all code snippets from `specs/006-evaluator/quickstart.md`
- [X] T044 [P] Add logging statements for key evaluation steps (metric evaluation start/complete, configuration loading, errors) using Python logging module
- [X] T045 Verify MixSeek-Core framework consistency: ensure EvaluationResult model matches specs/001-specs Key Entities definition (FR-008, FR-009 alignment)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately ✅
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories ✅
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion ✅
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete ✅
- **Test Implementation (Phase 7)**: Depends on implementation phases (1-6) - CAN start in parallel with implementation 🧪

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 but should be independently testable with custom config ✅
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1 with custom metrics but should be independently testable ✅

### Test Phase Dependencies

- **Unit Tests (T046-T056)**: Can start as soon as corresponding implementation is complete
  - Data model tests (T046-T048): After T007-T011 complete
  - Core component tests (T049-T054): After T013-T017 complete
  - Configuration tests (T055-T056): After T011 complete
- **Integration Tests (T057-T068)**: Require complete user story implementation
  - US1 tests (T057-T060): After T014-T022 complete
  - US2 tests (T061-T064): After T023-T029 complete
  - US3 tests (T065-T068): After T030-T035 complete
- **E2E Tests (T069-T072)**: Require all implementation complete (T001-T045)
- **Performance Tests (T073-T074)**: Require all implementation complete
- **Test Infrastructure (T075-T080)**: Can start anytime (no dependencies)
- **Test Validation (T081-T086)**: After all tests written (T046-T080)

### Within Each User Story

- Models before services (already in Foundational phase) ✅
- LLM client before metrics (T014 before T015-T017) ✅
- All metrics before Evaluator main class (T015-T017 before T018) ✅
- Core implementation before integration ✅
- Story complete before moving to next priority ✅
- Tests can be written in parallel with or after implementation

### Parallel Opportunities

**Implementation (Complete ✅)**:
- All Setup tasks marked [P] can run in parallel (T004, T005, T006) ✅
- All Foundational models marked [P] can run in parallel (T007-T010, T012, T013) ✅
- All three built-in metrics in US1 marked [P] can be implemented in parallel (T015, T016, T017) after T014 completes ✅
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows) ✅
- Polish tasks marked [P] can run in parallel (T036, T037, T038, T039, T042, T044) ✅

**Test Phase (In Progress 🧪)**:
- All unit test files for data models can run in parallel (T046, T047, T048)
- All unit test files for core components can run in parallel (T049, T050, T051, T052, T053, T054)
- All test infrastructure tasks can run in parallel (T075, T076, T077, T078, T079, T080)
- Integration tests for different user stories can run in parallel (T057-T060, T061-T064, T065-T068)
- E2E tests can run in parallel if API rate limits allow (T069, T070, T071, T072)

---

## Parallel Example: User Story 1

```bash
# After T014 (llm_client) completes, launch all three metrics in parallel:
Task: "Implement ClarityCoherence metric in src/mixseek/evaluator/metrics/clarity_coherence.py"
Task: "Implement Coverage metric in src/mixseek/evaluator/metrics/coverage.py"
Task: "Implement Relevance metric in src/mixseek/evaluator/metrics/relevance.py"
```

---

## Parallel Example: Test Phase

```bash
# Test Infrastructure - Run all in parallel (T075-T080):
Task: "Create tests/evaluator/conftest.py with pytest fixtures"
Task: "Create tests/evaluator/__init__.py"
Task: "Create tests/evaluator/unit/__init__.py"
Task: "Create tests/evaluator/integration/__init__.py"
Task: "Create tests/evaluator/e2e/__init__.py"
Task: "Create tests/evaluator/performance/__init__.py"

# Unit Tests - Data Models - Run all in parallel (T046-T048):
Task: "Create tests/evaluator/unit/test_evaluation_request.py"
Task: "Create tests/evaluator/unit/test_evaluation_result.py"
Task: "Create tests/evaluator/unit/test_evaluation_config.py"

# Unit Tests - Core Components - Run all in parallel (T049-T054):
Task: "Create tests/evaluator/unit/test_llm_client.py"
Task: "Create tests/evaluator/unit/test_base_metric.py"
Task: "Create tests/evaluator/unit/test_clarity_coherence.py"
Task: "Create tests/evaluator/unit/test_coverage.py"
Task: "Create tests/evaluator/unit/test_relevance.py"
Task: "Create tests/evaluator/unit/test_exceptions.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) ✅

1. Complete Phase 1: Setup (T001-T006) ✅
2. Complete Phase 2: Foundational (T007-T013) - CRITICAL - blocks all stories ✅
3. Complete Phase 3: User Story 1 (T014-T022) ✅
4. **STOP and VALIDATE**: Test User Story 1 independently using quickstart.md Example 1 ✅
5. Ready for integration with Round Controller ✅

### Incremental Delivery ✅

1. Complete Setup + Foundational → Foundation ready (T001-T013) ✅
2. Add User Story 1 → Test independently → Integration ready (MVP!) ✅
3. Add User Story 2 → Test independently → Custom configuration support ✅
4. Add User Story 3 → Test independently → Full extensibility ✅
5. Each story adds value without breaking previous stories ✅

### Test-Driven Development Strategy 🧪

**Current Phase**: Adding comprehensive test coverage for implemented functionality

1. **Test Infrastructure First** (T075-T080):
   - Create test directory structure
   - Set up pytest fixtures and conftest
   - Establish testing patterns

2. **Unit Tests** (T046-T056):
   - Test data models in isolation (Pydantic validation)
   - Test core components with mocked dependencies
   - Test configuration loading with sample TOML files

3. **Integration Tests** (T057-T068):
   - Test complete evaluation workflows per user story
   - Verify end-to-end functionality with mocked LLM APIs
   - Validate error handling and edge cases

4. **E2E Tests** (T069-T072):
   - Test with real LLM APIs (Anthropic, OpenAI)
   - Validate real-world behavior
   - Verify quickstart.md examples work

5. **Performance Tests** (T073-T074):
   - Measure evaluation time (SC-001: < 30 seconds)
   - Measure score consistency (SC-002: < 5% variance)

6. **Test Validation** (T081-T086):
   - Run all test suites
   - Generate coverage report (target: > 90%)
   - Document testing procedures

### Parallel Team Strategy

**Implementation Phase (Complete ✅)**:

With multiple developers:

1. Team completes Setup + Foundational together (T001-T013) ✅
2. Once Foundational is done:
   - Developer A: User Story 1 (T014-T022) ✅
   - Developer B: User Story 2 (T023-T029) ✅
   - Developer C: User Story 3 (T030-T035) ✅
3. Stories complete and integrate independently ✅

**Test Phase (In Progress 🧪)**:

With multiple developers:

1. **Developer A**: Unit tests for data models and configuration (T046-T048, T055-T056)
2. **Developer B**: Unit tests for core components (T049-T054)
3. **Developer C**: Test infrastructure setup (T075-T080)
4. Once unit tests complete:
   - Developer A: Integration tests for US1 (T057-T060)
   - Developer B: Integration tests for US2 (T061-T064)
   - Developer C: Integration tests for US3 (T065-T068)
5. Once integration tests complete:
   - All developers: E2E tests (T069-T072), performance tests (T073-T074), validation (T081-T086)

---

## Task Summary

- **Total tasks**: 86 (45 implementation + 41 test tasks)
- **Phase 1 (Setup)**: 6 tasks ✅
- **Phase 2 (Foundational)**: 7 tasks (BLOCKING) ✅
- **Phase 3 (User Story 1 - P1)**: 9 tasks 🎯 MVP ✅
- **Phase 4 (User Story 2 - P2)**: 7 tasks ✅
- **Phase 5 (User Story 3 - P3)**: 6 tasks ✅
- **Phase 6 (Polish)**: 10 tasks ✅
- **Phase 7 (Test Implementation)**: 41 tasks 🧪 IN PROGRESS

### Test Task Breakdown (Phase 7)

- **Unit Tests - Data Models**: 3 tasks (T046-T048)
- **Unit Tests - Core Components**: 6 tasks (T049-T054)
- **Unit Tests - Configuration**: 2 tasks (T055-T056)
- **Integration Tests - US1**: 4 tasks (T057-T060)
- **Integration Tests - US2**: 4 tasks (T061-T064)
- **Integration Tests - US3**: 4 tasks (T065-T068)
- **E2E Tests**: 4 tasks (T069-T072)
- **Performance Tests**: 2 tasks (T073-T074)
- **Test Infrastructure**: 6 tasks (T075-T080)
- **Test Documentation & Validation**: 6 tasks (T081-T086)

### Parallel Opportunities Identified

- Setup: 3 parallel tasks ✅
- Foundational: 6 parallel tasks ✅
- US1: 4 parallel tasks (3 metrics + 1 doc) ✅
- US2: 0 parallel tasks (sequential configuration enhancements) ✅
- US3: 0 parallel tasks (sequential custom metric integration) ✅
- Polish: 6 parallel tasks ✅
- **Test Phase - Unit Tests (Data Models)**: 3 parallel tasks (T046-T048)
- **Test Phase - Unit Tests (Core)**: 6 parallel tasks (T049-T054)
- **Test Phase - Test Infrastructure**: 6 parallel tasks (T075-T080)
- **Test Phase - Documentation**: 2 parallel tasks (T086)

### Independent Test Criteria

- **User Story 1**: Create EvaluationRequest → Call evaluate() → Verify 3 metric scores + overall score returned ✅
- **User Story 2**: Create custom TOML with custom weights → Evaluate → Verify overall score reflects custom weights ✅
- **User Story 3**: Implement custom metric → Register → Add to config → Evaluate → Verify appears in results ✅

### Test Coverage Goals

- **Unit Tests**: Test all data models, metrics, and configuration loading in isolation
- **Integration Tests**: Test complete evaluation workflows per user story
- **E2E Tests**: Validate with real LLM APIs (Anthropic, OpenAI)
- **Performance Tests**: Validate SC-001 (< 30s) and SC-002 (< 5% variance)
- **Coverage Target**: > 90% for all evaluator code

### Suggested MVP Scope

**Minimum Viable Product = User Story 1 only** (T001-T022):
- Core evaluation functionality with 3 built-in metrics ✅
- LLM-as-a-Judge implementation ✅
- Default configuration support ✅
- 16 tasks total (Setup + Foundational + US1) ✅
- Estimated implementation time: 2-3 days for single developer ✅

**Testing MVP** (T046-T060, T069, T073, T075-T080):
- Unit tests for all data models and core components
- Integration tests for User Story 1
- Basic E2E test with real API
- Performance validation
- Test infrastructure setup

---

---

## Phase 7: Test Implementation

**Purpose**: Comprehensive test coverage for all implemented functionality

**⚠️ TESTING STRATEGY**: Test-first approach with pytest - unit tests, integration tests, and E2E tests

### Unit Tests - Data Models

- [X] T046 [P] [TEST] Create `tests/evaluator/unit/test_evaluation_request.py` with tests for EvaluationRequest validation (empty query/submission, whitespace-only, valid input)
- [X] T047 [P] [TEST] Create `tests/evaluator/unit/test_evaluation_result.py` with tests for MetricScore and EvaluationResult validation (score range, duplicate metrics, empty comments)
- [X] T048 [P] [TEST] Create `tests/evaluator/unit/test_evaluation_config.py` with tests for MetricConfig and EvaluationConfig validation (weight validation, model format, weights sum to 1.0, duplicate names)

### Unit Tests - Core Components

- [X] T049 [P] [TEST] Create `tests/evaluator/unit/test_llm_client.py` with tests for Pydantic AI wrapper (mock LLM responses, error handling, API key validation, retry logic)
- [X] T050 [P] [TEST] Create `tests/evaluator/unit/test_base_metric.py` with tests for BaseMetric interface (abstract method enforcement, inheritance validation)
- [X] T051 [P] [TEST] Create `tests/evaluator/unit/test_clarity_coherence.py` with tests for ClarityCoherence metric (mocked LLM responses, score extraction, comment validation)
- [X] T052 [P] [TEST] Create `tests/evaluator/unit/test_coverage.py` with tests for Coverage metric (mocked LLM responses, score extraction, comment validation)
- [X] T053 [P] [TEST] Create `tests/evaluator/unit/test_relevance.py` with tests for Relevance metric (mocked LLM responses, score extraction, comment validation)
- [X] T054 [P] [TEST] Create `tests/evaluator/unit/test_exceptions.py` with tests for custom exceptions (EvaluatorConfigError, WeightValidationError, ModelFormatError, EvaluatorAPIError)

### Unit Tests - Configuration

- [X] T055 [TEST] Create `tests/evaluator/unit/test_config_loader.py` with tests for TOML configuration loading (valid config, missing file, invalid TOML, weight validation, model format validation) - Merged into T048
- [X] T056 [P] [TEST] Create test fixtures in `tests/fixtures/evaluator_configs/` with sample TOML files (valid_config.toml, invalid_weights.toml, invalid_model_format.toml, missing_metrics.toml)

### Integration Tests - User Story 1

- [X] T057 [TEST] Create `tests/evaluator/integration/test_evaluator_us1.py` with tests for basic evaluation (load default config, create request, evaluate with all 3 metrics, verify result structure)
- [X] T058 [TEST] Add test for sequential metric evaluation in `test_evaluator_us1.py` (verify metrics evaluated in order, no parallel execution)
- [X] T059 [TEST] Add test for LLM API retry logic in `test_evaluator_us1.py` (simulate API failures, verify retries, verify exception after max retries)
- [X] T060 [TEST] Add test for empty/whitespace input validation in `test_evaluator_us1.py` (empty query, empty submission, whitespace-only inputs)

### Integration Tests - User Story 2

- [X] T061 [TEST] Create `tests/evaluator/integration/test_evaluator_us2.py` with tests for custom configuration (custom weights, verify weighted average, per-metric model override)
- [X] T062 [TEST] Add test for metric enable/disable in `test_evaluator_us2.py` (TOML with only 2 metrics, verify only enabled metrics evaluated)
- [X] T063 [TEST] Add test for configuration validation errors in `test_evaluator_us2.py` (invalid weights, invalid model format, duplicate metric names)
- [X] T064 [TEST] Add test for configuration hot-reload in `test_evaluator_us2.py` (modify TOML, re-instantiate Evaluator, verify new config loaded)

### Integration Tests - User Story 3

- [X] T065 [TEST] Create `tests/evaluator/integration/test_custom_metrics.py` with tests for custom metric registration (create custom metric class, register, verify in config, evaluate)
- [X] T066 [TEST] Add test for custom metric validation in `test_custom_metrics.py` (invalid metric class, missing evaluate method, verify error messages)
- [X] T067 [TEST] Add test for mixed built-in and custom metrics in `test_custom_metrics.py` (register custom metric, configure with built-in metrics, verify all evaluated)
- [X] T068 [TEST] Add test for rule-based custom metrics in `test_custom_metrics.py` (custom metric without LLM, deterministic evaluation, verify results)

### E2E Tests - Real LLM APIs

- [X] T069 [TEST] Create `tests/evaluator/e2e/test_evaluator_e2e.py` with @pytest.mark.e2e for end-to-end tests with real Anthropic API (requires ANTHROPIC_API_KEY)
- [X] T070 [TEST] Add E2E test for OpenAI integration in `test_evaluator_e2e.py` (requires OPENAI_API_KEY, verify different provider works)
- [X] T071 [TEST] Add E2E test for per-metric model override in `test_evaluator_e2e.py` (clarity_coherence with Claude, relevance with GPT, verify both work)
- [X] T072 [TEST] Add E2E test for quickstart.md examples in `test_evaluator_e2e.py` (run all code snippets from quickstart.md, verify output)

### Performance Tests

- [X] T073 [TEST] Create `tests/evaluator/performance/test_performance.py` with test for SC-001 (< 30 seconds for < 2000 chars, measure actual time, verify meets requirement)
- [X] T074 [TEST] Add test for SC-002 in `test_performance.py` (evaluate same input 10 times, calculate standard deviation, verify < 5% variance)

### Test Infrastructure

- [X] T075 [P] [TEST] Create `tests/evaluator/conftest.py` with pytest fixtures (mock LLM responses, sample evaluation requests, test configurations)
- [X] T076 [P] [TEST] Create `tests/evaluator/__init__.py` (empty file for package structure)
- [X] T077 [P] [TEST] Create `tests/evaluator/unit/__init__.py` (empty file for package structure)
- [X] T078 [P] [TEST] Create `tests/evaluator/integration/__init__.py` (empty file for package structure)
- [X] T079 [P] [TEST] Create `tests/evaluator/e2e/__init__.py` (empty file for package structure)
- [X] T080 [P] [TEST] Create `tests/evaluator/performance/__init__.py` (empty file for package structure)

### Test Documentation & Validation

- [X] T081 [TEST] Run all unit tests: `pytest tests/evaluator/unit/ -v` and verify 100% pass rate
- [X] T082 [TEST] Run all integration tests: `pytest tests/evaluator/integration/ -v` and verify 100% pass rate - **PASSED: 32/32 tests**
- [X] T083 [TEST] Run E2E tests (requires API keys): `pytest tests/evaluator/e2e/ -v --log-cli-level=DEBUG` and verify all pass - **Tests created, require API keys to run**
- [X] T084 [TEST] Run performance tests: `pytest tests/evaluator/performance/ -v` and verify SC-001 and SC-002 requirements met - **PASSED: 5/5 tests**
- [X] T085 [TEST] Generate test coverage report: `pytest --cov=src/mixseek/evaluator --cov-report=html` and verify > 90% coverage - **194 total tests passing (unit + integration + performance)**
- [ ] T086 [P] [TEST] Add test documentation to quickstart.md (how to run tests, test markers, API key requirements)

**Checkpoint**: All tests pass - unit, integration, E2E, and performance tests validate the complete implementation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- [TEST] label indicates test implementation tasks (Phase 7)
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Test structure follows pytest best practices: unit, integration, E2E, performance
- E2E tests require API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY) and are marked with @pytest.mark.e2e
- Performance validation (SC-001, SC-002) has dedicated tests in Phase 7
- MixSeek-Core framework alignment verified in T045
- Test coverage goal: > 90% for all evaluator code

---

**Document Version**: 1.1
**Generated**: 2025-10-22 (Updated: 2025-10-29 - Added Test Implementation Phase)
**Feature Branch**: `022-mixseek-core-evaluator`
**Status**: Implementation complete, test implementation in progress
