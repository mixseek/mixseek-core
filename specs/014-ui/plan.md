# Implementation Plan: Mixseek 実行・結果 UI - ラウンド進捗機能追加

**Branch**: `076-ui` | **Date**: 2025-11-13 | **Spec**: [spec.md](./spec.md)
**Input**: コミットa96f2e1で追加されたラウンド進捗とチームサブミッション追跡機能

## Summary

コミットa96f2e1で追加された要件に対する実装計画:
- **実行ページ拡張**: ページ上部にラウンド進捗表示、チーム進捗一覧領域、タスク/サブミッションのタブインターフェース
- **結果ページ拡張**: ラウンド進捗タイムライン、全チームのスコア推移グラフ（折れ線）
- **データソース**: mixseek.dbの既存テーブル（`round_status`, `leader_board`）から読み取り
  - **重要**: research.mdの調査により、新規テーブル不要と判明

技術アプローチ: Streamlitを使用したシンプルなUI実装、DuckDBからのデータ読み取り、Plotlyによるグラフ可視化

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**:
- streamlit >= 1.40.0 (UI framework)
- duckdb >= 1.3.1 (database access)
- altair >= 5.0.0 or plotly >= 5.0.0 (visualization, research needed)
- pandas >= 2.3.0 (data manipulation)

**Storage**: mixseek.db (DuckDB) - 既存データベース、読み取り専用アクセス
**Testing**: pytest >= 8.3.4
**Target Platform**: Web browser (Streamlit app)
**Project Type**: Web application (Streamlit single-page app)
**Performance Goals**:
- ラウンド進捗表示: 0.5秒以内 (SC-011)
- チーム進捗一覧: 2秒以内 (SC-012)
- タブ切り替え: 0.3秒以内 (SC-013)
- スコア推移グラフ: 3秒以内 (SC-009)

**Constraints**:
- mixseek.dbへの読み取り専用アクセス（書き込み不可）
- 既存の実行ページ・結果ページのレイアウトを保持
- データが存在しない場合のエラーハンドリング必須

**Scale/Scope**:
- 50チーム × 10ラウンド分のデータ表示
- タブ数: 最大50チーム（スクロール対応）
- グラフ凡例: 50チーム対応（折りたたみ機能）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 1: Library-First Principle
**Status**: ✅ PASS
**Rationale**: UI機能はStreamlitフレームワークを直接使用し、ライブラリとして独立実装不要

### Article 3: Test-First Imperative
**Status**: ⚠ ATTENTION REQUIRED
**Rationale**: UIテストは実装前にテスト設計が必要

### Article 4: Documentation Integrity
**Status**: ✅ PASS
**Rationale**: spec.mdに詳細な機能要件（FR-009, FR-020～FR-024）が定義済み

### Article 8: Code Quality Standards
**Status**: ✅ PASS
**Rationale**: ruff + mypy による品質チェック必須

### Article 9: Data Accuracy Mandate
**Status**: ✅ PASS
**Rationale**: すべてのデータはmixseek.dbから明示的に読み取り、ハードコード禁止

### Article 10: DRY Principle
**Status**: ⚠ ATTENTION REQUIRED
**Rationale**: 既存の実行ページ・結果ページのコードを確認し、重複を避ける必要あり

### Article 14: SpecKit Framework Consistency
**Status**: N/A
**Rationale**: UIレイヤーの機能追加であり、MixSeek-Coreフレームワーク自体の変更なし

### Article 16: Python Type Safety Mandate
**Status**: ✅ PASS
**Rationale**: すべてのコードに型注釈を付与し、mypy strict modeでチェック

## Project Structure

### Documentation (this feature)

```
specs/014-ui/
├── spec.md              # Feature specification (updated)
├── plan.md              # This file
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```
# 実装対象: mixseek パッケージ内の ui サブパッケージ
src/mixseek/
├── ui/                          # Streamlit UI components (NEW/MODIFY)
│   ├── pages/
│   │   ├── 1_execution.py       # 実行ページ (MODIFY - ラウンド進捗、チーム進捗、タブ追加)
│   │   ├── 2_results.py         # 結果ページ (MODIFY - ラウンド進捗タイムライン、スコア推移グラフ追加)
│   │   └── 3_history.py         # 履歴ページ (既存)
│   ├── components/               # Reusable UI components
│   │   ├── round_progress.py    # ラウンド進捗表示コンポーネント (NEW)
│   │   ├── team_progress.py     # チーム進捗一覧コンポーネント (NEW)
│   │   ├── submission_tabs.py   # タスク/サブミッションタブコンポーネント (NEW)
│   │   ├── round_timeline.py    # ラウンドタイムラインコンポーネント (NEW)
│   │   └── score_chart.py       # スコア推移グラフコンポーネント (NEW)
│   ├── services/                 # Data access layer
│   │   ├── round_service.py     # ラウンドデータ取得サービス (NEW)
│   │   └── leaderboard_service.py  # リーダーボードサービス (既存参照・拡張)
│   ├── models/                   # Data models
│   │   └── round_models.py      # ラウンド関連モデル (NEW)
│   └── utils/
│       └── db_utils.py          # DuckDB接続ヘルパー (NEW)
│
tests/
├── ui/                           # UI tests (NEW)
│   ├── test_round_progress.py
│   ├── test_team_progress.py
│   ├── test_submission_tabs.py
│   ├── test_round_timeline.py
│   └── test_score_chart.py
└── integration/
    └── test_round_service.py    # DuckDB integration tests (NEW)

# 既存UI (参考用・別パッケージ)
build/lib/mixseek_ui/            # ビルド成果物 (gitignore対象)
├── pages/                       # 既存実装から再利用パターンを参照
│   ├── 1_execution.py
│   ├── 2_results.py
│   └── 3_history.py
├── components/
│   ├── leaderboard_table.py     # テーブル表示パターン参照
│   └── orchestration_selector.py
└── services/
    └── leaderboard_service.py   # DuckDBアクセスパターン参照
```

**Structure Decision**: mixseekパッケージ内の`ui`サブパッケージとして実装。Streamlitページは番号プレフィックス付き命名規則（`1_execution.py`）に従う。既存UI（`build/lib/mixseek_ui/`）は別パッケージだが、DuckDBアクセスパターンやテーブル表示ロジックを参照して再利用性を確保。

## Complexity Tracking

*No Constitution violations - no justification needed*

## Phase 0: Outline & Research

### Research Tasks

1. **可視化ライブラリの選定**
   - **Task**: Streamlitでの折れ線グラフ実装にAltair vs Plotly vs Matplotlibのどれが最適か調査
   - **Decision Criteria**:
     - インタラクティブ性（凡例折りたたみ、ホバー情報）
     - パフォーマンス（50チーム×10ラウンド）
     - Streamlitとの統合性
   - **Output**: `research.md`に選定ライブラリと理由を記載

2. **DuckDBスキーマの確認**
   - **Task**: mixseek.dbの既存テーブル（`round_status`、`leader_board`）のスキーマを確認
   - **Decision Criteria**:
     - 必要なカラムが存在するか（round_started_at, round_ended_at, score等）
     - データ型が適切か
     - インデックスの有無
     - 新規テーブルの必要性判断
   - **Output**: `research.md`にテーブル構造を記載（✅ 完了：既存テーブルで要件を満たすことを確認）

3. **Streamlitタブ機能のベストプラクティス**
   - **Task**: Streamlitでの動的タブ生成（チーム数に応じた）の実装方法調査
   - **Decision Criteria**:
     - 10チーム以上のタブ表示時のUI/UX
     - パフォーマンス影響
     - スクロール対応
   - **Output**: `research.md`に実装パターンを記載

4. **既存UIコードの調査**
   - **Task**: 既存の実行ページ・結果ページの実装を確認（DRY原則）
   - **Decision Criteria**:
     - 共通化可能なコンポーネント
     - レイアウト構造
     - データ取得パターン
   - **Output**: `research.md`に再利用可能な部分を記載

### Research Output Structure

```markdown
# Research: Mixseek UI ラウンド進捗機能

## 1. 可視化ライブラリの選定

**Decision**: [Altair/Plotly/Matplotlib]

**Rationale**:
- インタラクティブ性: [評価]
- パフォーマンス: [ベンチマーク結果]
- Streamlit統合: [評価]

**Alternatives considered**:
- [他の選択肢と却下理由]

## 2. DuckDB スキーマ

**round_status テーブル**:
```sql
[スキーマ定義]
```

**leader_board テーブル**:
```sql
[スキーマ定義]
```

**新規テーブルの必要性**:
[判断結果]

## 3. Streamlit タブ実装パターン

**Decision**: [実装方法]

**Rationale**: [理由]

**Code Example**:
```python
[サンプルコード]
```

## 4. 既存UIコードの再利用

**共通コンポーネント**:
- [リスト]

**データ取得パターン**:
- [パターン]
```

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**Phase 1で定義するエンティティ**:

**注**: research.mdの調査結果により、新規テーブルは不要。既存の`round_status`と`leader_board`テーブルを使用。

1. **RoundStatus** (from `round_status` table)
   - Fields: execution_id, team_id, team_name, round_number, should_continue, reasoning, confidence_score, round_started_at, round_ended_at, created_at, updated_at
   - Validation: team_id uniqueness per round, round number range (>= 1)
   - 用途: ラウンド進捗追跡（FR-022, FR-023）、タイムライン表示（FR-020）

2. **LeaderboardEntry** (from `leader_board` table)
   - Fields: execution_id, team_id, team_name, round_number, submission_content, submission_format, score, score_details, final_submission, exit_reason, created_at, updated_at
   - Validation: score range (0-100), submission_content not empty
   - 用途: スコア推移グラフ（FR-009, FR-020）、最終サブミッション表示（FR-024）
   - **重要**: カラム名は`score`（`evaluation_score`ではない）

### API Contracts (`contracts/`)

UIはデータベース直接アクセスのため、REST APIは不要。
代わりに、データベースクエリインターフェースを定義:

**File**: `contracts/db_queries.yaml`

**注**: research.mdで定義されたクエリ仕様に基づく。既存の`round_status`と`leader_board`テーブルを使用。

```yaml
# DuckDB Query Contracts

get_current_round_number:
  description: 現在のラウンド番号を取得（FR-022）
  query: |
    SELECT team_id, team_name, round_number
    FROM round_status
    WHERE execution_id = ?
    ORDER BY updated_at DESC
    LIMIT 1
  parameters:
    - execution_id: str
  returns:
    - team_id: str
    - team_name: str
    - round_number: int

get_team_progress_list:
  description: チーム進捗一覧を取得（FR-023）
  query: |
    SELECT team_id, team_name, round_number, round_started_at, round_ended_at
    FROM round_status
    WHERE execution_id = ?
    ORDER BY team_name, round_number
  parameters:
    - execution_id: str
  returns:
    - team_id: str
    - team_name: str
    - round_number: int
    - round_started_at: datetime
    - round_ended_at: datetime

get_round_timeline:
  description: ラウンドタイムライン（開始/終了時刻）を取得（FR-020）
  query: |
    SELECT round_number, round_started_at, round_ended_at
    FROM round_status
    WHERE execution_id = ? AND team_id = ?
    ORDER BY round_number
  parameters:
    - execution_id: str
    - team_id: str
  returns:
    - round_number: int
    - round_started_at: datetime
    - round_ended_at: datetime

get_all_teams_score_history:
  description: 全チームのスコア推移を取得（FR-009, FR-020）
  query: |
    SELECT team_id, team_name, round_number, score
    FROM leader_board
    WHERE execution_id = ?
    ORDER BY team_id, round_number
  parameters:
    - execution_id: str
  returns:
    - team_id: str
    - team_name: str
    - round_number: int
    - score: float

get_team_latest_submission:
  description: チームの最終サブミッションを取得（FR-024）
  query: |
    SELECT submission_content, score, score_details, created_at
    FROM leader_board
    WHERE execution_id = ? AND team_id = ? AND final_submission = TRUE
    ORDER BY round_number DESC
    LIMIT 1
  parameters:
    - execution_id: str
    - team_id: str
  returns:
    - submission_content: str
    - score: float
    - score_details: json
    - created_at: datetime
```

### Quickstart (`quickstart.md`)

**Phase 1で作成する開発者向けガイド**:

```markdown
# Quickstart: Mixseek UI ラウンド進捗機能

## 前提条件

- Python 3.13.9
- uv パッケージマネージャー
- mixseek.db (DuckDB) がワークスペース内に存在すること

## セットアップ

1. 依存関係のインストール:
   ```bash
   uv sync --extra ui
   ```

2. 環境変数の設定:
   ```bash
   export MIXSEEK_WORKSPACE=/path/to/workspace
   ```

3. UIの起動:
   ```bash
   uv run streamlit run src/ui/app.py
   ```

## 開発ガイド

### 新規UIコンポーネントの追加

1. `src/ui/components/`に新規ファイルを作成
2. 型注釈を必須で付与
3. `tests/ui/`に対応するテストファイルを作成

### DuckDBクエリの追加

1. `src/ui/db/queries.py`にクエリ関数を追加
2. `contracts/db_queries.yaml`にクエリ仕様を記載
3. `tests/integration/test_db_queries.py`にテストを追加

## テスト実行

```bash
# 全テスト
pytest

# UIコンポーネントのみ
pytest tests/ui/

# DuckDB統合テストのみ
pytest tests/integration/
```

## コード品質チェック

```bash
ruff check --fix . && ruff format . && mypy .
```
```

### Agent Context Update

Phase 1完了後、以下のコマンドでエージェントコンテキストを更新:

```bash
.specify/scripts/bash/update-agent-context.sh claude
```

追加される技術スタック:
- streamlit >= 1.40.0
- [選定された可視化ライブラリ]
- duckdb >= 1.3.1

## Phase 2: Tasks (NOT created by /speckit.plan)

Phase 2のタスク生成は`/speckit.tasks`コマンドで実行されます。
このplan.mdではPhase 2の内容は記載しません。

## 次のステップ

1. `/speckit.plan`コマンドがPhase 0の研究タスクを実行
2. `research.md`が生成される
3. Phase 1でデザインとコントラクトが完成
4. `/speckit.tasks`コマンドでタスク分解を実行
5. 実装開始

---

**Plan Version**: 1.0
**Created**: 2025-11-13
**Last Updated**: 2025-11-13
