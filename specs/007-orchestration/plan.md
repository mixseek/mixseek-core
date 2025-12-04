# Implementation Plan: MixSeek-Core Orchestrator - マルチチーム協調実行

**Branch**: `025-mixseek-core-orchestration` | **Date**: 2025-11-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-orchestration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

オーケストレータはユーザプロンプトを受け取り、複数チームのラウンドコントローラを起動して並列実行を管理し、各チームの完了を検知してDuckDBに記録を残す。初期実装では1ラウンドのみを実施する仮のラウンドコントローラを作成し、オーケストレータからCLI（`mixseek exec`コマンド）経由で実行できるようにする。既存のLeader Agent実装とDuckDBスキーマを活用し、完全に動作可能な実装を提供する。

## Technical Context

**Language/Version**: Python 3.13.9
**Primary Dependencies**:
- pydantic-ai >=1.3.0（Leader Agent統合）
- duckdb >=1.4.1（データ永続化）
- typer >=0.20.0（CLIフレームワーク）
- pydantic >=2.12.3（データモデル）
- asyncio（並列実行管理）

**Storage**: DuckDB（既存スキーマ活用: `round_history`, `leader_board`テーブル）
**Testing**: pytest（ユニット・統合テストの両方）
**Target Platform**: Linux/macOS（開発環境）
**Project Type**: single（既存mixseek-coreパッケージ内に実装）
**Performance Goals**:
- チーム起動レイテンシ < 10秒（SC-001）
- DuckDB記録完了 < 60秒（SC-002）
- 複数チーム並列実行対応（asyncio.gather使用）

**Constraints**:
- 既存DuckDBスキーマ（specs/008-leader/contracts/database-schema.sql）に準拠
- 既存AggregationStore（src/mixseek/storage/aggregation_store.py）を活用
- 初期実装は1ラウンドのみ（将来的に複数ラウンド対応を考慮した設計）

**Scale/Scope**:
- 複数チーム（1〜10チーム想定）の並列実行
- 1チームあたり1ラウンド（初期実装）
- CLIコマンド`mixseek exec`での実行

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Applicable Articles

- **Article 3 (Test-First Imperative)**: ✅ PASS
  - ユニットテスト: Orchestrator、RoundController、Modelsのテスト作成
  - 統合テスト: CLIコマンドのE2Eテスト作成
  - 実装前にテストを作成し、Redフェーズを確認

- **Article 4 (Documentation Integrity)**: ✅ PASS
  - 仕様（specs/007-orchestration/spec.md）との完全な整合性を維持
  - FR-001〜FR-010の機能要件を完全に実装
  - 仕様の不明点はユーザに確認済み

- **Article 8 (Code Quality Standards)**: ✅ PASS
  - ruff、mypy実行を必須化
  - コミット前に品質チェック実施
  - 型注釈完備

- **Article 9 (Data Accuracy Mandate)**: ✅ PASS
  - 環境変数MIXSEEK_WORKSPACEを使用（既存AggregationStoreと同様）
  - ハードコード禁止（タイムアウト値等はTOML設定から読み込み）
  - 明示的エラー処理

- **Article 10 (DRY Principle)**: ✅ PASS
  - 既存AggregationStore（src/mixseek/storage/aggregation_store.py）を再利用
  - 既存DuckDBスキーマ（specs/008-leader/contracts/database-schema.sql）を活用
  - 重複実装なし

- **Article 14 (SpecKit Framework Consistency)**: ✅ PASS
  - MixSeek-Core親仕様（specs/001-specs/spec.md）との整合性確認済み
  - Leader Agent仕様（specs/008-leader/spec.md）と連携
  - TUMIX由来のラウンドベース処理アーキテクチャに準拠

- **Article 16 (Python Type Safety Mandate)**: ✅ PASS
  - 全関数・メソッドに型注釈を付与
  - mypy strict mode対応
  - Pydantic Modelで型安全性を保証

### Gates Evaluation

すべてのArticleがPASSしており、Phase 0 Researchに進むことができます。

## Project Structure

### Documentation (this feature)

```
specs/007-orchestration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── orchestrator-api.md
│   ├── round-controller-api.md
│   └── cli-interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
src/mixseek/
├── orchestrator/                 # 新規ディレクトリ
│   ├── __init__.py
│   ├── orchestrator.py          # Orchestratorクラス（複数チーム管理）
│   ├── round_controller.py      # RoundControllerクラス（1ラウンド仮実装）
│   └── models.py                # OrchestratorTask, TeamStatus, ExecutionSummary
├── cli/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── exec.py              # 新規: mixseek execコマンド
│   │   ├── init.py              # 既存
│   │   ├── team.py              # 既存
│   │   └── ...
│   └── main.py                  # 既存（execコマンド登録追加）
├── storage/                     # 既存ディレクトリ
│   ├── __init__.py
│   └── aggregation_store.py    # 既存（再利用）
├── agents/                      # 既存
│   └── leader/
│       └── ...                  # 既存Leader Agent実装
└── models/                      # 既存
    ├── config.py                # 既存（チーム設定読み込み）
    └── ...

tests/
├── unit/
│   └── orchestrator/            # 新規ディレクトリ
│       ├── test_orchestrator.py
│       ├── test_round_controller.py
│       └── test_models.py
└── integration/
    └── test_orchestrator_e2e.py # 新規（CLIコマンドE2Eテスト）
```

**Structure Decision**:

Option 1（Single project）を選択。既存のmixseek-coreパッケージ構造を維持し、`src/mixseek/orchestrator/`ディレクトリを新規追加。CLI コマンドは既存の`src/mixseek/cli/commands/`に`exec.py`を追加する形で統合。既存の`storage/aggregation_store.py`と`agents/leader/`を活用することで、DRY原則（Article 10）を遵守。

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

Constitution Checkですべてのゲートがパスしているため、正当化が必要な違反はありません。
