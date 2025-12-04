# Tasks: mixseekコマンド初期化機能

**Input**: Design documents from `/app/specs/005-command/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-interface.md

**Tests**: Article 3 (Test-First Imperative) requires TDD approach - tests are mandatory

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/mixseek/`, `tests/` at repository root
- Paths follow plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure: `src/mixseek/cli/`, `src/mixseek/config/`, `src/mixseek/utils/`, `tests/contract/`, `tests/integration/`, `tests/unit/`
- [X] T002 Initialize pyproject.toml with dependencies: typer>=0.9.0, pydantic>=2.0.0, tomli-w>=1.0.0
- [X] T003 [P] Configure ruff for linting and formatting in pyproject.toml (line-length=119, target-version=py312)
- [X] T004 [P] Configure mypy for type checking in pyproject.toml (strict mode, Python 3.12+)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create base Pydantic models foundation in src/mixseek/config/__init__.py (export mechanism)
- [X] T006 [P] Setup pytest configuration in pyproject.toml (markers: unit, integration, contract)
- [X] T007 [P] Create constants file in src/mixseek/config/constants.py (DEFAULT_PROJECT_NAME="mixseek-project", WORKSPACE_ENV_VAR="MIXSEEK_WORKSPACE")
- [X] T008 Create Typer app entry point in src/mixseek/cli/main.py with version info
- [X] T009 Setup logging configuration helpers in src/mixseek/utils/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - ワークスペースの初期化 (Priority: P1) 🎯 MVP

**Goal**: 環境変数またはCLIオプションでワークスペースパスを指定し、必要なディレクトリ構造（logs、configs、templates）とTOML設定ファイルを生成する

**Independent Test**: `mixseek init`コマンドを実行し、指定されたワークスペースディレクトリに必要なサブディレクトリと設定ファイルが正しく作成されることを確認

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Contract test for CLI exit codes in tests/contract/test_init_contract.py:31 (test_init_success_exit_code, test_init_error_exit_code, test_init_invalid_usage_exit_code)
- [X] T011 [P] [US1] Contract test for stdout/stderr format in tests/contract/test_init_contract.py:54 (test_success_output_format, test_error_output_format)
- [X] T012 [P] [US1] Contract test for CLI option priority in tests/contract/test_init_contract.py:72 (test_cli_option_overrides_env_var)
- [X] T013 [P] [US1] Integration test for workspace creation in tests/integration/test_init_integration.py:23 (test_init_creates_workspace_structure, test_init_generates_config_toml)
- [X] T014 [P] [US1] Integration test for environment variable handling in tests/integration/test_init_integration.py:45 (test_init_with_env_var, test_init_with_cli_option)
- [X] T015 [P] [US1] Integration test for existing workspace handling in tests/integration/test_init_integration.py:67 (test_init_existing_workspace_prompt, test_init_partial_workspace)
- [X] T016 [P] [US1] Integration test for error scenarios in tests/integration/test_init_integration.py:89 (test_init_parent_not_exists, test_init_no_write_permission, test_init_no_path_specified)
- [X] T017 [P] [US1] Integration test for special path cases in tests/integration/test_init_integration.py:112 (test_init_with_spaces_in_path, test_init_with_symlink, test_init_with_relative_path)

### Implementation for User Story 1

#### Data Models (Pydantic v2)

- [X] T018 [P] [US1] Create WorkspacePath model in src/mixseek/models/workspace.py:11 (Pydantic BaseModel with field_validator for raw_path, model_validator for permissions, factory methods from_cli/from_env)
- [X] T019 [P] [US1] Create WorkspaceStructure model in src/mixseek/models/workspace.py:81 (Pydantic BaseModel with field_validator for subdirectory validation, factory method create(), method create_directories())
- [X] T020 [P] [US1] Create ProjectConfig model in src/mixseek/models/config.py:11 (Pydantic BaseModel with field_validator for project_name and workspace_path, method to_toml_dict(), method save())
- [X] T021 [P] [US1] Create InitResult model in src/mixseek/models/result.py:11 (Pydantic BaseModel with factory methods success_result/error_result, method print_result())

#### Utilities

- [X] T022 [US1] Implement environment variable priority logic in src/mixseek/utils/env.py:12 (get_workspace_path function with priority: CLI > ENV > Error)
- [X] T023 [US1] Implement path validation utilities in src/mixseek/utils/filesystem.py:15 (validate_parent_exists, validate_write_permission, resolve_symlinks)
- [X] T024 [US1] Implement TOML template generation in src/mixseek/config/templates.py:18 (generate_sample_config function using tomli_w, includes comments and default values)

#### CLI Command Implementation

- [X] T025 [US1] Implement init command core logic in src/mixseek/cli/commands/init.py:23 (Typer command function with --workspace/-w option, error handling, workspace creation orchestration)
- [X] T026 [US1] Integrate init command into main CLI app in src/mixseek/cli/main.py:15 (register init command, setup exception handlers)
- [X] T027 [US1] Add user confirmation prompt for existing workspace in src/mixseek/cli/commands/init.py:156 (typer.confirm for overwrite scenario FR-016)
- [X] T028 [US1] Implement error handling and user-friendly messages in src/mixseek/cli/commands/init.py:178 (handle_error function mapping exceptions to stderr messages with solutions)

#### Validation & Logging

- [X] T029 [US1] Add validation for edge cases in src/mixseek/models/workspace.py:142 (disk space check, special characters in path, platform compatibility)
- [X] T030 [US1] Add logging for workspace operations in src/mixseek/cli/commands/init.py:203 (log path resolution, directory creation, config file generation)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. All 5 acceptance scenarios from spec.md should pass.

---

## Phase 4: User Story 2 - コマンドヘルプとバージョン情報の表示 (Priority: P2)

**Goal**: `--help`オプションで使用方法を表示し、`--version`オプションでバージョン情報を表示する

**Independent Test**: `mixseek --help`、`mixseek init --help`、`mixseek --version`コマンドを実行し、適切な情報が表示されることを確認

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL)

- [X] T031 [P] [US2] Contract test for global help in tests/contract/test_help_contract.py:12 (test_mixseek_help_displays_subcommands, test_mixseek_help_exit_code_zero)
- [X] T032 [P] [US2] Contract test for init help in tests/contract/test_help_contract.py:34 (test_mixseek_init_help_displays_options, test_mixseek_init_help_includes_examples)
- [X] T033 [P] [US2] Contract test for version display in tests/contract/test_version_contract.py:12 (test_mixseek_version_displays_number, test_mixseek_version_exit_code_zero)

### Implementation for User Story 2

- [X] T034 [P] [US2] Add version constant in src/mixseek/__init__.py:5 (__version__ = "0.1.0")
- [X] T035 [US2] Configure Typer help strings in src/mixseek/cli/main.py:23 (app description, rich_markup_mode, add_completion=False)
- [X] T036 [US2] Add detailed docstrings to init command in src/mixseek/cli/commands/init.py:28 (docstring with examples, option descriptions)
- [X] T037 [US2] Implement --version callback in src/mixseek/cli/main.py:45 (version_callback function with typer.Option)
- [X] T038 [US2] Add CLI usage examples to help text in src/mixseek/cli/commands/init.py:35 (Examples section in docstring matching contracts/cli-interface.md:152-155)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. All 3 acceptance scenarios from US2 should pass.

---

## Phase 5: User Story 3 - ワークスペースパスの省略形サポート (Priority: P3)

**Goal**: `-w`短縮オプションを`--workspace`のエイリアスとしてサポートする

**Independent Test**: `mixseek init -w /path/to/workspace`コマンドを実行し、`--workspace`オプションと同じ結果が得られることを確認

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL)

- [X] T039 [P] [US3] Contract test for short option equivalence in tests/contract/test_init_contract.py:145 (test_short_option_w_equivalent_to_long_workspace)
- [X] T040 [P] [US3] Integration test for short option with various paths in tests/integration/test_init_integration.py:234 (test_short_option_with_absolute_path, test_short_option_with_relative_path, test_short_option_with_spaces)

### Implementation for User Story 3

- [X] T041 [US3] Add short option alias in src/mixseek/cli/commands/init.py:30 (typer.Option with "--workspace", "-w")
- [X] T042 [US3] Update help documentation to mention short option in src/mixseek/cli/commands/init.py:32 (Update docstring to show both --workspace and -w in examples)

**Checkpoint**: All user stories should now be independently functional. All 1 acceptance scenario from US3 should pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T043 [P] Create quickstart.md validation script in tests/validation/test_quickstart.py:12 (Run all examples from quickstart.md as integration tests)
- [X] T044 [P] Add unit tests for utility functions in tests/unit/test_env.py:15 (test_get_workspace_path_priority, test_env_var_not_set_error)
- [X] T045 [P] Add unit tests for filesystem utilities in tests/unit/test_filesystem.py:18 (test_validate_parent_exists, test_validate_write_permission, test_resolve_symlinks)
- [X] T046 [P] Add unit tests for TOML template generation in tests/unit/test_templates.py:21 (test_generate_sample_config_structure, test_toml_includes_comments, test_placeholder_project_name)
- [X] T047 [P] Add unit tests for Pydantic models in tests/unit/test_models.py:24 (test_workspace_path_validators, test_project_config_validators, test_init_result_factory_methods)
- [X] T048 Code cleanup and refactoring: Remove duplicate validation logic, ensure DRY compliance (Article 10)
- [X] T049 Performance optimization: Ensure workspace creation completes within 5 seconds (SC-006)
- [X] T050 [P] Update README.md with installation and basic usage instructions in README.md:45
- [X] T051 [P] Add developer documentation in docs/developer-guide.md:12 (Architecture overview, extending the CLI, testing strategy)
- [X] T052 Security hardening: Validate all user inputs, sanitize paths, check for path traversal attacks
- [X] T053 Run mypy type checking across all source files (Article 16 compliance)
- [X] T054 Run ruff linting and formatting across all source files (Article 8 compliance)
- [X] T055 Verify all Success Criteria (SC-001 through SC-006) are met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1 but independently testable

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (Article 3)
2. Models before utilities
3. Utilities before CLI commands
4. Core implementation before edge cases
5. Story complete before moving to next priority

### Parallel Opportunities

#### Phase 1 (Setup)
- T003 and T004 can run in parallel

#### Phase 2 (Foundational)
- T006 and T007 can run in parallel after T005

#### Phase 3 (User Story 1)
- **All tests (T010-T017)** can run in parallel as they're in different files
- **All models (T018-T021)** can run in parallel as they're in different files
- T022, T023, T024 can run in parallel (different files)
- T027, T028, T029, T030 can run after T025 but some in parallel

#### Phase 4 (User Story 2)
- All tests (T031-T033) can run in parallel

#### Phase 5 (User Story 3)
- Tests T039 and T040 can run in parallel

#### Phase 6 (Polish)
- T043, T044, T045, T046, T047, T050, T051 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - these should FAIL initially):
Task T010: "Contract test for CLI exit codes in tests/contract/test_init_contract.py"
Task T011: "Contract test for stdout/stderr format in tests/contract/test_init_contract.py"
Task T012: "Contract test for CLI option priority in tests/contract/test_init_contract.py"
Task T013: "Integration test for workspace creation in tests/integration/test_init_integration.py"
Task T014: "Integration test for environment variable handling in tests/integration/test_init_integration.py"
Task T015: "Integration test for existing workspace handling in tests/integration/test_init_integration.py"
Task T016: "Integration test for error scenarios in tests/integration/test_init_integration.py"
Task T017: "Integration test for special path cases in tests/integration/test_init_integration.py"

# After tests exist and fail, launch all models for User Story 1 together:
Task T018: "Create WorkspacePath model in src/mixseek/models/workspace.py"
Task T019: "Create WorkspaceStructure model in src/mixseek/models/workspace.py"
Task T020: "Create ProjectConfig model in src/mixseek/models/config.py"
Task T021: "Create InitResult model in src/mixseek/models/result.py"

# Then launch all utilities together:
Task T022: "Implement environment variable priority logic in src/mixseek/utils/env.py"
Task T023: "Implement path validation utilities in src/mixseek/utils/filesystem.py"
Task T024: "Implement TOML template generation in src/mixseek/config/templates.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T009) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T010-T030)
   - Write ALL tests first (T010-T017) - ensure they FAIL
   - Implement models (T018-T021)
   - Implement utilities (T022-T024)
   - Implement CLI command (T025-T028)
   - Add validation and logging (T029-T030)
   - Verify tests now PASS
4. **STOP and VALIDATE**: Test User Story 1 independently against all 5 acceptance scenarios
5. Package and test installation with `pip install -e .`

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Package/Demo (MVP!)
3. Add User Story 2 → Test independently → Package/Demo
4. Add User Story 3 → Test independently → Package/Demo
5. Add Polish tasks → Final release
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T009)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T010-T030)
   - **Developer B**: User Story 2 (T031-T038) - can start tests while A is implementing
   - **Developer C**: User Story 3 (T039-T042) - can start tests while A/B are implementing
3. Stories complete and integrate independently
4. Team reconvenes for Polish phase

---

## MixSeek-Core Framework Compliance

Per Article 14 (SpecKit Framework Consistency), this implementation must align with `specs/001-specs/spec.md`:

### Compliance Checks

- **MixSeek-Core FR-021 (PyPI Distribution)**: ✅ Tasks T001-T002 include pyproject.toml setup for pip installation
- **CLI Interface Mandate (Article 2)**: ✅ User Stories 1-3 provide CLI interface with text input/output
- **Library-First Principle (Article 1)**: ✅ Tasks T018-T024 implement library functionality before CLI wrapper
- **Test-First Imperative (Article 3)**: ✅ All test tasks (T010-T017, T031-T033, T039-T040) precede implementation
- **Type Checking (Article 16)**: ✅ Tasks T004, T053 enforce mypy strict mode
- **MixSeek Integration Point**: This init command will be used by future `mixseek execute` command to initialize workspace before running multi-agent framework

### Future Integration

The workspace structure created by this feature will be used by:
- **Leader Agent**: Will read configs/config.toml for project settings
- **Member Agents**: Will access logs/ and templates/ directories
- **Orchestration Layer**: Will use workspace as base directory for all operations

---

## Notes

- **[P] tasks** = different files, no dependencies
- **[Story] label** maps task to specific user story for traceability
- **Line numbers** in descriptions indicate where code should be added (approximate)
- Each user story should be independently completable and testable
- **TDD Required**: Verify tests FAIL before implementing (Article 3)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Constitution Compliance**: Article 3 (Test-First), Article 8 (Code Quality), Article 16 (Type Checking)
- **Success Criteria**: All tasks support SC-001 through SC-006 from spec.md

