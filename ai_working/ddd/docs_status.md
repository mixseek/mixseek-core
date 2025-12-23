# DDD Phase 2: Documentation Status

## Issue #68: Orchestrator on_round_complete Callback Exposure

**Status**: ✅ Ready for Review

## Files Changed

### 1. docs/orchestrator-guide.md
**Type**: User Guide (使用ガイド)

**Changes**:
- 新セクション「ラウンド完了時のコールバック」を追加（lines 536-593）
- Orchestratorでの`on_round_complete`使用例を提供
- ユースケース（進捗追跡、外部連携、研究用途）を説明
- 注意事項（例外処理）を記載

**Retcon Writing**: ✅ 機能が既に存在するかのように記述

### 2. docs/api/orchestrator/index.md
**Type**: API Reference (APIリファレンス)

**Changes**:
- Orchestratorコンストラクタに`on_round_complete`パラメータを追加
- 使用例を更新
- `OnRoundCompleteCallback`のインポートを追加

**Retcon Writing**: ✅ 機能が既に存在するかのように記述

### 3. specs/007-orchestration/contracts/orchestrator-api.md
**Type**: API Contract (API契約)

**Changes**:
- Orchestratorコンストラクタに`on_round_complete`パラメータを追加
- 使用例にコールバック付きの例を追加

**Retcon Writing**: ✅ 機能が既に存在するかのように記述

### 4. specs/007-orchestration/contracts/round-controller-api.md
**Type**: API Contract (API契約)

**Changes**:
- コンストラクタを現在の実装に合わせて更新
  - `task: OrchestratorTask`パラメータ追加
  - `evaluator_settings`, `judgment_settings`, `prompt_builder_settings`追加
  - `on_round_complete`パラメータ追加
- `run_round()`の戻り値を`LeaderBoardEntry`に更新
- 使用例を現在のAPIに合わせて更新

**Retcon Writing**: ✅ 現在の実装を正確に反映

## Verification Checklist

- [x] **Consistency**: 全ドキュメント間でパラメータ名・型・説明が一致
- [x] **DRY**: orchestrator-guide.mdに詳細、他は簡潔な参照形式
- [x] **Philosophy Alignment**: シンプルなパススルー設計を反映
- [x] **Type Accuracy**: `OnRoundCompleteCallback | None`型を正確に使用
- [x] **Import Statements**: 必要なインポートを明示
- [x] **Spec-Implementation Sync**: 契約が現在の実装と一致

## Ready for Code Implementation

Phase 2完了後、Phase 4で以下のコード変更を実施：

1. `src/mixseek/orchestrator/orchestrator.py`
   - `on_round_complete`パラメータ追加
   - RoundControllerへのパススルー

2. `tests/unit/orchestrator/test_orchestrator.py`
   - コールバックパラメータのテスト追加

## Notes

- 既存の`OnRoundCompleteCallback`型を再利用（新規型定義なし）
- 後方互換性：デフォルト値`None`で既存コードに影響なし
- RoundController契約を現在の実装と同期（将来の不整合を防止）
