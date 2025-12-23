# DDD Plan: Orchestrator on_round_complete Callback Exposure

## Problem Statement

`RoundController`は`on_round_complete`コールバックパラメータを受け付け、各ラウンド完了後に正しく呼び出す。しかし、`Orchestrator`はこのパラメータを公開していないため、公開APIからこの機能を使用することができない。

**ユーザー価値:**
- 外部統合がラウンド完了イベントにフックできる
- リアルタイム進捗追跡が可能
- カスタム後処理パイプラインの実装が可能

**Issue:** #68

## Proposed Solution

`Orchestrator.__init__()`に`on_round_complete`パラメータを追加し、`RoundController`作成時にパススルーする。

```python
class Orchestrator:
    def __init__(
        self,
        settings: OrchestratorSettings,
        save_db: bool = True,
        on_round_complete: OnRoundCompleteCallback | None = None,
    ) -> None:
        self._on_round_complete = on_round_complete
        ...
```

## Alternatives Considered

### Alternative A: OrchestratorSettingsに含める (却下)

`OrchestratorSettings`Pydanticモデルに`on_round_complete`フィールドを追加。

**却下理由:**
- コールバック関数はTOMLでシリアライズ不可
- Pydanticモデルにランタイムコールバックを含めるのは不適切
- 不必要な複雑さ

### Alternative B: executeメソッドの引数として渡す (却下)

`Orchestrator.execute()`メソッドにパラメータを追加。

**却下理由:**
- `execute()`のシグネチャが複雑化
- RoundControllerは`__init__`時にコールバックを設定するため、実行時に変更するのは不自然

## Architecture & Design

### Key Interfaces

既存の`OnRoundCompleteCallback`型を再利用:

```python
# mixseek/round_controller/models.py (既存)
OnRoundCompleteCallback = Callable[
    ["RoundState", list["MemberSubmission"]],
    Awaitable[None],
]
```

### Module Boundaries

```
Orchestrator (public API)
    └── on_round_complete parameter ── pass-through ──> RoundController
                                                            └── invoke callback after each round
```

### Data Models

変更なし。既存の`OnRoundCompleteCallback`型を使用。

## Files to Change

### Non-Code Files (Phase 2)

- [ ] `docs/orchestrator-guide.md` - Orchestratorでのコールバック使用例を追加

### Code Files (Phase 4)

- [ ] `src/mixseek/orchestrator/orchestrator.py` - `on_round_complete`パラメータ追加
- [ ] `tests/unit/orchestrator/test_orchestrator.py` - 新パラメータのテスト追加

## Philosophy Alignment

### Ruthless Simplicity

- **Start minimal**: 1パラメータ追加のみ
- **Avoid future-proofing**: `evaluator`や`query_generator`の追加は別Issue
- **Clear over clever**: シンプルなパススルー、変換なし

### Modular Design

- **Bricks (modules)**: Orchestrator, RoundController
- **Studs (interfaces)**: OnRoundCompleteCallback型
- **Regeneratable**: この仕様から再実装可能

## Test Strategy

### Unit Tests

1. `test_orchestrator_with_on_round_complete` - パラメータが正しく渡されることを確認
2. `test_orchestrator_on_round_complete_none_default` - デフォルト値(None)で正常動作を確認

### Integration Tests

既存の`test_round_controller_hooks.py`テストで`RoundController`側のコールバック動作は検証済み。
Orchestratorからのパススルーのみを追加テスト。

### User Testing

```python
from mixseek.orchestrator import Orchestrator
from mixseek.round_controller import OnRoundCompleteCallback, RoundState

async def my_callback(round_state: RoundState, submissions: list) -> None:
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

orchestrator = Orchestrator(
    settings=settings,
    on_round_complete=my_callback,
)
await orchestrator.execute("Test prompt")
```

## Implementation Approach

### Phase 2 (Docs)

1. `docs/orchestrator-guide.md`に以下を追加:
   - Orchestratorでの`on_round_complete`使用例
   - ユースケース説明

### Phase 4 (Code)

1. `src/mixseek/orchestrator/orchestrator.py`:
   - Import `OnRoundCompleteCallback` from `round_controller.models`
   - Add parameter to `__init__`
   - Store as `self._on_round_complete`
   - Pass to `RoundController` in `_execute_impl`

2. `tests/unit/orchestrator/test_orchestrator.py`:
   - Add test for callback parameter
   - Add test for None default

## Success Criteria

- [ ] `make check` passes (lint, format, type check)
- [ ] `make test` passes (all tests)
- [ ] Orchestratorがon_round_completeパラメータを受け付ける
- [ ] RoundControllerにコールバックが正しく渡される
- [ ] 既存のテストが引き続きパスする（後方互換性）

## Risk Assessment

**Low Risk Change:**
- オプショナルパラメータ追加のみ
- デフォルト値Noneで完全な後方互換性
- 既存のRoundControllerロジックに変更なし

## Next Steps

✅ Plan complete and approved
➡️ Ready for `/ddd:2-docs`
