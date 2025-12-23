# API Contract: Orchestrator

**Date**: 2025-11-05
**Spec**: [../spec.md](../spec.md)
**Data Model**: [../data-model.md](../data-model.md)

このドキュメントは、`Orchestrator`クラスの公開APIを定義します。

## Class: Orchestrator

複数チームのラウンドコントローラを管理し、並列実行を制御するコンポーネント。

### Constructor

```python
from mixseek.round_controller import OnRoundCompleteCallback

class Orchestrator:
    def __init__(
        self,
        settings: OrchestratorSettings,
        save_db: bool = True,
        on_round_complete: OnRoundCompleteCallback | None = None,
    ) -> None:
        """Orchestratorインスタンス作成

        Args:
            settings: オーケストレータ設定
            save_db: DuckDBへの保存フラグ
            on_round_complete: ラウンド完了時に呼び出されるコールバック（オプション）。
                全チームの全RoundControllerに渡され、各ラウンド完了時に呼び出されます。

        Raises:
            EnvironmentError: MIXSEEK_WORKSPACE未設定時
            FileNotFoundError: チーム設定ファイルが見つからない場合
        """
```

### Methods

#### execute()

```python
async def execute(
    self,
    user_prompt: str,
    timeout_seconds: int | None = None,
) -> ExecutionSummary:
    """ユーザプロンプトを受け取り、複数チームを並列実行

    Args:
        user_prompt: ユーザプロンプト
        timeout_seconds: チーム単位タイムアウト（秒）。Noneの場合はconfigのデフォルト値を使用

    Returns:
        ExecutionSummary: 全チームの実行結果を集約したサマリー

    Raises:
        ValueError: user_promptが空文字列の場合
        TimeoutError: 全チームがタイムアウトした場合（少なくとも1チームが完了すれば発生しない）
    """
```

**処理フロー**:

1. `OrchestratorTask`を生成
2. 各チームの`RoundController`を作成
3. `asyncio.gather()`で並列実行（`return_exceptions=True`）
4. 完了したチームの`RoundResult`を収集
5. 最高スコアチームを特定
6. `ExecutionSummary`を生成して返す

**エラーハンドリング**:

- 個別チームのエラーは`RoundResult`に記録せず、失格として扱う
- 全チームが失敗した場合でも、`ExecutionSummary`を返す（`best_team_id=None`）

#### get_team_status()

```python
async def get_team_status(
    self,
    team_id: str,
) -> TeamStatus:
    """特定チームのステータス取得（監視インターフェース用）

    Args:
        team_id: チーム識別子

    Returns:
        TeamStatus: チームの現在ステータス

    Raises:
        KeyError: 存在しないteam_idの場合
    """
```

#### get_all_team_statuses()

```python
async def get_all_team_statuses(self) -> list[TeamStatus]:
    """全チームのステータス取得（監視インターフェース用）

    Returns:
        list[TeamStatus]: 全チームのステータスリスト
    """
```

### Example Usage

```python
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.round_controller import RoundState

# 設定読み込み
settings = load_orchestrator_settings(Path("orchestrator.toml"))

# 基本的な使用
orchestrator = Orchestrator(settings=settings)

# コールバック付きの使用
async def on_round_complete(round_state: RoundState, member_submissions: list) -> None:
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

orchestrator = Orchestrator(
    settings=settings,
    on_round_complete=on_round_complete,
)

# 実行
summary = await orchestrator.execute(
    user_prompt="最新のAI技術トレンドを調査してください",
)

# 結果表示
print(f"完了チーム: {summary.completed_teams}/{summary.total_teams}")
print(f"最高スコア: {summary.best_score} (チーム: {summary.best_team_id})")
```

### Error Handling

| Error Type | Condition | Handling |
|------------|-----------|----------|
| `EnvironmentError` | MIXSEEK_WORKSPACE未設定 | 初期化時に発生、明示的なエラーメッセージを表示 |
| `FileNotFoundError` | チーム設定ファイル不在 | 初期化時に発生、ファイルパスを表示 |
| `ValueError` | user_prompt空文字列 | execute()呼び出し時に発生 |
| `TimeoutError` | 全チーム完了前にタイムアウト | 完了チームがある場合は発生しない |

### Performance Characteristics

- **並列実行**: `asyncio.gather()`により、N個のチームが並列実行される
- **タイムアウト**: チーム単位でタイムアウトが適用される（デフォルト: 600秒）
- **リソース使用量**: 各チームは独立したDuckDBコネクションを使用（スレッドローカル）

### Contract Compliance

- **FR-001**: ユーザプロンプトをタスク定義に正規化 ✅
- **FR-002**: 複数チーム並列実行をサポート ✅
- **FR-005**: 全チーム完了後にサマリーを生成 ✅
- **FR-006**: チームタイムアウト時は即座に失格 ✅
- **FR-007**: チーム単位の状態監視インターフェース提供 ✅

### Thread Safety

- `Orchestrator`インスタンスは非スレッドセーフ（単一asyncioイベントループで使用）
- 内部で使用する`AggregationStore`はスレッドローカルコネクションで並列安全

### Testing Considerations

- **ユニットテスト**: モックされた`RoundController`で並列実行フローをテスト
- **統合テスト**: 実際のLeader AgentとDuckDBを使用してE2Eテスト
- **タイムアウトテスト**: 意図的にタイムアウトを発生させて失格処理を検証
