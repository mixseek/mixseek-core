# Data Model: MixSeek-Core Orchestrator

**Date**: 2025-11-05
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md)

このドキュメントは、オーケストレータとラウンドコントローラのデータモデルを定義します。

## 1. OrchestratorTask

ユーザプロンプトから生成されるタスク定義。オーケストレータが管理する実行単位です。

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | `str` | Yes | タスクの一意識別子（UUID） |
| `user_prompt` | `str` | Yes | ユーザから受け取ったプロンプト |
| `team_configs` | `list[Path]` | Yes | チーム設定TOMLファイルパスのリスト |
| `created_at` | `datetime` | Yes (auto) | タスク作成日時（UTC） |
| `timeout_seconds` | `int` | Yes | チーム単位タイムアウト（秒） |

### Pydantic Model

```python
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

class OrchestratorTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()), description="タスク一意識別子")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_configs: list[Path] = Field(description="チーム設定TOMLパスリスト")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="作成日時")
    timeout_seconds: int = Field(gt=0, description="チーム単位タイムアウト（秒）")
```

### Usage Example

```python
task = OrchestratorTask(
    user_prompt="最新のAI技術トレンドを調査してください",
    team_configs=[
        Path("workspace/configs/team1.toml"),
        Path("workspace/configs/team2.toml"),
    ],
    timeout_seconds=600,
)
```

## 2. TeamStatus

特定チームの実行状態。オーケストレータが各チームの進行状況を追跡するために使用します。

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `team_id` | `str` | Yes | チーム識別子（TeamConfigから取得） |
| `team_name` | `str` | Yes | チーム名（TeamConfigから取得） |
| `status` | `Literal["pending", "running", "completed", "failed", "timeout"]` | Yes | 実行ステータス |
| `current_round` | `int` | Yes | 現在のラウンド番号（初期値: 0） |
| `started_at` | `datetime \| None` | No | 実行開始日時 |
| `completed_at` | `datetime \| None` | No | 実行完了日時 |
| `error_message` | `str \| None` | No | エラーメッセージ（失敗時） |

### Pydantic Model

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

class TeamStatus(BaseModel):
    team_id: str = Field(description="チーム識別子")
    team_name: str = Field(description="チーム名")
    status: Literal["pending", "running", "completed", "failed", "timeout"] = Field(
        default="pending",
        description="実行ステータス",
    )
    current_round: int = Field(default=0, ge=0, description="現在のラウンド番号")
    started_at: datetime | None = Field(default=None, description="実行開始日時")
    completed_at: datetime | None = Field(default=None, description="実行完了日時")
    error_message: str | None = Field(default=None, description="エラーメッセージ")
```

### Status Transitions

```
pending -> running -> completed
               |
               +----> failed
               |
               +----> timeout
```

## 3. RoundResult

1ラウンドの実行結果。RoundControllerが返す結果です。

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `team_id` | `str` | Yes | チーム識別子 |
| `team_name` | `str` | Yes | チーム名 |
| `round_number` | `int` | Yes | ラウンド番号 |
| `submission_content` | `str` | Yes | Leader Agentが生成したSubmissionテキスト |
| `evaluation_score` | `float` | Yes | 評価スコア（0.0-1.0） |
| `evaluation_feedback` | `str` | Yes | 評価フィードバック |
| `usage` | `RunUsage` | Yes | リソース使用量（Pydantic AI RunUsage） |
| `execution_time_seconds` | `float` | Yes | 実行時間（秒） |
| `completed_at` | `datetime` | Yes (auto) | 完了日時 |

### Pydantic Model

```python
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from pydantic_ai import RunUsage

class RoundResult(BaseModel):
    team_id: str = Field(description="チーム識別子")
    team_name: str = Field(description="チーム名")
    round_number: int = Field(ge=1, description="ラウンド番号")
    submission_content: str = Field(description="Submissionテキスト")
    evaluation_score: float = Field(ge=0.0, le=1.0, description="評価スコア")
    evaluation_feedback: str = Field(description="評価フィードバック")
    usage: RunUsage = Field(description="リソース使用量")
    execution_time_seconds: float = Field(gt=0, description="実行時間（秒）")
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="完了日時",
    )
```

## 4. ExecutionSummary

全チームの完了後に生成される最終集約情報。

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | `str` | Yes | タスク識別子（OrchestratorTaskから） |
| `user_prompt` | `str` | Yes | ユーザプロンプト |
| `team_results` | `list[RoundResult]` | Yes | 各チームのラウンド結果 |
| `best_team_id` | `str \| None` | No | 最高スコアチームID（完了チームがない場合None） |
| `best_score` | `float \| None` | No | 最高評価スコア |
| `total_teams` | `int` | Yes (computed) | 総チーム数 |
| `completed_teams` | `int` | Yes (computed) | 完了チーム数 |
| `failed_teams` | `int` | Yes (computed) | 失敗チーム数 |
| `total_execution_time_seconds` | `float` | Yes | 総実行時間（秒） |
| `created_at` | `datetime` | Yes (auto) | サマリー作成日時 |

### Pydantic Model

```python
from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field

class ExecutionSummary(BaseModel):
    task_id: str = Field(description="タスク識別子")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_results: list[RoundResult] = Field(default_factory=list, description="チーム結果リスト")
    best_team_id: str | None = Field(default=None, description="最高スコアチームID")
    best_score: float | None = Field(default=None, ge=0.0, le=1.0, description="最高評価スコア")
    total_execution_time_seconds: float = Field(gt=0, description="総実行時間（秒）")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="サマリー作成日時",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_teams(self) -> int:
        """総チーム数"""
        return len(self.team_results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completed_teams(self) -> int:
        """完了チーム数（評価スコアが存在）"""
        return sum(1 for r in self.team_results if r.evaluation_score is not None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_teams(self) -> int:
        """失敗チーム数"""
        return self.total_teams - self.completed_teams
```

### Usage Example

```python
summary = ExecutionSummary(
    task_id="12345",
    user_prompt="最新のAI技術トレンドを調査してください",
    team_results=[result1, result2],
    best_team_id="team-001",
    best_score=0.92,
    total_execution_time_seconds=45.3,
)

print(f"完了チーム: {summary.completed_teams}/{summary.total_teams}")
print(f"最高スコア: {summary.best_score} (チーム: {summary.best_team_id})")
```

## 5. OrchestratorSettings

オーケストレータ設定（TOMLファイルから読み込み）。Feature 051の`OrchestratorSettings`を使用します。詳細は`specs/013-configuration/spec.md`を参照してください。

### 主要フィールド

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_path` | `Path` | Yes | ワークスペースパス |
| `timeout_per_team_seconds` | `int` | No | チーム単位タイムアウト（秒）、デフォルト: 600 |
| `max_retries_per_team` | `int` | No | チームあたり最大リトライ数、デフォルト: 0 |
| `teams` | `list[dict]` | Yes | チーム参照リスト（例: `[{"config": "team1.toml"}]`） |

### TOML Format

```toml
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/team1.toml"

[[orchestrator.teams]]
config = "configs/team2.toml"
```

**Note**: `OrchestratorSettings`は`ConfigurationManager`経由で読み込まれ、トレーサビリティとバリデーションが自動的に適用されます。

## Data Flow

```
1. User Input
   |
   v
2. OrchestratorTask (作成)
   |
   v
3. Orchestrator.execute(task)
   |
   +-- TeamStatus (各チーム初期化)
   |
   +-- RoundController.run_round() (並列実行)
       |
       +-- Leader Agent 実行
       |
       +-- Evaluator 実行
       |
       +-- DuckDB 記録
       |
       v
   RoundResult (各チーム結果)
   |
   v
4. ExecutionSummary (最終集約)
   |
   v
5. ユーザへ結果表示
```

## Validation Rules

### OrchestratorTask
- `user_prompt`: 空文字列不可
- `team_configs`: 最低1つ以上のチーム設定が必要
- `timeout_seconds`: 正の整数

### TeamStatus
- `status`: 定義されたステータス値のみ許可
- `current_round`: 0以上の整数

### RoundResult
- `evaluation_score`: 0.0〜1.0の範囲
- `execution_time_seconds`: 正の数値

### ExecutionSummary
- `best_score`: 存在する場合は0.0〜1.0の範囲
- `total_execution_time_seconds`: 正の数値

## Database Persistence

以下のデータはDuckDBに永続化されます:

- **round_history**: `RoundResult`の詳細（Message History + Member Agent応答記録）
- **leader_board**: `RoundResult`の評価結果（Submission + スコア + フィードバック）

詳細は既存スキーマを参照: `specs/008-leader/contracts/database-schema.sql`
