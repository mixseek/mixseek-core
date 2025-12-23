# API Contract: RoundController

**Date**: 2025-11-05
**Spec**: [../spec.md](../spec.md)
**Data Model**: [../data-model.md](../data-model.md)

このドキュメントは、`RoundController`クラスの公開APIを定義します。

## Class: RoundController

単一チームの1ラウンド実行を管理するコンポーネント。Leader Agentの起動、Evaluatorの実行、DuckDBへの記録を担当します。

### Constructor

```python
from mixseek.round_controller import OnRoundCompleteCallback
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.config.schema import EvaluatorSettings, JudgmentSettings, PromptBuilderSettings

class RoundController:
    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        task: OrchestratorTask,
        evaluator_settings: EvaluatorSettings,
        judgment_settings: JudgmentSettings,
        prompt_builder_settings: PromptBuilderSettings,
        save_db: bool = True,
        on_round_complete: OnRoundCompleteCallback | None = None,
    ) -> None:
        """RoundControllerインスタンス作成

        Args:
            team_config_path: チーム設定TOMLファイルパス
            workspace: ワークスペースパス
            task: Orchestratorタスク（execution_id、max_rounds、min_roundsを含む）
            evaluator_settings: Evaluator設定（Orchestratorから渡される）
            judgment_settings: Judgment設定（Orchestratorから渡される）
            prompt_builder_settings: PromptBuilder設定（Orchestratorから渡される）
            save_db: DuckDBへの保存フラグ（デフォルト: True）
            on_round_complete: ラウンド完了時に呼び出されるコールバック（オプション）。
                (RoundState, list[MemberSubmission])を受け取り、例外が発生しても実行は継続されます。

        Raises:
            FileNotFoundError: team_config_pathが存在しない場合
            ValidationError: チーム設定が不正な場合
        """
```

### Methods

#### run_round()

```python
async def run_round(
    self,
    user_prompt: str,
    timeout_seconds: int,
) -> LeaderBoardEntry:
    """マルチラウンドを実行し、最良のLeaderBoardEntryを返す

    処理フロー:
    1. max_roundsまでラウンドを繰り返す
    2. 各ラウンド:
       - Leader Agent実行
       - Evaluator実行（0-100スケール）
       - DuckDB記録（round_history, leader_board）
       - on_round_completeコールバック呼び出し（設定されている場合）
       - 改善見込み判定（min_rounds以降）
    3. 最高スコアの提出を返す

    Args:
        user_prompt: ユーザプロンプト
        timeout_seconds: タイムアウト（秒）

    Returns:
        LeaderBoardEntry: 最良の提出エントリ（全ラウンド中の最高スコア）

    Raises:
        TimeoutError: タイムアウト発生時
        Exception: Leader AgentまたはEvaluatorでエラー発生時

    Note:
        execution_idはOrchestratorTaskに含まれています
    """
```

**処理フロー**:

1. **Leader Agent実行**:
   - チーム設定からLeader Agent作成
   - `leader_agent.run(user_prompt)`を実行
   - Submissionテキストとメッセージ履歴を取得

2. **DuckDB記録（round_history）**:
   - `AggregationStore.save_aggregation()`を呼び出し
   - Message HistoryとMember Agent応答記録を保存

3. **Evaluator実行**:
   - 既存のEvaluator実装（src/mixseek/evaluator/）を使用してSubmissionを評価
   - `EvaluationRequest`を作成し、`evaluator.evaluate()`を呼び出し
   - `EvaluationResult`から`overall_score`（0-100スケール）を取得し、0.0-1.0に正規化（DuckDB契約準拠）
   - 各メトリクスのコメントを統合してフィードバックを生成

4. **DuckDB記録（leader_board）**:
   - `AggregationStore.save_to_leader_board()`を呼び出し
   - Submission、評価スコア、フィードバックを保存

5. **RoundResult生成**:
   - 実行時間、リソース使用量を含む結果を返す

**エラーハンドリング**:

- Leader Agentエラー: 例外を再発生（Orchestratorで失格処理）
- Evaluatorエラー: 例外を再発生（Orchestratorで失格処理）
- DuckDBエラー: AggregationStoreのリトライに委譲（3回リトライ後に例外）
- タイムアウト: `asyncio.TimeoutError`を発生

#### get_team_id()

```python
def get_team_id(self) -> str:
    """チーム識別子を取得

    Returns:
        str: チームID
    """
```

#### get_team_name()

```python
def get_team_name(self) -> str:
    """チーム名を取得

    Returns:
        str: チーム名
    """
```

### Example Usage

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController, RoundState
from mixseek.agents.leader.models import MemberSubmission

# Evaluator設定を取得
workspace = Path("/path/to/workspace")
config_manager = ConfigurationManager(workspace=workspace)
evaluator_settings = config_manager.get_evaluator_settings()
judgment_settings = config_manager.get_judgment_settings()
prompt_builder_settings = config_manager.get_prompt_builder_settings()

# OrchestratorTask作成
task = OrchestratorTask(
    user_prompt="...",
    team_configs=[Path("team.toml")],
    timeout_seconds=600,
    max_rounds=3,
    min_rounds=1,
)

# コールバック定義（オプション）
async def on_round_complete(
    round_state: RoundState,
    member_submissions: list[MemberSubmission],
) -> None:
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

# RoundController初期化
controller = RoundController(
    team_config_path=Path("team.toml"),
    workspace=workspace,
    task=task,
    evaluator_settings=evaluator_settings,
    judgment_settings=judgment_settings,
    prompt_builder_settings=prompt_builder_settings,
    save_db=True,
    on_round_complete=on_round_complete,
)

# マルチラウンド実行
result = await controller.run_round(
    user_prompt="最新のAI技術トレンドを調査してください",
    timeout_seconds=600,
)

print(f"Execution ID: {result.execution_id}")
print(f"Team: {result.team_name}")
print(f"Best Round: {result.round_number}")
print(f"Score: {result.score}")  # 0-100スケール
print(f"Submission: {result.submission_content}")
print(f"Exit Reason: {result.exit_reason}")
```

### Timeout Implementation

```python
import asyncio

async def run_round_with_timeout(
    self,
    user_prompt: str,
    timeout_seconds: int,
) -> RoundResult:
    """タイムアウト付きラウンド実行"""
    try:
        return await asyncio.wait_for(
            self.run_round(user_prompt, timeout_seconds),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        # タイムアウト処理（Orchestratorで失格）
        raise
```

### Error Handling

| Error Type | Condition | Handling |
|------------|-----------|----------|
| `FileNotFoundError` | チーム設定ファイル不在 | 初期化時に発生 |
| `ValidationError` | チーム設定が不正 | 初期化時に発生（Pydantic） |
| `TimeoutError` | タイムアウト発生 | run_round()実行時に発生 |
| `Exception` | Leader Agent/Evaluatorエラー | run_round()実行時に発生、Orchestratorで失格処理 |

### Performance Characteristics

- **Leader Agent実行時間**: タスクとチーム構成に依存（通常10-60秒）
- **Evaluator実行時間**: LLM-as-a-Judgeの場合は5-15秒
- **DuckDB記録時間**: 通常1秒未満（リトライ含めて最大10秒）
- **合計実行時間**: 通常20-100秒（タイムアウトデフォルト: 600秒）

### Contract Compliance

- **FR-003**: ラウンド開始・終了通知をOrchestratorへ返す ✅
- **FR-004**: ラウンド終了条件判定（初期実装では1ラウンドで自動終了） ✅
- **FR-008**: DuckDB通信障害時の再送処理（AggregationStoreに委譲） ✅

### Thread Safety

- `RoundController`インスタンスは非スレッドセーフ
- 複数チームの並列実行時は、各チームが独立したRoundControllerインスタンスを使用
- `AggregationStore`はスレッドローカルコネクションで並列安全

### Testing Considerations

- **ユニットテスト**:
  - モックされたLeader AgentとEvaluatorで基本フローをテスト
  - タイムアウト処理をテスト
  - エラーハンドリングをテスト

- **統合テスト**:
  - 実際のLeader AgentとDuckDBを使用してE2Eテスト
  - 並列実行時の競合テスト

### Future Extensions

初期実装は1ラウンドのみですが、将来的に複数ラウンド対応時は以下を追加:

- `should_continue_round()`: ラウンド継続判定
- `load_previous_round()`: 前ラウンド結果読み込み
- `update_round_state()`: ラウンド状態更新
