# Tasks: Mixseek UI ラウンド進捗機能追加

**Feature**: 076-ui | **Branch**: `076-ui`
**Input**: Design documents from `/home/driller/repo/dseek_for_drillan/specs/014-ui/`
**Prerequisites**: plan.md, spec.md, research.md

**Context**: 既存の実装（`build/lib/mixseek_ui/`のパターン）に留意し、`src/mixseek/ui/`に新規機能を追加します。

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US5)
- Include exact file paths in descriptions

## Path Conventions
- **Implementation**: `src/mixseek/ui/` (mixseekパッケージのuiサブパッケージ)
- **Tests**: `tests/ui/`, `tests/integration/`
- **Reference**: `build/lib/mixseek_ui/` (既存UIパターン参照用)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: ラウンド進捗機能の実装に必要な共通基盤の構築

- [X] T001 [P] pyproject.tomlにPlotly依存関係を追加 (`plotly>=6.0.0`)
- [X] T002 [P] src/mixseek/ui/models/ ディレクトリ構造確認（既存の場合はスキップ）
- [X] T003 [P] src/mixseek/ui/services/ ディレクトリ構造確認（既存の場合はスキップ）
- [X] T004 [P] src/mixseek/ui/components/ ディレクトリ作成（存在しない場合）
- [X] T005 [P] src/mixseek/ui/utils/ ディレクトリ作成（存在しない場合）
- [X] T006 [P] tests/ui/ ディレクトリ作成
- [X] T007 [P] tests/integration/ ディレクトリ確認（既存の場合はスキップ）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 全ユーザーストーリーで共通使用するデータモデルとデータベースアクセス基盤

**⚠️ CRITICAL**: このフェーズ完了後、各ユーザーストーリーの並列実装が可能

### データモデル定義

- [X] T008 [P] `RoundProgress` Pydanticモデルを `src/mixseek/ui/models/round_models.py` に作成
  - Fields: team_id, team_name, round_number, round_started_at, round_ended_at
  - `from_db_row()` クラスメソッド実装
  - 型注釈必須、mypy strict mode準拠

- [X] T009 [P] `TeamScoreHistory` Pydanticモデルを `src/mixseek/ui/models/round_models.py` に追加
  - Fields: team_id, team_name, round_number, score
  - `from_db_row()` クラスメソッド実装

- [X] T010 [P] `TeamSubmission` Pydanticモデルを `src/mixseek/ui/models/round_models.py` に追加
  - Fields: team_id, team_name, round_number, submission_content, score, score_details, created_at, final_submission
  - `from_db_row()` クラスメソッド実装

### データベースアクセス基盤

- [X] T011 DuckDB接続ヘルパーを `src/mixseek/ui/utils/db_utils.py` に作成
  - `get_workspace_path()` 関数（環境変数 MIXSEEK_WORKSPACE 読み取り、Article 9準拠）
  - `get_db_connection()` 関数（mixseek.db接続）
  - エラーハンドリング（DBファイル不在時は None 返却、エラー投げない）
  - 既存 `build/lib/mixseek_ui/services/leaderboard_service.py` のパターン参照

- [X] T012 ラウンドデータサービスを `src/mixseek/ui/services/round_service.py` に作成
  - `fetch_current_round_progress(execution_id: str) -> RoundProgress | None`
    - round_statusテーブルから最新ラウンド取得（research.md クエリ1参照）
  - `fetch_team_progress_list(execution_id: str) -> list[RoundProgress]`
    - 全チーム進捗一覧取得（research.md クエリ2参照）
  - `fetch_round_timeline(execution_id: str, team_id: str) -> list[RoundProgress]`
    - ラウンドタイムライン取得（research.md クエリ3参照）
  - `fetch_all_teams_score_history(execution_id: str) -> pd.DataFrame`
    - leader_boardから全チームスコア推移取得（research.md クエリ4参照）
  - `fetch_team_final_submission(execution_id: str, team_id: str) -> TeamSubmission | None`
    - 最終サブミッション取得（research.md クエリ5参照）
  - 既存 `build/lib/mixseek_ui/services/leaderboard_service.py` のDuckDBアクセスパターン参照

**Checkpoint**: 基盤完成 - 各ユーザーストーリーの並列実装可能

---

## Phase 3: User Story 1 - タスクを実行する (Priority: P1) 🎯

**Goal**: 実行ページにリアルタイム進捗表示、ラウンド進捗表示、チーム進捗一覧、タスク/サブミッションタブを追加

**Independent Test**: 実行ページを開き、タスク実行中にリアルタイム進捗（Streamlit標準コンポーネント）が表示され、実行完了後にラウンド進捗（"ラウンド 3/10"）、チーム進捗一覧テーブル、タブ（タスク + 各チーム）が表示されることを確認

**対象要件**: FR-004, FR-022, FR-023, FR-024, SC-011, SC-012, SC-013

### リアルタイム進捗表示実装 (FR-004)

- [X] T025 [P] [US1] 実行状態管理モデルを `src/mixseek/ui/models/execution.py` に作成
  - `ExecutionState` Pydanticモデル
    - Fields: execution_id, status (PENDING/RUNNING/COMPLETED/FAILED), current_round, total_rounds, error_message
    - 型注釈必須、mypy strict mode準拠
  - `ExecutionStatus` Enum定義 (PENDING, RUNNING, COMPLETED, FAILED)

- [X] T026 [US1] バックグラウンド実行サービスを `src/mixseek/ui/services/execution_service.py` に修正
  - `run_orchestration_in_background(prompt: str, orchestration_option: OrchestrationOption) -> str`
    - threadingを使用してオーケストレーション実行を別スレッドで開始
    - 実行開始時にグローバル辞書_execution_statesをRUNNINGに設定
    - execution_idを生成して返却
  - `get_execution_status(execution_id: str) -> ExecutionState`
    - mixseek.dbのround_statusテーブルから現在の実行状態を取得
    - 現在ラウンド、総ラウンド数を計算
  - エラー時はExecutionState.status=FAILEDに設定、error_messageを記録
  - 既存のオーケストレーション実行ロジックを保持

- [X] T027 [US1] リアルタイム進捗表示コンポーネントを `src/mixseek/ui/components/realtime_progress.py` に作成
  - `render_realtime_progress(execution_id: str) -> None`
    - Streamlit標準コンポーネント使用:
      - `st.status()` でステータス表示（実行中/完了/エラー）
      - `st.progress()` で進捗バー表示（current_round / total_rounds）
      - `st.metric()` で現在ラウンド表示（例: "ラウンド 3/10"）
    - `get_execution_status()` を呼び出して実行状態取得
    - ステータスがRUNNINGの場合のみ表示
    - エラー時は `st.error()` でエラーメッセージ表示

- [X] T028 [US1] 実行ページ `src/mixseek/ui/pages/1_execution.py` にポーリングロジック追加
  - バックグラウンド実行ボタン処理:
    - `run_orchestration_in_background()` を呼び出し
    - st.session_state.current_execution_id に execution_id を保存
    - st.session_state.is_running を True に設定
    - st.session_state.polling_enabled を True に設定
  - ポーリングループ実装:
    - st.session_state.polling_enabled が True の場合:
      - `render_realtime_progress(execution_id)` を表示
      - `get_execution_status(execution_id)` を呼び出し
      - ステータスが COMPLETED または FAILED の場合:
        - st.session_state.polling_enabled を False に設定
        - ポーリング停止
      - ステータスが RUNNING の場合:
        - `time.sleep(2)` で2秒待機
        - `st.rerun()` でページ再レンダリング
  - エラーハンドリング:
    - 実行中エラー発生時は即座にポーリング停止
    - エラーメッセージを明確に表示
    - 実行ボタンを再度有効化

### 実行完了後の詳細表示実装 (FR-022, FR-023, FR-024)

- [X] T013 [P] [US1] ラウンド進捗表示コンポーネント `src/mixseek/ui/components/round_progress.py` を作成
  - `render_round_progress(execution_id: str) -> None`
  - `fetch_current_round_progress()` 呼び出し
  - "ラウンド X/Y" 形式で `st.metric()` 表示
  - データ不在時は何も表示しない（エラーとしない）
  - 既存 `build/lib/mixseek_ui/pages/2_results.py` のメトリック表示パターン参照

- [X] T014 [P] [US1] チーム進捗一覧コンポーネント `src/mixseek/ui/components/team_progress.py` を作成
  - `render_team_progress_list(execution_id: str) -> None`
  - `fetch_team_progress_list()` 呼び出し
  - Pandas DataFrame変換 → `st.dataframe()` 表示
  - カラム: チーム名、現在ラウンド、完了数、開始時刻、終了時刻
  - データ不在時は「チーム進捗データがありません」メッセージ表示
  - 既存 `build/lib/mixseek_ui/components/leaderboard_table.py` のテーブル表示パターン参照

- [X] T015 [P] [US1] タスク/サブミッションタブコンポーネント `src/mixseek/ui/components/submission_tabs.py` を作成
  - `render_submission_tabs(execution_id: str, user_prompt: str, teams: list) -> None`
  - `st.tabs()` で動的タブ生成（["タスク"] + チーム名リスト）
  - タスクタブ: `st.text_area()` でプロンプト表示（disabled=True）
  - 各チームタブ: `fetch_team_final_submission()` 呼び出し、サブミッション表示
  - データ不在時は「サブミッションデータがありません」メッセージ
  - research.md の Streamlitタブ実装パターン参照

- [X] T029 [US1] 実行ページ `src/mixseek/ui/pages/1_execution.py` にUI表示ロジック追加
  - 実行中の表示:
    - `render_realtime_progress(execution_id)` を上部に表示
    - 詳細表示エリア（進捗確認、タブ）は非表示
  - 実行完了後の表示:
    - リアルタイム進捗を非表示
    - ページ上部に `render_round_progress(execution_id)` 追加（既存レイアウト保持）
    - 進捗確認領域を追加 `st.subheader("進捗確認")` + `render_team_progress_list(execution_id)`
    - タブエリアを追加 `st.divider()` + `render_submission_tabs(execution_id, prompt, teams)`
  - セッション状態から `execution_id`、`prompt`、`execution_status` 取得
  - 既存 `build/lib/mixseek_ui/pages/1_execution.py` のレイアウト構造を保持

**Checkpoint**: User Story 1完了 - 実行ページのリアルタイム進捗とラウンド進捗機能が独立して動作可能

---

## Phase 4: User Story 5 - ラウンド進捗とスコア推移を確認する (Priority: P2)

**Goal**: 結果ページにラウンドタイムライン、全チームスコア推移グラフを追加

**Independent Test**: 結果ページを開き、ラウンドタイムライン（各ラウンドの開始/終了時刻）、スコア推移折れ線グラフ（50チーム対応、凡例折りたたみ可能）が表示されることを確認

**対象要件**: FR-009, FR-020, FR-021, SC-008, SC-009, SC-010

### 実装 for User Story 5

- [X] T017 [P] [US5] ラウンドタイムラインコンポーネント `src/mixseek/ui/components/round_timeline.py` を作成
  - `render_round_timeline(execution_id: str, team_id: str) -> None`
  - `fetch_round_timeline()` 呼び出し
  - Pandas DataFrame変換 → `st.dataframe()` 表示
  - カラム: ラウンド番号、開始時刻、終了時刻
  - タイムライン形式で時系列表示
  - データ不在時は「ラウンドデータがありません。ラウンドコントローラによる実行後に表示されます」メッセージ
  - 既存 `build/lib/mixseek_ui/components/leaderboard_table.py` のテーブル表示パターン参照

- [X] T018 [P] [US5] スコア推移グラフコンポーネント `src/mixseek/ui/components/score_chart.py` を作成
  - `render_score_chart(execution_id: str) -> None`
  - `fetch_all_teams_score_history()` 呼び出し
  - Plotly Express折れ線グラフ作成（research.md 実装例参照）
    - `px.line(df, x="round_number", y="score", color="team_name")`
    - `hover_data=["team_id"]` でホバー情報追加
    - `st.plotly_chart(fig, use_container_width=True)` で表示
  - 凡例のクリックで系列表示/非表示切り替え（Plotlyネイティブ機能）
  - WebGL自動有効化（1000+データポイント）
  - データ不在時は「スコア推移データがありません」メッセージ

- [X] T019 [US5] 結果ページ `src/mixseek/ui/pages/2_results.py` を修正
  - リーダーボード下に `st.divider()` 追加
  - ラウンド進捗エリア追加:
    - `st.subheader("ラウンド進捗")`
    - `render_round_progress(execution_id)` （現在ラウンド表示）
    - `render_round_timeline(execution_id, top_team_id)` （タイムライン表示）
  - スコア推移エリア追加:
    - `st.divider()`
    - `st.subheader("スコア推移")`
    - `render_score_chart(execution_id)`
  - 既存のリーダーボード表示を保持（FR-009のプレースホルダー削除）
  - 既存 `build/lib/mixseek_ui/pages/2_results.py` のレイアウト構造を保持（行100-103のプレースホルダーを実装で置き換え）

**Checkpoint**: User Story 5完了 - 結果ページのラウンド進捗・スコア推移機能が独立して動作可能

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: コード品質、エラーハンドリング、パフォーマンス最適化

- [X] T020 [P] 全コンポーネントに型注釈を追加・確認（mypy strict mode準拠）
- [X] T021 [P] エラーハンドリング強化
  - DuckDB接続失敗時の明示的メッセージ
  - クエリエラー時のログ出力
  - データ型不一致時の型変換エラー処理

- [X] T022 [P] コード品質チェック実行
  - `ruff check --fix .`
  - `ruff format .`
  - `mypy src/mixseek/ui/`
  - すべてのエラー・警告を解決

- [X] T023 [P] ドキュメント文字列追加
  - 全関数にGoogle-style docstring追加
  - Args, Returns, Raises セクション記載
  - 使用例コメント追加（複雑な関数）

- [X] T030 最終確認
  - 全ファイルの作成確認
  - リアルタイム進捗機能の動作確認
  - 型チェック・リント合格確認（ruff check --fix, ruff format, mypy）
  - tasks.md更新

---

## Dependencies & Execution Strategy

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← すべてのUSの前提条件
    ↓
  ┌─┴─┐
  ↓   ↓
[US1] [US5]  ← 並列実装可能（異なるファイル）
  ↓   ↓
  └─┬─┘
    ↓
Phase 5 (Polish)
```

**並列実装可能な組み合わせ**:
- Phase 2完了後: US1 (T025-T029) と US5 (T017-T019) を並列実装可能
- Phase 5内: T020-T023, T030 すべて並列実行可能

### Parallel Execution Examples

**Phase 2 (Foundational)**:
```bash
# モデル定義（並列可能）
T008, T009, T010 を並列実行

# サービス実装（T011完了後）
T012 実行（T011に依存）
```

**Phase 3 (US1) + Phase 4 (US5)**:
```bash
# US1とUS5は異なるファイルのため並列可能
並列グループ1: T025, T027 (US1のモデル・コンポーネント)
並列グループ2: T017, T018 (US5のコンポーネント)

# サービス・ページ修正（順次実行）
T026 (execution_service.py 修正)
T028 (1_execution.py ポーリング追加)
T029 (1_execution.py UI表示ロジック追加)
T019 (2_results.py 修正)
```

**Phase 5 (Polish)**:
```bash
# すべて並列実行可能
T020, T021, T022, T023, T030 を並列実行
```

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**推奨MVP**: User Story 1のリアルタイム進捗表示
- タスク実行中のリアルタイム進捗表示（Streamlit標準コンポーネント）
- 実行完了後のラウンド進捗表示
- チーム進捗一覧
- タスク/サブミッションタブ
- **独立価値**: 実行中のリアルタイム状況が可視化され、即座に価値提供

### Incremental Delivery

1. **Sprint 1**: Phase 1 + Phase 2 (基盤構築)
2. **Sprint 2**: Phase 3 (US1 - リアルタイム進捗 + 実行ページ拡張) → MVP完成
3. **Sprint 3**: Phase 4 (US5 - 結果ページ拡張)
4. **Sprint 4**: Phase 5 (品質向上)

---

## Task Summary

**Total Tasks**: 30

**Task Count by Phase**:
- Phase 1 (Setup): 7 tasks (すべて完了)
- Phase 2 (Foundational): 5 tasks (すべて完了)
- Phase 3 (US1): 8 tasks (4完了、4新規 - リアルタイム進捗)
- Phase 4 (US5): 3 tasks (すべて完了)
- Phase 5 (Polish): 7 tasks (4完了、3新規)

**Task Count by User Story**:
- US1 (タスク実行): 8 tasks (T013-T015, T025-T029)
  - リアルタイム進捗: 4 tasks (T025-T028)
  - 実行完了後の詳細表示: 4 tasks (T013-T015, T029)
- US5 (ラウンド進捗・スコア推移): 3 tasks (T017-T019)

**New Tasks (リアルタイム進捗表示)**:
- T025: 実行状態管理モデル作成
- T026: バックグラウンド実行サービス修正
- T027: リアルタイム進捗表示コンポーネント作成
- T028: 実行ページにポーリングロジック追加
- T029: 実行ページにUI表示ロジック追加
- T030: 最終確認

**Parallel Opportunities**:
- Phase 1: 7 tasks すべて並列可能 (完了)
- Phase 2: 3 tasks (T008, T009, T010) 並列可能 (完了)
- Phase 3 + Phase 4: US1とUS5のコンポーネント作成を並列可能（最大4タスク: T025, T027, T017, T018）
- Phase 5: 5 tasks すべて並列可能

**Independent Test Criteria**:
- US1: 実行ページ単体で、タスク実行中にリアルタイム進捗が2秒間隔で更新され、実行完了後にラウンド進捗・チーム進捗・タブが表示され操作可能
- US5: 結果ページ単体で、ラウンドタイムライン・スコア推移グラフが表示されインタラクティブ操作可能

**Estimated Effort**:
- Setup + Foundational: 完了
- US1 Realtime Progress (New): 4-5時間
- US1 Post-Execution Display: 完了
- US5 Implementation: 完了
- Polish: 1-2時間
- **Remaining**: 5-7時間

---

**Tasks Version**: 2.0 (リアルタイム進捗表示追加)
**Generated**: 2025-11-13
**Next Step**: Phase 3 リアルタイム進捗表示タスク (T025-T029) から実装開始
