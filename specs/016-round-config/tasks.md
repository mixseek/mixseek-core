# Implementation Tasks: Round Configuration in TOML

**Feature**: 101-round-config
**Branch**: `feature/101-round-config`
**Generated**: 2025-11-18
**Status**: In Progress (T001-T007 Complete, Testing Phase)

## Overview

本ドキュメントは、Feature 101-round-config（ラウンド設定のTOML対応）の実装タスクを定義する。Article 3（Test-First Imperative）に従い、すべてのテストを実装前に作成し、ユーザー承認を得た後にRedフェーズを確認してから実装を進める。

**User Stories**:
- **US1** (P1): TOMLファイルによる設定
- **US2** (P2): 環境変数による上書き
- **US3** (P1): バリデーションとエラー処理

**Implementation Strategy**: TDD（Test-Driven Development）アプローチを採用。各ユーザーストーリーは独立してテスト可能な単位として実装される。

## Phase 1: Setup & Prerequisites

*Note: Prerequisite tasks that must complete before any user story implementation*

### T001 [Setup] Verify existing infrastructure

**File**: `src/mixseek/config/schema.py`, `src/mixseek/orchestrator/models.py`
**Story**: Foundation
**Type**: Verification
**Estimated Time**: 15 minutes

**Description**:
既存のOrchestratorSettingsとOrchestratorTaskモデルの実装を確認し、ラウンド設定フィールドの追加箇所を特定する。

**Acceptance Criteria**:
- OrchestratorSettings（src/mixseek/config/schema.py:523-580）の構造を理解
- OrchestratorTask（src/mixseek/orchestrator/models.py:14-50）の既存ラウンド設定フィールドを確認
- Pydantic Settings設定（env_prefix、validate_default等）を確認

**Dependencies**: None

---

### T002 [Setup] Create test file structure

**Files**: `tests/config/test_orchestrator_settings.py` (new)
**Story**: Foundation
**Type**: Setup
**Estimated Time**: 10 minutes

**Description**:
ラウンド設定のユニットテストファイルを作成する。

**Acceptance Criteria**:
- `tests/config/test_orchestrator_settings.py`ファイルが作成される
- 必要なimport文（pytest、pydantic、ConfigurationManager）が含まれる
- テスト用のfixture（temporary workspace、mock TOML files）が定義される

**Dependencies**: None

**Parallel**: ✅ Can run in parallel with T001

---

## Phase 2: User Story 1 - TOMLファイルによる設定 (P1)

*Goal: システム運用者がorchestrator.tomlでラウンド実行パラメータを設定できるようにする*

**Independent Test**: カスタムラウンド設定を含むorchestrator.tomlを作成し、`mixseek exec`コマンドを実行し、ラウンドコントローラーがハードコードされたデフォルト値ではなく設定値を使用することを確認する。

### T003 [US1][Test] Write unit tests for OrchestratorSettings field validation

**File**: `tests/config/test_orchestrator_settings.py`
**Story**: US1
**Type**: Test (TDD Red Phase)
**Estimated Time**: 45 minutes

**Description**:
OrchestratorSettingsの新規ラウンド設定フィールド（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）のバリデーションテストを作成する。

**Test Cases**:
1. **test_default_round_configuration**: デフォルト値が正しく設定されることを確認
   - max_rounds = 5
   - min_rounds = 2
   - submission_timeout_seconds = 300
   - judgment_timeout_seconds = 60

2. **test_max_rounds_constraints**: max_roundsの制約を検証
   - 有効範囲: 1 ≤ max_rounds ≤ 10
   - 範囲外の値（0、11）でValidationErrorが発生

3. **test_min_rounds_constraints**: min_roundsの制約を検証
   - 有効範囲: min_rounds ≥ 1
   - 範囲外の値（0、-1）でValidationErrorが発生

4. **test_timeout_constraints**: タイムアウトフィールドの制約を検証
   - submission_timeout_seconds > 0
   - judgment_timeout_seconds > 0
   - 負の値、0でValidationErrorが発生

5. **test_toml_file_loading**: orchestrator.tomlからのラウンド設定読み込みを検証
   - カスタムTOMLファイル（max_rounds=10等）を作成
   - ConfigurationManagerで読み込み
   - 設定値が正しく反映されることを確認

**Acceptance Criteria**:
- すべてのテストケースが記述される
- テストは失敗する（Redフェーズ - 実装前）
- テストコードはPEP 8、ruff、mypyに準拠

**Dependencies**: T002

---

### T004 [US1][Test][Checkpoint] User approval for US1 tests

**File**: N/A (Approval Process)
**Story**: US1
**Type**: Gate
**Estimated Time**: Review time

**Description**:
T003で作成したテストをユーザーに提示し、承認を得る。Article 3（Test-First Imperative）の必須要件。

**Acceptance Criteria**:
- テストがユーザーに提示される
- ユーザーがテストの妥当性を確認し、承認する
- テストが失敗することが確認される（Redフェーズ）

**Dependencies**: T003

**🚨 GATE**: This checkpoint must pass before proceeding to T005

---

### T005 [US1][Impl] Add round configuration fields to OrchestratorSettings

**File**: `src/mixseek/config/schema.py`
**Story**: US1
**Type**: Implementation (TDD Green Phase)
**Estimated Time**: 30 minutes

**Description**:
OrchestratorSettingsクラスに4つのラウンド設定フィールドを追加する。

**Implementation Steps**:
1. `src/mixseek/config/schema.py:523-580`のOrchestratorSettingsクラスを編集
2. 以下のフィールドを追加:
   ```python
   max_rounds: int = Field(
       default=5,
       ge=1,
       le=10,
       description="Maximum number of rounds per team (matches OrchestratorTask default)",
   )

   min_rounds: int = Field(
       default=2,
       ge=1,
       description="Minimum number of rounds before LLM-based judgment (matches OrchestratorTask default)",
   )

   submission_timeout_seconds: int = Field(
       default=300,
       gt=0,
       description="Timeout for team submission in each round (seconds, matches OrchestratorTask default)",
   )

   judgment_timeout_seconds: int = Field(
       default=60,
       gt=0,
       description="Timeout for evaluation judgment in each round (seconds, matches OrchestratorTask default)",
   )
   ```

**Acceptance Criteria**:
- 4つのフィールドがOrchestratorSettingsに追加される
- Pydantic Field制約（ge、le、gt）が正しく定義される
- デフォルト値がOrchestratorTaskと一致する
- T003のテストが通過する（Greenフェーズ）

**Dependencies**: T004 (Gate: User approval)

---

### T006 [US1][Test] Write integration tests for Orchestrator config pass-through

**File**: `tests/orchestrator/test_orchestrator.py`
**Story**: US1
**Type**: Test
**Estimated Time**: 30 minutes

**Description**:
OrchestratorクラスがOrchestratorSettingsからOrchestratorTaskへラウンド設定を正しく渡すことを確認する統合テストを作成する。

**Test Cases**:
1. **test_round_config_passthrough_with_toml**: TOML設定がOrchestratorTaskに反映されることを確認
   - orchestrator.tomlにカスタムラウンド設定を含める
   - Orchestrator.execute()を呼び出す
   - 生成されたOrchestratorTaskのラウンド設定を検証

2. **test_round_config_passthrough_with_defaults**: デフォルト値がOrchestratorTaskに渡されることを確認
   - orchestrator.tomlにラウンド設定を含めない
   - Orchestrator.execute()を呼び出す
   - デフォルト値がOrchestratorTaskに設定されることを確認

**Acceptance Criteria**:
- 統合テストが記述される
- テストは失敗する（実装前）
- `tests/orchestrator/test_orchestrator.py`が適切に更新される

**Dependencies**: T005

**Parallel**: ✅ Can be written in parallel with T005 (different file)

---

### T007 [US1][Impl] Pass round configuration from Orchestrator to OrchestratorTask

**File**: `src/mixseek/orchestrator/orchestrator.py`
**Story**: US1
**Type**: Implementation
**Estimated Time**: 20 minutes

**Description**:
Orchestrator.execute()メソッドでOrchestratorTask生成時にラウンド設定を渡す。

**Implementation Steps**:
1. `src/mixseek/orchestrator/orchestrator.py:128-139`を編集
2. OrchestratorTaskインスタンス化時に以下のフィールドを追加:
   ```python
   task = OrchestratorTask(
       execution_id=execution_id,
       user_prompt=user_prompt,
       team_configs=[ref.config for ref in self.config.teams],
       timeout_seconds=timeout,
       # Add round configuration
       max_rounds=self.config.max_rounds,
       min_rounds=self.config.min_rounds,
       submission_timeout_seconds=self.config.submission_timeout_seconds,
       judgment_timeout_seconds=self.config.judgment_timeout_seconds,
   )
   ```

**Acceptance Criteria**:
- ラウンド設定がOrchestratorSettingsからOrchestratorTaskへ渡される
- T006の統合テストが通過する
- 既存の機能に影響なし（後方互換性維持）

**Dependencies**: T006

---

### T008 [US1][Checkpoint] Verify US1 acceptance scenarios

**File**: N/A (Manual Test)
**Story**: US1
**Type**: Manual Verification
**Estimated Time**: 30 minutes

**Description**:
spec.mdで定義されたUS1の受け入れシナリオを手動で検証する。

**Acceptance Scenarios**:
1. orchestrator.tomlに`max_rounds = 10`を設定し、システムが最大10ラウンドまで実行することを確認
2. orchestrator.tomlに`min_rounds = 3`を設定し、システムが最低3ラウンドを保証することを確認
3. orchestrator.tomlに`submission_timeout_seconds = 600`を設定し、タイムアウトが適用されることを確認
4. orchestrator.tomlに`judgment_timeout_seconds = 120`を設定し、タイムアウトが適用されることを確認

**Acceptance Criteria**:
- すべての受け入れシナリオが通過する
- quickstart.mdの設定例が動作することを確認

**Dependencies**: T007

**🎯 MILESTONE**: User Story 1 (P1) Complete

---

## Phase 3: User Story 3 - バリデーションとエラー処理 (P1)

*Goal: 無効なラウンド設定値に対して明確なバリデーションエラーを表示する*

**Independent Test**: 無効な設定（max_rounds = 0、min_rounds > max_rounds等）を提供し、設定読み込み時に明確なエラーメッセージが表示されることを確認する。

**Note**: US3はP1優先度であり、US1と密接に関連しているため、US2（P2）よりも先に実装する。

### T009 [US3][Test] Write tests for cross-field validation

**File**: `tests/config/test_orchestrator_settings.py`
**Story**: US3
**Type**: Test (TDD Red Phase)
**Estimated Time**: 30 minutes

**Description**:
min_rounds <= max_roundsの相互フィールドバリデーションテストを作成する。

**Test Cases**:
1. **test_min_rounds_exceeds_max_rounds**: min_rounds > max_roundsでValidationErrorが発生
   ```python
   # max_rounds=3, min_rounds=5 → ValidationError
   ```

2. **test_valid_round_combinations**: 有効な組み合わせが許可される
   ```python
   # max_rounds=10, min_rounds=5 → OK
   # max_rounds=5, min_rounds=5 → OK (境界値)
   ```

3. **test_error_message_clarity**: エラーメッセージが具体的な値を含む
   ```python
   # "min_rounds (5) must be <= max_rounds (3)" のような形式
   ```

**Acceptance Criteria**:
- 相互検証テストが記述される
- テストは失敗する（Redフェーズ）
- エラーメッセージの形式が検証される

**Dependencies**: T005

---

### T010 [US3][Impl] Add cross-field validation to OrchestratorSettings

**File**: `src/mixseek/config/schema.py`
**Story**: US3
**Type**: Implementation (TDD Green Phase)
**Estimated Time**: 20 minutes

**Description**:
OrchestratorSettingsに@model_validatorを追加し、min_rounds <= max_roundsを検証する。

**Implementation Steps**:
1. `src/mixseek/config/schema.py`のOrchestratorSettingsクラスに追加:
   ```python
   from pydantic import model_validator

   @model_validator(mode='after')
   def validate_round_configuration(self) -> 'OrchestratorSettings':
       """Validate min_rounds <= max_rounds constraint."""
       if self.min_rounds > self.max_rounds:
           raise ValueError(
               f"min_rounds ({self.min_rounds}) must be <= max_rounds ({self.max_rounds})"
           )
       return self
   ```

**Acceptance Criteria**:
- @model_validatorが実装される
- T009のテストが通過する（Greenフェーズ）
- エラーメッセージが明確で具体的

**Dependencies**: T009

---

### T011 [US3][Test] Write tests for validation error messages

**File**: `tests/config/test_orchestrator_settings.py`
**Story**: US3
**Type**: Test
**Estimated Time**: 30 minutes

**Description**:
spec.mdの受け入れシナリオに対応するバリデーションエラーテストを作成する。

**Test Cases**:
1. **test_max_rounds_zero_error_message**: max_rounds = 0でエラー
   - エラーメッセージ: "Input should be greater than or equal to 1"

2. **test_min_rounds_exceeds_max_rounds_error_message**: min_rounds > max_roundsでエラー
   - エラーメッセージ: "min_rounds (5) must be <= max_rounds (3)"

3. **test_negative_timeout_error_message**: submission_timeout_seconds = -100でエラー
   - エラーメッセージ: "Input should be greater than 0"

4. **test_validation_error_timing**: バリデーションエラーが1秒以内に検出される（SC-004）

**Acceptance Criteria**:
- すべてのエラーケースがテストされる
- エラーメッセージの形式が検証される
- バリデーション時間が1秒以内であることを確認（SC-004）

**Dependencies**: T010

**Parallel**: ✅ Can be written in parallel with T010

---

### T012 [US3][Checkpoint] Verify US3 acceptance scenarios

**File**: N/A (Manual Test)
**Story**: US3
**Type**: Manual Verification
**Estimated Time**: 20 minutes

**Description**:
spec.mdで定義されたUS3の受け入れシナリオを手動で検証する。

**Acceptance Scenarios**:
1. orchestrator.tomlに`max_rounds = 0`を設定し、バリデーションエラーが表示されることを確認
2. orchestrator.tomlに`min_rounds = 5, max_rounds = 3`を設定し、明確なエラーメッセージが表示されることを確認
3. orchestrator.tomlに`submission_timeout_seconds = -100`を設定し、エラーが表示されることを確認

**Acceptance Criteria**:
- すべての受け入れシナリオが通過する
- エラーメッセージが明確で分かりやすい
- quickstart.mdのトラブルシューティングセクションが有効

**Dependencies**: T011

**🎯 MILESTONE**: User Story 3 (P1) Complete

---

## Phase 4: User Story 2 - 環境変数による上書き (P2)

*Goal: 環境変数を使用してTOML設定されたラウンドパラメータを上書きできるようにする*

**Independent Test**: 環境変数（MIXSEEK_MAX_ROUNDS=7）を設定し、異なる値を含むorchestrator.tomlでタスクを実行し、環境変数が優先されることを確認する。

### T013 [US2][Test] Write tests for environment variable precedence

**File**: `tests/config/test_orchestrator_settings.py`
**Story**: US2
**Type**: Test
**Estimated Time**: 30 minutes

**Description**:
環境変数がTOML設定を上書きすることを確認するテストを作成する。

**Test Cases**:
1. **test_env_var_overrides_toml**: 環境変数がTOML設定を上書き
   ```python
   # TOML: max_rounds = 5
   # ENV: MIXSEEK_MAX_ROUNDS=7
   # Expected: max_rounds = 7
   ```

2. **test_env_var_overrides_default**: 環境変数がデフォルト値を上書き
   ```python
   # No TOML setting
   # ENV: MIXSEEK_MAX_ROUNDS=8
   # Expected: max_rounds = 8
   ```

3. **test_precedence_order**: 優先順位（ENV > TOML > Default）を検証
   - 環境変数ありの場合: 環境変数の値
   - 環境変数なし、TOMLあり: TOMLの値
   - 環境変数なし、TOMLなし: デフォルト値

4. **test_all_round_fields_env_override**: すべてのラウンド設定フィールドで環境変数上書きを検証
   - MIXSEEK_MAX_ROUNDS
   - MIXSEEK_MIN_ROUNDS
   - MIXSEEK_SUBMISSION_TIMEOUT_SECONDS
   - MIXSEEK_JUDGMENT_TIMEOUT_SECONDS

**Acceptance Criteria**:
- 環境変数優先順位テストが記述される
- テストはすでに通過する（Pydantic Settingsの既存機能）
- すべてのラウンド設定フィールドで環境変数上書きが動作する

**Dependencies**: T010 (US3 completion recommended for stable foundation)

---

### T014 [US2][Checkpoint] Verify US2 acceptance scenarios

**File**: N/A (Manual Test)
**Story**: US2
**Type**: Manual Verification
**Estimated Time**: 20 minutes

**Description**:
spec.mdで定義されたUS2の受け入れシナリオを手動で検証する。

**Acceptance Scenarios**:
1. `MIXSEEK_MAX_ROUNDS=7`環境変数を設定し、orchestrator.tomlに`max_rounds = 5`が含まれる場合、max_rounds=7が使用されることを確認
2. `MIXSEEK_MIN_ROUNDS=1`環境変数を設定し、TOML設定に関わらずmin_rounds=1が使用されることを確認

**Acceptance Criteria**:
- すべての受け入れシナリオが通過する
- quickstart.mdの環境変数例が動作することを確認

**Dependencies**: T013

**🎯 MILESTONE**: User Story 2 (P2) Complete

---

## Phase 5: Polish & Integration

*Final tasks for code quality, documentation, and system integration*

### T015 [Polish] Run code quality checks

**Files**: All modified files
**Story**: Integration
**Type**: Quality Assurance
**Estimated Time**: 20 minutes

**Description**:
Article 8（Code Quality Standards）に従い、すべての品質チェックを実行する。

**Quality Checks**:
```bash
# Linting and auto-fix
ruff check --fix .

# Formatting
ruff format .

# Type checking
mypy .
```

**Acceptance Criteria**:
- ruff check: 0 errors
- ruff format: すべてのファイルがフォーマット済み
- mypy: 0 type errors (strict mode)
- 新しいコードがline length 119以内

**Dependencies**: All implementation tasks (T005, T007, T010)

---

### T016 [Polish] Verify backwards compatibility

**Files**: All modified files
**Story**: Integration
**Type**: Compatibility Test
**Estimated Time**: 20 minutes

**Description**:
既存のorchestrator.tomlファイル（ラウンド設定なし）が引き続き動作することを確認する。

**Test Cases**:
1. ラウンド設定を含まない既存のorchestrator.tomlでタスクを実行
2. デフォルト値（max_rounds=5等）が使用されることを確認
3. 既存の機能（timeout_per_team_seconds、teams）に影響がないことを確認

**Acceptance Criteria**:
- 既存のorchestrator.tomlファイルが動作する
- デフォルト値が正しく適用される
- 既存機能に破壊的変更なし

**Dependencies**: T008, T012, T014 (All user stories complete)

---

### T017 [Polish] Verify success criteria

**Files**: N/A (Success Criteria Verification)
**Story**: Integration
**Type**: Final Verification
**Estimated Time**: 30 minutes

**Description**:
spec.mdで定義された成功基準（SC-001～SC-007）を検証する。

**Success Criteria Verification**:
- **SC-001**: orchestrator.toml経由でmax_roundsを設定でき、システムが設定された制限を尊重する ✅
- **SC-002**: orchestrator.toml経由でmin_roundsを設定でき、システムがLLMベースの終了前に最低その数のラウンドを保証する ✅
- **SC-003**: orchestrator.toml経由でタイムアウト値を設定でき、タイムアウト適用を観察できる ✅
- **SC-004**: 設定バリデーションが無効な設定を読み込み後1秒以内に明確なエラーメッセージで拒否する ✅
- **SC-005**: 環境変数がTOML設定値を正常に上書きする ✅
- **SC-006**: すべての4つのラウンド設定フィールドがorchestrator.tomlで指定されていない場合にデフォルト値で正しく動作する ✅
- **SC-007**: `mixseek config list`コマンドで新規追加されたラウンド設定フィールドが表示される ✅

**Acceptance Criteria**:
- すべての成功基準が検証される
- 各成功基準の検証方法が文書化される

**Dependencies**: T016

---

### T018 [Polish] Final commit and PR preparation

**Files**: All modified files
**Story**: Integration
**Type**: Git Operations
**Estimated Time**: 15 minutes

**Description**:
変更をコミットし、プルリクエストの準備を行う。

**Commit Steps**:
```bash
# Stage all changes
git add src/mixseek/config/schema.py
git add src/mixseek/orchestrator/orchestrator.py
git add tests/config/test_orchestrator_settings.py
git add tests/orchestrator/test_orchestrator.py

# Commit with message
git commit -m "feat(101-round-config): Add TOML support for round configuration

Implemented Feature 101-round-config to enable TOML-based configuration
for round execution parameters (max_rounds, min_rounds, timeouts).

**User Stories Completed**:
- US1 (P1): TOML file configuration
- US2 (P2): Environment variable override
- US3 (P1): Validation and error handling

**Changes**:
- Added 4 round config fields to OrchestratorSettings (FR-001~FR-004)
- Implemented cross-field validation (FR-005)
- Passed round config from Orchestrator to OrchestratorTask (FR-006)
- Added comprehensive unit and integration tests

**Testing**:
- All tests passing (pytest)
- Code quality checks passing (ruff, mypy)
- Backwards compatibility verified

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Acceptance Criteria**:
- すべての変更がコミットされる
- コミットメッセージがconventional commits形式に準拠
- Article 3（Test-First）、Article 8（Code Quality）に準拠

**Dependencies**: T017

**🎉 FINAL MILESTONE**: Feature 101-round-config Complete!

---

## Task Summary

**Total Tasks**: 18
**Estimated Total Time**: ~6.5 hours

### Tasks by Phase

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Setup | T001-T002 | 25 min |
| Phase 2: US1 (P1) | T003-T008 | 3h 05min |
| Phase 3: US3 (P1) | T009-T012 | 1h 40min |
| Phase 4: US2 (P2) | T013-T014 | 50 min |
| Phase 5: Polish | T015-T018 | 1h 45min |

### Tasks by User Story

| User Story | Tasks | Priority |
|------------|-------|----------|
| US1: TOML Configuration | T003-T008 | P1 |
| US2: Environment Variable Override | T013-T014 | P2 |
| US3: Validation & Error Handling | T009-T012 | P1 |
| Setup & Integration | T001-T002, T015-T018 | Foundation |

### Parallel Execution Opportunities

**Phase 1**:
- T001 [P] T002 (different concerns)

**Phase 2 (US1)**:
- T003 must complete first (test foundation)
- T005 [P] T006 (different files: schema.py vs test_orchestrator.py)

**Phase 3 (US3)**:
- T010 [P] T011 (implementation vs additional tests)

**Phase 4 (US2)**:
- T013 is self-contained (environment variable tests)

## Dependencies Graph

```
Setup Phase
├── T001 (Verify infrastructure) ──────┐
└── T002 (Create test file) [P] ───────┤
                                        │
User Story 1 (P1)                      │
├── T003 (US1 Tests) ◄─────────────────┘
├── T004 (Gate: User Approval) ◄─ T003
├── T005 (US1 Implementation) ◄─ T004
├── T006 (Integration Tests) [P] ◄─ T005
├── T007 (Config Pass-through) ◄─ T006
└── T008 (US1 Checkpoint) ◄─ T007
         │
         │ US1 Complete ✓
         │
User Story 3 (P1)
├── T009 (US3 Tests) ◄─ T005 (needs US1 foundation)
├── T010 (Cross-field Validation) ◄─ T009
├── T011 (Error Message Tests) [P] ◄─ T010
└── T012 (US3 Checkpoint) ◄─ T011
         │
         │ US3 Complete ✓
         │
User Story 2 (P2)
├── T013 (US2 Tests) ◄─ T010 (recommended)
└── T014 (US2 Checkpoint) ◄─ T013
         │
         │ US2 Complete ✓
         │
Polish & Integration
├── T015 (Code Quality) ◄─ T005, T007, T010
├── T016 (Backwards Compat) ◄─ T008, T012, T014
├── T017 (Success Criteria) ◄─ T016
└── T018 (Final Commit) ◄─ T017

Legend:
[P] = Can be executed in parallel with previous task
◄─ = Depends on
```

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Recommended MVP**: User Story 1 only (P1)
- **Tasks**: T001-T008
- **Estimated Time**: ~3.5 hours
- **Deliverable**: TOML-based round configuration with default validation
- **Value**: Core功能が動作し、運用者がorchestrator.tomlで設定を管理できる

### Incremental Delivery Plan

**Iteration 1** (MVP):
- Phase 1: Setup (T001-T002)
- Phase 2: US1 - TOML Configuration (T003-T008)
- Deliver: Basic TOML configuration support

**Iteration 2** (Enhanced Validation):
- Phase 3: US3 - Validation & Error Handling (T009-T012)
- Deliver: Robust error handling and validation

**Iteration 3** (Complete Feature):
- Phase 4: US2 - Environment Variable Override (T013-T014)
- Phase 5: Polish & Integration (T015-T018)
- Deliver: Full feature with environment variable support

### TDD Workflow

Each implementation task follows TDD cycle:

1. **Red Phase**: Write failing test (T003, T006, T009, T011, T013)
2. **User Approval**: Get user approval for tests (T004 gate)
3. **Green Phase**: Implement code to pass tests (T005, T007, T010)
4. **Refactor**: Code quality checks (T015)
5. **Verify**: User story checkpoints (T008, T012, T014)

### Parallel Execution Examples

**Example 1: Phase 1 Setup**
```bash
# Terminal 1: Verify infrastructure
Task T001

# Terminal 2: Create test files (in parallel)
Task T002
```

**Example 2: Phase 2 US1 Tests and Implementation**
```bash
# Sequential: Write and approve tests first
Task T003 → T004 (Gate)

# After approval, parallel execution
# Terminal 1: Implement OrchestratorSettings
Task T005

# Terminal 2: Write integration tests (in parallel)
Task T006
```

## Quality Gates

### Gate 1: Test Approval (T004)

**Criteria**:
- All US1 tests reviewed and approved by user
- Tests demonstrate Redフェーズ（fail before implementation）
- Test coverage is comprehensive (FR-001~FR-007)

**Action if Failed**: Revise tests based on user feedback, resubmit for approval

### Gate 2: User Story Checkpoints (T008, T012, T014)

**Criteria**:
- All acceptance scenarios pass
- Independent test criteria verified
- No regressions in existing functionality

**Action if Failed**: Debug and fix implementation, re-run tests

### Gate 3: Final Verification (T017)

**Criteria**:
- All success criteria (SC-001~SC-007) verified
- Code quality checks pass (ruff, mypy)
- Backwards compatibility confirmed

**Action if Failed**: Address failures, re-run verification

---

## Phase 6: Architecture Simplification (FR-011)

*Refactored Orchestrator to use OrchestratorSettings directly, eliminated redundant OrchestratorConfig (COMPLETED)*

### T019 [Refactor][Test] Write tests for Orchestrator with OrchestratorSettings

**File**: `tests/unit/orchestrator/test_orchestrator.py`
**Story**: FR-011
**Type**: Test (TDD Red Phase)
**Estimated Time**: 30 minutes

**Description**:
OrchestratorがOrchestratorSettingsを直接受け取るようになった場合のテストを作成する。

**Test Cases**:
1. **test_orchestrator_initialization_with_settings**: OrchestratorSettingsでOrchestrator初期化
2. **test_orchestrator_uses_settings_workspace**: OrchestratorがOrchestratorSettings.workspace_pathを使用
3. **test_orchestrator_uses_settings_teams**: OrchestratorがOrchestratorSettings.teamsを使用
4. **test_orchestrator_uses_settings_timeout**: OrchestratorがOrchestratorSettings.timeout_per_team_secondsを使用

**Acceptance Criteria**:
- 新しいテストが記述される
- テストは失敗する（Redフェーズ - 実装前）
- テストコードがruff、mypyに準拠

**Dependencies**: T015 (Code quality checks complete)

---

### T020 [Refactor][Impl] Refactor Orchestrator to accept OrchestratorSettings

**Files**:
- `src/mixseek/orchestrator/orchestrator.py`
- `src/mixseek/cli/commands/exec.py`
- `src/mixseek/orchestrator/__init__.py`

**Story**: FR-011
**Type**: Implementation (TDD Green Phase)
**Estimated Time**: 60 minutes

**Description**:
Orchestratorクラスを`OrchestratorSettings`を受け取るようにリファクタリングした（`OrchestratorConfig`削除済み）。

**Implementation Steps** (COMPLETED):
1. `Orchestrator.__init__`のシグネチャ変更:
   ```python
   def __init__(
       self,
       settings: OrchestratorSettings,
       save_db: bool = True,
   ) -> None:
   ```

2. `self.config`を`self.settings`に変更し、各属性アクセスを更新:
   - `self.config.timeout_per_team_seconds` → `self.settings.timeout_per_team_seconds`
   - `self.config.teams` → `self.settings.teams`

3. `load_orchestrator_settings`関数を実装:
   ```python
   def load_orchestrator_settings(config_path: Path, workspace: Path | None = None) -> OrchestratorSettings:
       config_manager = ConfigurationManager(workspace=workspace)
       return config_manager.load_orchestrator_settings(config_path=config_path)
   ```

4. `exec.py`の`_load_and_validate_config`と`_initialize_orchestrator`を更新

5. `__init__.py`のエクスポートを更新（`load_orchestrator_settings`に変更）

**Acceptance Criteria** (ALL MET):
- Orchestratorが`OrchestratorSettings`を受け取る
- `OrchestratorConfig`への参照がすべて削除済み
- T019のテストが通過した（Greenフェーズ）
- 既存の統合テストが通過した

**Dependencies**: T019

---

### T021 [Refactor][Test] Update all tests to use OrchestratorSettings

**Files**: `tests/**/*.py`
**Story**: FR-011
**Type**: Test Update
**Estimated Time**: 45 minutes

**Description**:
すべてのテストを`OrchestratorSettings`を使用するように更新した（`OrchestratorConfig`削除済み）。

**Test Files Updated** (COMPLETED):
- `tests/unit/orchestrator/test_orchestrator.py`
- `tests/unit/orchestrator/test_models.py`
- `tests/integration/test_orchestrator_e2e.py`
- `tests/cli/commands/test_exec_logfire.py`
- その他のテスト（約18箇所）

**Implementation Steps** (COMPLETED):
1. `OrchestratorSettings`を使用するようfixture/モックを変更
2. `config=OrchestratorConfig(...)`を`settings=OrchestratorSettings(...)`に変更
3. テストアサーションを更新（`orchestrator.config.*` → `orchestrator.settings.*`）

**Acceptance Criteria** (ALL MET):
- すべてのテストが`OrchestratorSettings`を使用
- `OrchestratorConfig`への参照が削除済み
- 全テストスイートが通過した（`pytest tests/`）

**Dependencies**: T020

---

### T022 [Refactor][Cleanup] Remove OrchestratorConfig model

**File**: `src/mixseek/orchestrator/models.py`
**Story**: FR-011
**Type**: Code Cleanup
**Estimated Time**: 15 minutes

**Description**:
`OrchestratorConfig`モデルと`TeamReference`モデルの定義を完全に削除した。

**Implementation Steps** (COMPLETED):
1. `src/mixseek/orchestrator/models.py`から`OrchestratorConfig`クラス定義を削除
2. `TeamReference`クラスも削除（他で使用されていないことを確認済み）
3. インポート文をクリーンアップ

**Acceptance Criteria** (ALL MET):
- `OrchestratorConfig`クラスが削除済み
- `TeamReference`クラスが削除済み
- 全テストスイートが通過した
- ruff、mypyチェックが通過した

**Dependencies**: T021

---

### T023 [Refactor][Checkpoint] Verify FR-011 complete

**File**: N/A (Verification)
**Story**: FR-011
**Type**: Manual Verification
**Estimated Time**: 20 minutes

**Description**:
FR-011（アーキテクチャ簡素化）が完全に実装されたことを確認する。

**Verification Checklist** (COMPLETED):
- [x] Orchestratorが`OrchestratorSettings`を直接受け取る
- [x] `OrchestratorConfig`への参照がコードベースに存在しない（ドキュメント内の履歴記述を除く）
- [x] すべてのテストが通過した（`pytest tests/ -v`）
- [x] コード品質チェックが通過した（ruff、mypy）
- [x] 既存機能に破壊的変更がない（後方互換性維持）

**Acceptance Criteria** (ALL MET):
- すべてのチェックリスト項目が完了
- 68個以上のorchestrator関連テストが通過

**Dependencies**: T022

**🎯 MILESTONE**: FR-011 (Architecture Simplification) Complete

---

## Notes

### Constitution Compliance

- **Article 3 (Test-First)**: T003, T006, T009, T011, T013（テスト優先）
- **Article 4 (Documentation)**: spec.md、data-model.md、quickstart.md準拠
- **Article 8 (Code Quality)**: T015（ruff、mypy実行）
- **Article 9 (Data Accuracy)**: デフォルト値明示、マジックナンバー排除
- **Article 10 (DRY)**: 既存ConfigurationManager再利用
- **Article 14 (Framework Consistency)**: MixSeek-Core仕様との整合性確認済み
- **Article 16 (Type Safety)**: Pydantic型注釈、mypy strict mode

### Risk Mitigation

**Risk 1**: OrchestratorSettings変更が既存機能に影響
- **Mitigation**: T016で後方互換性を明示的にテスト

**Risk 2**: バリデーションロジックの複雑化
- **Mitigation**: T009-T011で段階的にテストを追加し、明確なエラーメッセージを確保

**Risk 3**: 環境変数優先順位の誤解
- **Mitigation**: T013で明示的に優先順位をテスト、quickstart.mdで文書化

## Next Steps

1. **Start with T001**: Verify existing infrastructure
2. **Follow TDD workflow**: Tests → Approval → Implementation
3. **Track progress**: 各タスク完了時にチェックマーク ✅
4. **Communicate**: Gate通過時、Milestone到達時にステークホルダーに報告

**Ready to begin implementation!** 🚀
