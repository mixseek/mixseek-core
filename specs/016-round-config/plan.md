# Implementation Plan: Round Configuration in TOML

**Branch**: `feature/101-round-config` | **Date**: 2025-11-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-round-config/spec.md`

## Summary

この機能は、OrchestratorTaskモデルに既に定義されているラウンド実行パラメータ（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）をTOMLファイル経由で設定可能にする。具体的には、OrchestratorSettingsモデルに同等のフィールドを追加し、既存のConfigurationManagerインフラストラクチャを活用して環境変数とTOMLファイルからの設定読み込みをサポートする。これにより、運用者はコード変更なしでマルチラウンド実行の動作を宣言的に調整できる。

**Technical Approach**: Pydantic Settingsの既存インフラストラクチャを再利用し、OrchestratorSettingsにフィールドを追加、Orchestratorクラスでタスク作成時に設定値を渡すという最小限の変更で実現する。

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Pydantic Settings (v2.x), pydantic (v2.x)
**Storage**: N/A (TOML設定ファイルのみ)
**Testing**: pytest (既存テストインフラ使用)
**Target Platform**: Linux/macOS (開発環境: Docker devコンテナ)
**Project Type**: single (mixseek-coreパッケージ内の設定拡張)
**Performance Goals**: 設定読み込み時間 < 1秒、バリデーションエラー検出時間 < 1秒
**Constraints**: 既存orchestrator.tomlファイルとの後方互換性維持、既存のConfigurationManagerインフラを変更しない
**Scale/Scope**: 4つの設定フィールド追加、2ファイル変更、約100行のコード追加（テスト含む）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article 3: Test-First Imperative ✅

**適用**: 実装前にテストを作成し、ユーザー承認を得た後にRedフェーズを確認する。

**実施計画**:
1. OrchestratorSettings拡張のユニットテスト作成（バリデーション制約、デフォルト値、環境変数優先順位）
2. Orchestrator統合テスト作成（設定値の受け渡し確認）
3. テストをユーザーに提示し、承認を得る
4. テストが失敗することを確認（Redフェーズ）
5. 実装を進める

### Article 4: Documentation Integrity ✅

**適用**: spec.mdとの完全な整合性を保つ。

**実施計画**:
- FR-001～FR-010に定義された要件を実装チェックリストとして使用
- 仕様の曖昧性を検出した場合は実装を停止し、明確化を要求
- SC-001～SC-007の成功基準が検証可能であることを確認

### Article 8: Code Quality Standards ✅

**適用**: コミット前に`ruff check --fix . && ruff format . && mypy .`を実行し、全エラーを解消する。

**実施計画**:
- ruff設定（line length 119、Python 3.13）を遵守
- mypyのstrict modeで型エラーゼロを維持
- 品質チェック失敗時は次工程に進まない

### Article 9: Data Accuracy Mandate ✅

**適用**: デフォルト値を明示的に定義し、マジックナンバーを排除する。

**実施計画**:
- デフォルト値（max_rounds=5、min_rounds=2、submission_timeout_seconds=300、judgment_timeout_seconds=60）をPydantic Fieldで明示的に定義
- 環境変数のフォールバックなしで明示的なエラーメッセージを提供
- OrchestratorTaskの既存デフォルト値と一致させる

### Article 10: DRY Principle ✅

**適用**: 既存のConfigurationManagerインフラストラクチャを再利用し、コードの重複を避ける。

**実施計画**:
- 051-configurationで確立されたTOML読み込みメカニズムを再利用
- 新しい設定読み込みロジックを追加しない
- バリデーションパターンは既存のOrchestratorSettings実装を踏襲

### Article 14: SpecKit Framework Consistency ✅

**適用**: MixSeek-Core仕様（specs/001-specs）との整合性を確認する。

**検証結果**:
- OrchestratorTaskは001-mixseek-core-specsのKey Entitiesで定義されている
- Round Controllerは既にOrchestratorTaskのラウンド設定フィールドを使用している（FR-007）
- 本機能は既存フィールドをTOML経由で公開するのみで、フレームワーク構造を変更しない
- **整合性: OK** - MixSeek-Core仕様からの逸脱なし

### Article 16: Python Type Safety Mandate ✅

**適用**: Pydanticモデルで包括的な型注釈と静的型チェックを実施する。

**実施計画**:
- すべてのフィールドにPydantic Field型注釈を付与
- バリデーション制約（ge、le、gt）を明示的に定義
- mypy strictモードで型エラーゼロを維持

### Complexity Tracking

*No violations - all Constitution requirements are satisfied*

本機能は既存インフラストラクチャの最小限の拡張であり、憲法違反は発生しない。

## Project Structure

### Documentation (this feature)

```
specs/016-round-config/
├── spec.md              # Feature specification (completed)
├── checklists/          # Quality checklists
│   └── requirements.md  # Requirements checklist (completed)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
└── quickstart.md        # Phase 1 output (to be generated)
```

### Source Code (repository root)

```
src/mixseek/
├── config/
│   └── schema.py                  # MODIFY: Add round config fields to OrchestratorSettings
├── orchestrator/
│   ├── orchestrator.py            # MODIFY: Pass round config from settings to OrchestratorTask
│   └── models.py                  # REFERENCE: OrchestratorTask with existing round fields
└── round_controller/
    └── controller.py              # REFERENCE: Uses OrchestratorTask round fields

tests/
├── config/
│   └── test_orchestrator_settings.py  # ADD: Unit tests for round config validation
└── orchestrator/
    └── test_orchestrator.py           # MODIFY: Integration tests for config pass-through
```

**Structure Decision**: Single project structure（既存のmixseek-coreパッケージ内）。本機能は2つの既存モジュールの拡張のみで、新しいモジュール追加は不要。

## Phase 0: Research & Unknowns

**Status**: To be generated in `research.md`

### Research Tasks

1. **Pydantic Settings Field Validation Patterns**: 既存のOrchestratorSettings実装を調査し、フィールドバリデーション（ge、le、gt制約）とmodel_validatorの使用パターンを理解する
2. **Environment Variable Naming Convention**: Pydantic Settingsでの環境変数名の自動生成ルール（MIXSEEK_MAX_ROUNDS等）を確認する
3. **Cross-Field Validation Best Practices**: min_rounds <= max_roundsのような相互検証をPydanticで実装するベストプラクティスを調査する
4. **Orchestrator Configuration Pass-Through Pattern**: 既存のOrchestrator実装でConfigurationManagerからOrchestratorTaskへの設定受け渡しパターンを確認する

### Decisions to Document

- **Validation Strategy**: OrchestratorSettingsとOrchestratorTaskの両方でバリデーションを実装するか、片方のみか
- **Default Value Source of Truth**: デフォルト値の単一情報源をどこに置くか（OrchestratorSettings vs OrchestratorTask）
- **Error Message Format**: バリデーションエラーメッセージの形式と詳細度

## Phase 1: Design Artifacts

**Status**: To be generated

### Data Model (`data-model.md`)

- OrchestratorSettings拡張設計（Pydanticモデル）
- バリデーション制約の定義
- 環境変数マッピング

### Quickstart Guide (`quickstart.md`)

- orchestrator.tomlでのラウンド設定例
- 環境変数での上書き例
- バリデーションエラーのトラブルシューティング

### Contracts

本機能はAPIエンドポイントを提供しないため、contracts/ディレクトリは作成しない。代わりに、Pydanticモデルのスキーマがコントラクトとして機能する。

## Implementation Checklist

### Phase 0: Research ✅
- [ ] research.mdを生成し、すべてのNEEDS CLARIFICATIONを解決
- [ ] Pydantic Settings検証パターンを調査
- [ ] 既存のOrchestratorSettings実装を分析
- [ ] Orchestrator設定受け渡しフローを確認

### Phase 1: Design ✅
- [ ] data-model.mdを生成（OrchestratorSettings拡張設計）
- [ ] quickstart.mdを生成（TOML設定例とトラブルシューティング）
- [ ] agent contextを更新（.claude/CLAUDE.md等）

### Gate: Constitution Re-check ✅
- [ ] Article 3: テストファースト実施を確認
- [ ] Article 4: spec.mdとの整合性を確認
- [ ] Article 14: MixSeek-Core仕様との整合性を確認

### Ready for Phase 2 (Task Generation) ✅
- [ ] すべてのPhase 0/1成果物が完成
- [ ] Constitution Checkが全てPASS
- [ ] 次は`/speckit.tasks`コマンドでtasks.mdを生成

## Notes

- 本機能は既存の051-configuration機能に依存しており、新しい設定読み込みメカニズムは不要
- RoundController実装（012-round-controller）は既にOrchestratorTaskのラウンド設定フィールドを使用しているため、ラウンド実行ロジックの変更は不要
- timeout_per_team_seconds（オーケストレータレベル）とsubmission_timeout_seconds/judgment_timeout_seconds（ラウンドレベル）は異なるレイヤーで独立に適用されるため、相互バリデーションは不要
