# Orchestrator API リファレンス

Orchestrator/RoundController APIの完全なリファレンスドキュメントです。

```{toctree}
:maxdepth: 2

data-models
```

## 概要

MixSeek-Core Orchestratorは、複数チームの並列実行を管理する2つの主要コンポーネントで構成されています：

- **Orchestrator**: 複数チームの並列実行と結果集約
- **RoundController**: 単一チームの1ラウンド実行管理

```{mermaid}
graph TD
    A[Orchestrator] --> B[RoundController 1]
    A --> C[RoundController 2]
    A --> D[RoundController N]
    B --> E[Leader Agent 1]
    C --> F[Leader Agent 2]
    D --> G[Leader Agent N]
    E --> H[Evaluator 1]
    F --> I[Evaluator 2]
    G --> J[Evaluator N]
    H --> K[DuckDB]
    I --> K
    J --> K
```

## Orchestrator API

### クラス: `Orchestrator`

複数チームのラウンドコントローラを管理し、並列実行を制御します。

#### Constructor

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
            OSError: MIXSEEK_WORKSPACE未設定時
        """
```

**使用例**:

```python
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.round_controller import RoundState

# 基本的な使用
settings = load_orchestrator_settings(
    Path("orchestrator.toml"),
    workspace=Path("/path/to/workspace")
)
orchestrator = Orchestrator(settings=settings)

# コールバック付きの使用
async def on_round_complete(round_state: RoundState, member_submissions: list) -> None:
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

orchestrator = Orchestrator(
    settings=settings,
    on_round_complete=on_round_complete,
)
```

#### メソッド: `execute()`

ユーザプロンプトを受け取り、複数チームを並列実行します。

```python
async def execute(
    self,
    user_prompt: str,
    timeout_seconds: int | None = None,
) -> ExecutionSummary:
    """ユーザプロンプトを複数チームで並列実行

    Args:
        user_prompt: ユーザプロンプト（空文字列不可）
        timeout_seconds: チーム単位タイムアウト（秒、Noneの場合は設定値使用）

    Returns:
        ExecutionSummary: 全チームの実行結果とランキング

    Raises:
        ValueError: user_promptが空の場合
        Exception: 全チーム失敗時
    """
```

**処理フロー**:

1. OrchestratorTaskを生成（UUID、タイムアウト等）
2. 全チームのRoundControllerを作成
3. `asyncio.gather()`で並列実行
4. 失敗チームを隔離（他チームは継続）
5. 完了チームから最高スコアチームを特定
6. ExecutionSummaryを生成して返却

**使用例**:

```python
summary = await orchestrator.execute(
    user_prompt="最新のAI技術トレンドを調査してください",
    timeout_seconds=600,
)

print(f"Total Teams: {summary.total_teams}")
print(f"Best Team: {summary.best_team_id}")
print(f"Best Score: {summary.best_score}")

# 最高スコアチームのSubmission
best_result = next(
    r for r in summary.team_results
    if r.team_id == summary.best_team_id
)
print(best_result.submission_content)
```

#### メソッド: `get_team_status()`

特定チームの実行状態を取得します。

```python
async def get_team_status(
    self,
    team_id: str,
) -> TeamStatus:
    """チームステータス取得

    Args:
        team_id: チーム識別子

    Returns:
        TeamStatus: チーム実行状態

    Raises:
        KeyError: 指定されたチームIDが存在しない場合
    """
```

**使用例**:

```python
status = await orchestrator.get_team_status("research-team-001")
print(f"Status: {status.status}")
print(f"Round: {status.current_round}")
```

#### メソッド: `get_all_team_statuses()`

全チームの実行状態を取得します。

```python
async def get_all_team_statuses(self) -> list[TeamStatus]:
    """全チームステータス取得

    Returns:
        list[TeamStatus]: 全チームの実行状態リスト
    """
```

**使用例**:

```python
statuses = await orchestrator.get_all_team_statuses()
for status in statuses:
    print(f"{status.team_name}: {status.status}")
```

### エラーハンドリング

Orchestratorは以下のエラーを発生させます：

| 例外 | 発生条件 | 対処方法 |
|------|---------|---------|
| `OSError` | `MIXSEEK_WORKSPACE`未設定 | 環境変数を設定 |
| `ValueError` | `user_prompt`が空 | 有効なプロンプトを指定 |
| `FileNotFoundError` | 設定ファイル不在 | ファイルパスを確認 |
| `Exception` | 全チーム失敗 | チーム設定を確認 |

**エラーハンドリング例**:

```python
try:
    summary = await orchestrator.execute(user_prompt="...")
except ValueError as e:
    print(f"Invalid prompt: {e}")
except FileNotFoundError as e:
    print(f"Config file not found: {e}")
except Exception as e:
    print(f"All teams failed: {e}")
```

## RoundController API

### クラス: `RoundController`

単一チームのマルチラウンド実行を管理します。

#### Constructor

```python
class RoundController:
    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        task: OrchestratorTask,
        evaluator_settings: EvaluatorSettings,
        save_db: bool = True,
    ) -> None:
        """RoundControllerインスタンス作成

        Args:
            team_config_path: チーム設定TOMLファイルパス
            workspace: ワークスペースパス
            task: Orchestratorタスク（execution_id、max_rounds、min_roundsを含む）
            evaluator_settings: Evaluator設定（Orchestratorから渡される）
            save_db: DuckDBへの保存フラグ（デフォルト: True）

        Raises:
            FileNotFoundError: team_config_pathが存在しない場合
            ValidationError: チーム設定が不正な場合
        """
```

**使用例**:

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController

# Evaluator設定を取得
workspace = Path("/path/to/workspace")
config_manager = ConfigurationManager(workspace=workspace)
evaluator_settings = config_manager.get_evaluator_settings()

# OrchestratorTask作成
task = OrchestratorTask(
    user_prompt="...",
    team_configs=[Path("team.toml")],
    timeout_seconds=600,
    max_rounds=3,
    min_rounds=1,
)

# RoundController初期化
controller = RoundController(
    team_config_path=Path("team.toml"),
    workspace=workspace,
    task=task,
    evaluator_settings=evaluator_settings,
    save_db=True,
)
```

#### メソッド: `run_round()`

マルチラウンドを実行し、最良のLeaderBoardEntryを返します。

```python
async def run_round(
    self,
    user_prompt: str,
    timeout_seconds: int,
) -> LeaderBoardEntry:
    """マルチラウンド実行

    処理フロー:
    1. max_roundsまでラウンドを繰り返す
    2. 各ラウンド:
       - Leader Agent実行
       - Evaluator実行（0-100スケール）
       - DuckDB記録（round_history, leader_board）
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

**使用例**:

```python
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

#### メソッド: `get_team_id()`

チーム識別子を取得します。

```python
def get_team_id(self) -> str:
    """チーム識別子を取得

    Returns:
        str: チームID
    """
```

#### メソッド: `get_team_name()`

チーム名を取得します。

```python
def get_team_name(self) -> str:
    """チーム名を取得

    Returns:
        str: チーム名
    """
```

**使用例**:

```python
controller = RoundController(...)
team_id = controller.get_team_id()
team_name = controller.get_team_name()
print(f"{team_name} ({team_id})")
```

### エラーハンドリング

RoundControllerは以下のエラーを発生させます：

| 例外 | 発生条件 | 対処方法 |
|------|---------|---------|
| `FileNotFoundError` | チーム設定ファイル不在 | ファイルパスを確認 |
| `ValidationError` | チーム設定が不正 | 設定内容を確認 |
| `TimeoutError` | タイムアウト発生 | タイムアウト値を延長 |
| `Exception` | Leader Agent/Evaluatorエラー | ログを確認 |

**エラーハンドリング例**:

```python
try:
    result = await controller.run_round(
        user_prompt="...",
        timeout_seconds=600,
        execution_id="550e8400-e29b-41d4-a716-446655440000",
    )
except asyncio.TimeoutError:
    print("Timeout occurred")
except FileNotFoundError as e:
    print(f"Config file not found: {e}")
except Exception as e:
    print(f"Execution failed: {e}")
```

## 設定ローダー

### 関数: `load_orchestrator_settings()`

オーケストレータ設定TOMLファイルを読み込み、`OrchestratorSettings`オブジェクトを返します。

```python
def load_orchestrator_settings(
    config: Path,
    workspace: Path | None = None
) -> OrchestratorSettings:
    """オーケストレータ設定TOML読み込み

    Args:
        config: 設定TOMLファイルパス
        workspace: ワークスペースパス（Noneの場合はMIXSEEK_WORKSPACE環境変数から取得）

    Returns:
        OrchestratorSettings: オーケストレータ設定

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        WorkspacePathNotSpecifiedError: workspaceもMIXSEEK_WORKSPACEも未指定の場合
    """
```

**使用例**:

```python
from pathlib import Path
from mixseek.orchestrator import load_orchestrator_settings

# ワークスペース明示指定
settings = load_orchestrator_settings(
    Path("orchestrator.toml"),
    workspace=Path("/path/to/workspace")
)

# 環境変数MIXSEEK_WORKSPACEから取得
settings = load_orchestrator_settings(Path("configs/orchestrator.toml"))
```

## パフォーマンス特性

### 並列実行のスケーラビリティ

- **並列度**: チーム数に応じて並列実行（`asyncio.gather()`使用）
- **リソース**: 各チームが独立したLeader Agent + Member Agentsを起動
- **ボトルネック**: LLM APIのレート制限、DuckDB書き込み

**推奨事項**:
- チーム数: 2-10が実用的
- タイムアウト: タスク複雑度に応じて調整（300-1200秒）
- リソース: 各チームが独立して実行されるため、メモリ使用量はチーム数に比例

### タイムアウト挙動

- **チーム単位タイムアウト**: 各チームに独立したタイムアウトが適用
- **タイムアウト発生時**: 該当チームは失敗として記録、他チームは継続
- **全チームタイムアウト**: 全チーム失敗として処理

### リソース使用量

| リソース | 使用量 | 備考 |
|---------|--------|------|
| メモリ | チーム数 × 200MB | Leader Agent + Member Agents |
| CPU | 低～中 | I/O待機が主体 |
| ネットワーク | 高 | LLM API通信 |
| ディスク | 低 | DuckDB書き込みのみ |

## スレッド安全性

### asyncioイベントループでの使用

Orchestrator/RoundControllerは完全に非同期設計されています：

```python
async def main():
    orchestrator = Orchestrator(...)

    # 複数タスクを並列実行可能
    task1 = orchestrator.execute("タスク1")
    task2 = orchestrator.execute("タスク2")

    results = await asyncio.gather(task1, task2)
```

### DuckDB接続の並列安全性

- **AggregationStore**: スレッドローカルコネクションで並列安全
- **リトライ機構**: 書き込み失敗時は最大3回リトライ

## ベストプラクティス

### 1. 適切なタイムアウト設定

```python
# シンプルなタスク
summary = await orchestrator.execute(
    user_prompt="...",
    timeout_seconds=300,  # 5分
)

# 複雑なタスク
summary = await orchestrator.execute(
    user_prompt="...",
    timeout_seconds=1200,  # 20分
)
```

### 2. エラーハンドリング

```python
try:
    summary = await orchestrator.execute(user_prompt="...")
except Exception as e:
    logger.error(f"Orchestration failed: {e}")
    # フォールバック処理
```

### 3. 結果の検証

```python
summary = await orchestrator.execute(user_prompt="...")

if summary.failed_teams > 0:
    logger.warning(f"{summary.failed_teams} teams failed")

if summary.best_score and summary.best_score < 0.5:
    logger.warning("Low quality submission")
```

### 4. リソース管理

```python
# 大量のタスクを順次実行
for task in tasks:
    summary = await orchestrator.execute(task)
    await asyncio.sleep(10)  # レート制限対策
```

## 次のステップ

- **[Data Models](data-models.md)** - データモデルの詳細
- **[Orchestrator Guide](../../orchestrator-guide.md)** - 使い方ガイド
- **[Database Schema](../../database-schema.md)** - DuckDBスキーマ

## 参照

- specs/007-orchestration/contracts/orchestrator-api.md
- specs/007-orchestration/contracts/round-controller-api.md
