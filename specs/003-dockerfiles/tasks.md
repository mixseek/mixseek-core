# Tasks: Docker開発環境テンプレート

**Input**: Design documents from `/specs/003-dockerfiles/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are not explicitly requested in the feature specification, so test tasks are not included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Docker infrastructure: `dockerfiles/` at repository root
- Documentation: `docs/` at repository root
- Tests: `tests/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per implementation plan with dockerfiles/{dev,ci,prod,templates}/ directories
- [X] T002 [P] Create .gitignore file excluding .env.* files and Docker build artifacts
- [X] T003 [P] Initialize repository documentation structure in docs/
- [X] T004 [P] Create dockerfiles/Makefile.common with shared variables and network management targets

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create base Dockerfile interface contract validation in dockerfiles/Makefile.common with build arg requirements (USERNAME, UID, GID)
- [X] T006 [P] Setup UID/GID synchronization mechanism in dockerfiles/Makefile.common with HOST_USERNAME, HOST_UID, HOST_GID variables
- [X] T007 [P] Create docker network management targets (create_network) in dockerfiles/Makefile.common
- [X] T008 [P] Setup base directory structure creation logic for /app and /venv directories
- [X] T009 Configure error handling and validation framework for Docker build processes

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 標準化された開発環境のセットアップ (Priority: P1) 🎯 MVP

**Goal**: 新しい開発者が10分以内に再現可能な開発環境（AI開発ツール含む）をセットアップできる

**Independent Test**: リポジトリをクローンし、`make -C dockerfiles/dev build && make -C dockerfiles/dev run && make -C dockerfiles/dev bash`を実行してPython/Node.js/AI開発ツールが利用可能なことを確認

### Implementation for User Story 1

- [X] T010 [P] [US1] Create development environment Dockerfile in dockerfiles/dev/Dockerfile with base image ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim
- [X] T011 [P] [US1] Create development environment Makefile in dockerfiles/dev/Makefile with build, run, bash, stop, rm targets
- [X] T012 [US1] Implement Node.js 22.20.0 installation via nvm in dockerfiles/dev/Dockerfile with NVM_DIR and NODE_VERSION environment variables
- [X] T013 [US1] Install AI development tools (Claude Code, Codex, Gemini CLI) via npm global install in dockerfiles/dev/Dockerfile
- [X] T014 [US1] Setup Python virtual environment with uv in dockerfiles/dev/Dockerfile with PYTHONPATH and VIRTUAL_ENV configuration
- [X] T015 [US1] Configure development container user permissions with non-root user setup using build args
- [X] T016 [US1] Add development workflow volume mounts in dockerfiles/dev/Makefile for project files and hot reload
- [X] T017 [US1] Configure development container ports (5678 for debugpy) and network connectivity
- [X] T018 [US1] Add debugging support targets in dockerfiles/dev/Makefile (debug target with ARG parameter)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - セキュアな設定管理 (Priority: P1)

**Goal**: バージョン管理で機密情報を公開せずに、環境別に設定を安全に管理できる

**Independent Test**: 環境テンプレートをコピー、設定後にコンテナ起動してハードコードされた認証情報なしで環境変数が読み込まれることを確認

### Implementation for User Story 2

- [X] T019 [P] [US2] Create development environment template in dockerfiles/templates/.env.dev.template with placeholder format
- [X] T020 [P] [US2] Create CI environment template in dockerfiles/templates/.env.ci.template with CI-specific placeholders
- [X] T021 [P] [US2] Create production environment template in dockerfiles/templates/.env.prod.template with production security placeholders
- [X] T022 [US2] Implement environment variable loading in dockerfiles/dev/Makefile using --env-file parameter
- [X] T023 [US2] Add template validation function in dockerfiles/Makefile.common to check placeholder format
- [X] T024 [US2] Configure secure environment variable handling with no secrets in Dockerfiles
- [X] T025 [US2] Add environment-specific sections (system, AI tools, cloud providers, development tools, database) to all templates
- [X] T026 [US2] Document environment variable setup workflow in quickstart.md template copying instructions

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 多環境サポート (Priority: P2)

**Goal**: 開発、CI、本番環境で環境固有の最適化と設定を持ちながら一貫性を保つ

**Independent Test**: 各環境のコンテナを個別にビルド・実行し、適切なツールセットのみが含まれることを確認

### Implementation for User Story 3

- [X] T027 [P] [US3] Create CI environment Dockerfile in dockerfiles/ci/Dockerfile with minimal Python toolchain (uv, pytest, ruff, coverage)
- [X] T028 [P] [US3] Create CI environment Makefile in dockerfiles/ci/Makefile with test-full, coverage, security-scan targets
- [X] T029 [P] [US3] Create production environment Dockerfile in dockerfiles/prod/Dockerfile with multi-stage build and minimal runtime
- [X] T030 [P] [US3] Create production environment Makefile in dockerfiles/prod/Makefile with secure deployment targets
- [X] T031 [US3] Configure environment-specific Docker build args and runtime options for each environment type
- [X] T032 [US3] Implement CI-specific optimizations (read-only volumes, security caps, tmpfs) in dockerfiles/ci/Makefile
- [X] T033 [US3] Implement production security hardening (read-only filesystem, non-root user, health checks) in dockerfiles/prod/Dockerfile
- [X] T034 [US3] Add environment-specific image tagging and registry operations in each Makefile
- [X] T035 [US3] Configure resource and security constraints appropriate for each environment type

**Checkpoint**: All three environments (dev/ci/prod) should now be independently functional

---

## Phase 6: User Story 4 - 開発ワークフロー統合 (Priority: P2)

**Goal**: コンテナ化環境でテスト、リント、デバッグ、ビルドなどの開発タスクが統合されたワークフローで実行できる

**Independent Test**: 各開発ワークフロータスクを個別実行し、期待される結果を合理的な時間内で得られることを確認

### Implementation for User Story 4

- [X] T036 [P] [US4] Add code quality targets (lint, format, check) to dockerfiles/dev/Makefile using ruff and mypy
- [X] T037 [P] [US4] Add testing targets (unittest, only-test) to dockerfiles/dev/Makefile with pytest integration
- [X] T038 [P] [US4] Add AI development tool integration targets (claude-code, codex, gemini) in dockerfiles/dev/Makefile
- [X] T039 [US4] Configure hot reload functionality with file watching patterns in development environment
- [X] T040 [US4] Add container lifecycle management targets (restart, logs, stats) to all environment Makefiles
- [X] T041 [US4] Implement debugging workflow with remote debugpy setup and port forwarding
- [X] T042 [US4] Add development environment health checks and validation targets
- [X] T043 [US4] Configure parallel execution support for independent development tasks

**Checkpoint**: All user stories should now be independently functional with integrated workflows

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T044 [P] Create comprehensive troubleshooting section in quickstart.md with common Docker issues
- [ ] T045 [P] Add performance monitoring targets and resource usage validation
- [ ] T046 [P] Implement container cleanup and reset procedures across all environments
- [ ] T047 [P] Add build optimization with BuildKit cache mounts and multi-stage efficiency
- [ ] T048 [P] Create environment validation and health check procedures
- [ ] T049 [P] Document team deployment and CI/CD integration workflows
- [ ] T050 Run quickstart.md validation with full 10-minute setup workflow testing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Can integrate with US1 but should be independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses US2 templates but should be independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Uses US1 dev environment but should be independently testable

### Within Each User Story

- Infrastructure before implementation (Dockerfiles before Makefiles)
- Base environment before specialized tools
- Configuration before runtime integration
- Core functionality before workflow integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Dockerfiles and Makefiles for different environments marked [P] can run in parallel
- Template files marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all Dockerfiles and Makefiles for User Story 1 together:
Task: "Create development environment Dockerfile in dockerfiles/dev/Dockerfile"
Task: "Create development environment Makefile in dockerfiles/dev/Makefile"
```

## Parallel Example: User Story 2

```bash
# Launch all environment templates together:
Task: "Create development environment template in dockerfiles/templates/.env.dev.template"
Task: "Create CI environment template in dockerfiles/templates/.env.ci.template"
Task: "Create production environment template in dockerfiles/templates/.env.prod.template"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only - Both P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (標準化された開発環境)
4. Complete Phase 4: User Story 2 (セキュアな設定管理)
5. **STOP and VALIDATE**: Test both P1 user stories independently
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Basic MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Secure MVP!)
4. Add User Story 3 → Test independently → Deploy/Demo (Multi-env support!)
5. Add User Story 4 → Test independently → Deploy/Demo (Full workflow!)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (標準化された開発環境)
   - Developer B: User Story 2 (セキュアな設定管理)
   - Developer C: User Story 3 (多環境サポート)
   - Developer D: User Story 4 (開発ワークフロー統合)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Focus on Docker, Makefile, and environment template files as primary deliverables
- AI development tools only in dev environment per specification
- Environment templates use placeholder format [VALUE] for security
- All make commands should work from project root using `-C dockerfiles/[env]` format