# Tasks: MixSeek Agent Skills - ワークスペース管理

**Input**: Design documents from `/specs/023-agent-skills-mixseek/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: E2Eテスト（Claude Code/Gemini CLIでの動作確認）で代替。skills-ref validateで検証。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Skills directory**: `.skills/` at repository root
- **Scripts**: `.skills/<skill-name>/scripts/`
- **References**: `.skills/<skill-name>/references/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: スキルディレクトリ構造の初期化

- [x] T001 Create `.skills/` directory structure at repository root
- [x] T002 [P] Add `.skills/` to `CLAUDE.md` Active Technologies section

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 共通参照ファイルの作成（全スキルで使用）

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `.skills/mixseek-model-list/references/VALID-MODELS.md` from `docs/data/valid-models.csv`
- [x] T004 [P] Create shared TOML schema documentation template for references/ directories

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - ワークスペース初期化 (Priority: P1) 🎯 MVP

**Goal**: 自然言語で「mixseekのワークスペースを作成して」と依頼し、必要なディレクトリ構造と初期設定を自動生成

**Independent Test**: 空のディレクトリで「ワークスペースを初期化して」と依頼し、`configs/`、`logs/`、`templates/`ディレクトリが作成されることを確認

### Implementation for User Story 1

- [x] T005 [P] [US1] Create `.skills/mixseek-workspace-init/SKILL.md` with frontmatter and instructions
- [x] T006 [P] [US1] Create `.skills/mixseek-workspace-init/scripts/init-workspace.sh` for directory creation

### Validation for User Story 1

- [x] T007 [US1] Validate mixseek-workspace-init skill with `agentskills validate .skills/mixseek-workspace-init`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - チーム設定生成 (Priority: P1)

**Goal**: 「Web検索と分析ができるチームを作って」のような自然言語でチーム設定を生成し、有効なTOML設定ファイルを取得

**Independent Test**: 「Web検索エージェントを持つチームを作成して」と依頼し、有効なteam.tomlが生成されることを確認

### Implementation for User Story 2

- [x] T008 [P] [US2] Create `.skills/mixseek-team-config/SKILL.md` with frontmatter, instructions, and TOML templates
- [x] T009 [P] [US2] Create `.skills/mixseek-team-config/references/TOML-SCHEMA.md` with team config schema
- [x] T010 [P] [US2] Create `.skills/mixseek-team-config/references/MEMBER-TYPES.md` with agent type descriptions

### Validation for User Story 2

- [x] T011 [US2] Validate mixseek-team-config skill with `agentskills validate .skills/mixseek-team-config`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - オーケストレーター設定生成 (Priority: P2)

**Goal**: 複数チームを並列実行して競合させるオーケストレーター設定を自然言語で生成

**Independent Test**: 「2つのチームで競合させる設定を作って」と依頼し、orchestrator.tomlが生成されることを確認

### Implementation for User Story 3

- [x] T012 [P] [US3] Create `.skills/mixseek-orchestrator-config/SKILL.md` with frontmatter and instructions
- [x] T013 [P] [US3] Create `.skills/mixseek-orchestrator-config/references/TOML-SCHEMA.md` with orchestrator schema

### Validation for User Story 3

- [x] T014 [US3] Validate mixseek-orchestrator-config skill with `agentskills validate .skills/mixseek-orchestrator-config`

**Checkpoint**: User Stories 1, 2, and 3 should all work independently

---

## Phase 6: User Story 4 - 評価設定生成 (Priority: P2)

**Goal**: Submissionを評価するための評価基準と判定ロジックの設定を自然言語で生成

**Independent Test**: 「正確性を重視した評価設定を作って」と依頼し、evaluator.tomlとjudgment.tomlが生成されることを確認

### Implementation for User Story 4

- [x] T015 [P] [US4] Create `.skills/mixseek-evaluator-config/SKILL.md` with frontmatter and instructions
- [x] T016 [P] [US4] Create `.skills/mixseek-evaluator-config/references/TOML-SCHEMA.md` with evaluator/judgment schema
- [x] T017 [P] [US4] Create `.skills/mixseek-evaluator-config/references/METRICS.md` with standard metrics descriptions

### Validation for User Story 4

- [x] T018 [US4] Validate mixseek-evaluator-config skill with `agentskills validate .skills/mixseek-evaluator-config`

**Checkpoint**: User Stories 1-4 should all work independently

---

## Phase 7: User Story 5 - 設定検証 (Priority: P2)

**Goal**: 生成または手動編集した設定ファイルがMixSeekスキーマに準拠しているか検証

**Independent Test**: 「team.tomlを検証して」と依頼し、TOML構文エラーや必須フィールド欠落が報告されることを確認

### Implementation for User Story 5

- [x] T019 [P] [US5] Create `.skills/mixseek-config-validate/SKILL.md` with frontmatter and validation instructions
- [x] T020 [P] [US5] Create `.skills/mixseek-config-validate/scripts/validate-config.py` using existing Pydantic schemas

### Validation for User Story 5

- [x] T021 [US5] Validate mixseek-config-validate skill with `agentskills validate .skills/mixseek-config-validate`
- [x] T022 [US5] Run ruff and mypy on `.skills/mixseek-config-validate/scripts/validate-config.py`

**Checkpoint**: User Stories 1-5 should all work independently

---

## Phase 8: User Story 6 - モデル一覧取得 (Priority: P3)

**Goal**: 利用可能なLLMモデルの一覧を取得し、用途に適したモデルを選択

**Independent Test**: 「今使えるモデルを教えて」と依頼し、プロバイダー別のモデル一覧が表示されることを確認

### Implementation for User Story 6

- [x] T023 [P] [US6] Create `.skills/mixseek-model-list/SKILL.md` with frontmatter and model listing instructions

### Validation for User Story 6

- [x] T024 [US6] Validate mixseek-model-list skill with `agentskills validate .skills/mixseek-model-list`

**Checkpoint**: All user stories (1-6) should now be independently functional

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 全体検証と仕上げ

- [x] T025 [P] Run `agentskills validate` on all 6 skills
- [x] T026 [P] Verify quickstart.md examples work with implemented skills
- [x] T027 Update `CLAUDE.md` with skill installation and usage information
- [x] T028 Run E2E validation: test skill discovery and basic usage in Claude Code

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories (T003 creates VALID-MODELS.md used by US6)
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 priority - can proceed in parallel
  - US3 and US4 and US5 are P2 priority - can proceed in parallel
  - US6 is P3 priority - depends on T003 (VALID-MODELS.md)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational - Conceptually builds on US2 but independently testable
- **User Story 4 (P2)**: Can start after Foundational - No dependencies on other stories
- **User Story 5 (P2)**: Can start after Foundational - Validates configs from US2/US3/US4 but independently testable
- **User Story 6 (P3)**: Depends on T003 (VALID-MODELS.md from Foundational phase)

### Within Each User Story

- SKILL.md files can be created in parallel ([P] marked)
- references/ files can be created in parallel ([P] marked)
- scripts/ files can be created in parallel ([P] marked)
- Validation must come after all files for that skill are created
- Story complete before moving to next priority

### Parallel Opportunities

- T002 can run in parallel with T001 completion
- T003 and T004 can run in parallel
- T005 and T006 can run in parallel (US1)
- T008, T009, T010 can run in parallel (US2)
- T012 and T013 can run in parallel (US3)
- T015, T016, T017 can run in parallel (US4)
- T019 and T020 can run in parallel (US5)
- T023 can run independently (US6)
- T025, T026 can run in parallel (Polish)

---

## Parallel Example: User Story 2

```bash
# Launch all SKILL.md and references for User Story 2 together:
Task: "Create .skills/mixseek-team-config/SKILL.md with frontmatter, instructions, and TOML templates"
Task: "Create .skills/mixseek-team-config/references/TOML-SCHEMA.md with team config schema"
Task: "Create .skills/mixseek-team-config/references/MEMBER-TYPES.md with agent type descriptions"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (workspace-init)
4. Complete Phase 4: User Story 2 (team-config)
5. **STOP and VALIDATE**: Test both skills independently with Claude Code
6. Deploy/demo if ready - users can initialize workspaces and generate team configs

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently (workspace init works)
3. Add User Story 2 → Test independently (team config works) → MVP!
4. Add User Story 3 → Test independently (orchestrator config works)
5. Add User Story 4 → Test independently (evaluator config works)
6. Add User Story 5 → Test independently (config validation works)
7. Add User Story 6 → Test independently (model list works)
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (workspace-init) + User Story 3 (orchestrator)
   - Developer B: User Story 2 (team-config) + User Story 4 (evaluator)
   - Developer C: User Story 5 (validate) + User Story 6 (model-list)
3. Stories complete and validate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify with `agentskills validate` after each skill is complete
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All SKILL.md files must follow contracts/skill-format.md
- All TOML references must follow contracts/toml-schemas.md
