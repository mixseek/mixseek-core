# Implementation Plan: Round Controller - ラウンドライフサイクル管理

**Branch**: `012-round-controller` | **Date**: 2025-11-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-round-controller/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

既存の`025-mixseek-core-orchestration`で実装されたRound Controllerを、本仕様(`012-round-controller`)に従って置き換えます。主な変更点は以下の通りです：

1. **複数ラウンド反復改善の実装**: 単一ラウンドから複数ラウンド対応への拡張。各ラウンド終了後、LLMによる改善見込み判定を実行し、次ラウンド継続または終了を決定します。
2. **最終戻り値の変更**: Round Controllerは複数ラウンドを実行し、**最高スコアのラウンドの`LeaderBoardEntry`**をOrchestratorに返します（FR-007準拠）。既存の`RoundResult`は使用しません。
3. **ラウンド設定のタスク統合**: 独立したTOML設定ファイルを廃止し、オーケストレータから受け取るタスク(`OrchestratorTask`)に最大ラウンド数、最小ラウンド数、各種タイムアウト設定を統合します。
4. **DuckDBスキーマ拡張**: `round_status`テーブルに改善見込み判定結果（should_continue、reasoning、confidence_score）を統合し、`leader_board`テーブルにexecution_id、final_submission、exit_reasonカラムを追加します。
5. **スコアスケール変更**: 既存の0-1スケールから、Evaluatorが返す0-100スケールをそのまま使用するよう変更します。
6. **プロンプト整形の拡張**: 各ラウンドでチームに送信するプロンプトに、過去のSubmission履歴、評価フィードバック、leader_boardのランキング情報を統合します。

技術的アプローチ：既存の実装（`src/mixseek/orchestrator`、`src/mixseek/round_controller`）をベースに、本仕様で必要な変更を最小限に抑えつつ、新機能を追加します。既存のテストを維持し、新仕様の要件を検証するテストを追加します。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**: Pydantic AI (Direct Model Request API)、DuckDB 1.0以降、Pydantic 2.x
**Storage**: DuckDB（`$MIXSEEK_WORKSPACE/mixseek.db`、MVCC並列書き込みサポート）
**Testing**: pytest（ユニットテスト、統合テスト、E2Eテスト）
**Target Platform**: Linux server（Docker環境）
**Project Type**: single（既存mixseek-coreパッケージの拡張）
**Performance Goals**:
- 単一チーム・単一ラウンド実行: タスク受信からDuckDB保存完了まで30秒以内（95パーセンタイル、SC-001）
- 複数ラウンド（5ラウンド）実行: 各ラウンドの評価結果およびexecution_idを100%正確にDuckDBに記録（SC-002）
- 複数チーム（5チーム）並列実行: すべてのチームのレコードを競合なくDuckDBに保存（成功率100%、SC-003）

**Constraints**:
- DuckDB書き込み失敗時の3回リトライ（エクスポネンシャルバックオフ: 1秒、2秒、4秒）
- 全リトライ失敗時はチーム全体を失格として扱う
- LLM改善見込み判定の精度80%以上（手動評価との一致率、SC-004）
- プロンプトにleader_boardランキング情報を100%正確に含める（SC-007）

**Scale/Scope**:
- 最大5チーム並列実行（典型的なユースケース）
- 最大5ラウンド反復改善（設定可能）
- DuckDBテーブル: `round_status`、`leader_board`（新規作成）
- 既存コード影響範囲: `src/mixseek/orchestrator`、`src/mixseek/round_controller`、`src/mixseek/storage`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 3: Test-First Imperative ✅ PASS
- **要件**: 実装前にテストを作成し、ユーザー承認を取得し、Redフェーズを確認する
- **適用**: 既存テスト（`tests/unit/round_controller/`、`tests/unit/orchestrator/`）を用いて既存実装の挙動を保証する。新仕様の要件を検証するテストを追加する
- **判定**: 既存テストの保持および新規テスト追加により準拠

### Article 4: Documentation Integrity ✅ PASS
- **要件**: 実装は仕様との完全な整合性を保つ
- **適用**: 本plan.mdは`specs/012-round-controller/spec.md`に基づいて作成される。実装時は仕様の全機能要件（FR-001～FR-013）を満たす
- **判定**: 仕様書を基準とした実装により準拠

### Article 8: Code Quality Standards ✅ PASS
- **要件**: コミット前に`ruff check --fix . && ruff format . && mypy .`を実行し、全エラーを解消する
- **適用**: 実装完了後、コミット前に品質チェックを実行する
- **判定**: 品質チェック実行により準拠

### Article 9: Data Accuracy Mandate ✅ PASS
- **要件**: データは明示的なソースから取得し、推測・フォールバック・ハードコードを禁止する
- **適用**:
  - ラウンド設定（最大ラウンド数、最小ラウンド数、タイムアウト）は`OrchestratorTask`から明示的に受け取る
  - 環境変数`MIXSEEK_WORKSPACE`は既存実装で検証済み
  - リトライ回数（3回）、バックオフ時間（1秒、2秒、4秒）は名前付き定数として定義する
- **判定**: 明示的データソース指定により準拠

### Article 10: DRY Principle ✅ PASS
- **要件**: 実装前に既存コードを検索し、重複を避ける
- **適用**:
  - 既存の`src/mixseek/orchestrator/orchestrator.py`（単一ラウンド実装）を拡張する
  - 既存の`src/mixseek/round_controller/controller.py`を複数ラウンド対応に置き換える
  - Evaluator実装（`src/mixseek/evaluator`）のLLM-as-a-Judge手法を参考に改善見込み判定を実装する
- **判定**: 既存実装の再利用および参考により準拠

### Article 14: SpecKit Framework Consistency ✅ PASS
- **要件**: すべてのSpecKitコマンドは`specs/001-specs`と整合性を保つ
- **適用**:
  - 親仕様の`specs/001-specs/spec.md`のFR-006（ラウンドベース処理）、FR-007（Round Controllerの責務）、FR-011（ラウンド終了インターフェース）に準拠
  - 本仕様は親仕様のRound Controller責務を具体化したものであり、MixSeek-Coreアーキテクチャとの整合性を保つ
- **判定**: 親仕様準拠により整合性を確保

### Article 16: Python Type Safety Mandate ✅ PASS
- **要件**: すべての関数・メソッドに型注釈を付与し、mypy strict設定で型チェックを実行する
- **適用**: Pydantic Modelによる型安全なデータ構造定義、全関数に型注釈を追加
- **判定**: 型注釈とmypy型チェックにより準拠

### Article 17: Python Docstring Standards ✅ PASS (推奨)
- **要件**: Google-style docstringによる包括的なドキュメント（推奨事項）
- **適用**: 公開関数・クラスにdocstringを記述する
- **判定**: docstring記述により品質向上を図る（推奨事項として実施）

### 全体判定: ✅ PASS
すべての非交渉的原則（Article 3, 4, 8, 9, 10, 14, 16）に準拠しています。Phase 0リサーチに進む準備が整いました。

## Project Structure

### Documentation (this feature)

```
specs/012-round-controller/
├── spec.md              # 機能仕様書（既存）
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (DuckDBスキーマ定義)
│   └── schema.sql       # round_status、leader_boardテーブルDDL
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
src/mixseek/
├── orchestrator/
│   ├── __init__.py
│   ├── orchestrator.py          # [変更] 各チームからLeaderBoardEntryを受け取る
│   └── models.py                # [変更] OrchestratorTaskにラウンド設定追加、ExecutionSummary.team_resultsをLeaderBoardEntryリストに変更
├── round_controller/
│   ├── __init__.py
│   ├── controller.py            # [大幅変更] 複数ラウンド対応、改善見込み判定、プロンプト整形、最終的にLeaderBoardEntryを返す
│   └── models.py                # [新規] RoundState、ImprovementJudgment等のPydanticモデル
├── storage/
│   ├── __init__.py
│   ├── aggregation_store.py     # [変更] round_status、leader_boardテーブル対応
│   └── schema.py                # [新規] DuckDBスキーマ定義（CREATE TABLE文）
└── models/
    └── leaderboard.py           # [新規] LeaderBoardEntry Pydanticモデル（Round Controllerの戻り値）

tests/
├── unit/
│   ├── round_controller/
│   │   ├── test_round_controller.py           # [変更] 複数ラウンドテスト追加、LeaderBoardEntry戻り値検証
│   │   └── test_improvement_judgment.py       # [新規] 改善見込み判定テスト
│   ├── orchestrator/
│   │   └── test_orchestrator.py               # [変更] ラウンド設定統合テスト、LeaderBoardEntry受け取り検証
│   └── storage/
│       └── test_aggregation_store.py          # [変更] 新テーブル対応テスト
└── integration/
    └── test_orchestrator_e2e.py               # [変更] E2E複数ラウンドテスト、LeaderBoardEntry検証
```

**Structure Decision**:
既存のsingle projectパターンを維持します。主な変更箇所は`src/mixseek/round_controller/`（複数ラウンド対応）と`src/mixseek/storage/`（新DuckDBスキーマ対応）です。既存の`orchestrator`、`models`も部分的に変更します。テストは既存構造を維持しつつ、新仕様の要件を検証するテストを追加します。

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

該当なし（Constitution Checkですべて準拠）
