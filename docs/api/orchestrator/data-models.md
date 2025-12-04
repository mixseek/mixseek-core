# Orchestrator データモデル

Orchestrator/RoundControllerで使用されるデータモデルの詳細リファレンスです。

## 概要

Orchestratorは以下のPydanticモデルを使用してデータを管理します：

- **OrchestratorTask**: タスク定義（UUID、プロンプト、チーム設定）
- **TeamStatus**: チーム実行状態（status、round、タイムスタンプ）
- **RoundResult**: 1ラウンドの実行結果（submission、評価、usage）
- **ExecutionSummary**: 全チーム集約結果（ランキング、統計）
- **OrchestratorSettings**: オーケストレータ設定（workspace、timeout、teams）
- **FailedTeamInfo**: 失敗チーム情報（error_message）

## データフロー

```{mermaid}
graph TD
    A[User Input] --> B[OrchestratorTask]
    B --> C[Orchestrator.execute]
    C --> D[TeamStatus: pending]
    D --> E[TeamStatus: running]
    E --> F[RoundController.run_round]
    F --> G[RoundResult]
    G --> H[TeamStatus: completed]
    H --> I[ExecutionSummary]
    I --> J[Best Team Selection]
```

## OrchestratorTask

ユーザプロンプトから生成されるタスク定義です。

### フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| execution_id | str | ❌ | UUID生成 | オーケストレーション実行識別子 |
| user_prompt | str | ✅ | - | ユーザプロンプト |
| team_configs | list[Path] | ✅ | - | チーム設定TOMLパスリスト |
| created_at | datetime | ❌ | 現在時刻(UTC) | 作成日時 |
| timeout_seconds | int | ✅ | - | チーム単位タイムアウト（秒） |

### バリデーション

- `user_prompt`: 空文字列不可
- `team_configs`: 1つ以上のチーム設定が必要
- `timeout_seconds`: 正の整数

### 使用例

```python
from pathlib import Path
from mixseek.orchestrator.models import OrchestratorTask

task = OrchestratorTask(
    user_prompt="最新のAI技術トレンドを調査してください",
    team_configs=[
        Path("configs/research-team.toml"),
        Path("configs/analysis-team.toml"),
    ],
    timeout_seconds=600,
)

print(f"Execution ID: {task.execution_id}")
print(f"Created at: {task.created_at}")
```

## TeamStatus

特定チームの実行状態を表します。

### フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| team_id | str | ✅ | - | チーム識別子 |
| team_name | str | ✅ | - | チーム名 |
| status | Literal | ❌ | "pending" | 実行ステータス |
| current_round | int | ❌ | 0 | 現在のラウンド番号 |
| started_at | datetime \| None | ❌ | None | 実行開始日時 |
| completed_at | datetime \| None | ❌ | None | 実行完了日時 |
| error_message | str \| None | ❌ | None | エラーメッセージ |

### ステータス値

- `pending`: 実行待機中
- `running`: 実行中
- `completed`: 正常完了
- `failed`: 失敗
- `timeout`: タイムアウト

### ステータス遷移

```{mermaid}
stateDiagram-v2
    [*] --> pending
    pending --> running : execute()
    running --> completed : success
    running --> failed : error
    running --> timeout : timeout
    completed --> [*]
    failed --> [*]
    timeout --> [*]
```

### 使用例

```python
from mixseek.orchestrator.models import TeamStatus

status = TeamStatus(
    team_id="research-team-001",
    team_name="Research Team",
)

print(f"Status: {status.status}")  # "pending"

# ステータス更新
status.status = "running"
status.started_at = datetime.now(UTC)
```

## RoundResult

1ラウンドの実行結果を表します。

### フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| execution_id | str | ✅ | - | オーケストレーション実行識別子（UUID） |
| team_id | str | ✅ | - | チーム識別子 |
| team_name | str | ✅ | - | チーム名 |
| round_number | int | ✅ | - | ラウンド番号（≥1） |
| submission_content | str | ✅ | - | Submissionテキスト |
| evaluation_score | float | ✅ | - | 評価スコア（0.0-1.0） |
| evaluation_feedback | str | ✅ | - | 評価フィードバック |
| usage | RunUsage | ✅ | - | リソース使用量 |
| execution_time_seconds | float | ✅ | - | 実行時間（秒、>0） |
| completed_at | datetime | ❌ | 現在時刻(UTC) | 完了日時 |

### バリデーション

- `round_number`: 1以上
- `evaluation_score`: 0.0-1.0の範囲
- `execution_time_seconds`: 正の実数

### 使用例

```python
from mixseek.orchestrator.models import RoundResult
from pydantic_ai import RunUsage

result = RoundResult(
    execution_id="550e8400-e29b-41d4-a716-446655440000",
    team_id="research-team-001",
    team_name="Research Team",
    round_number=1,
    submission_content="最新のAI技術トレンドについて...",
    evaluation_score=0.92,  # 0.0-1.0スケール
    evaluation_feedback="包括的な調査結果が提供されました。",
    usage=RunUsage(input_tokens=1500, output_tokens=3000, requests=5),
    execution_time_seconds=45.2,
)

print(f"Execution ID: {result.execution_id}")
print(f"Score: {result.evaluation_score * 100:.2f}")  # 92.00（表示用）
print(f"Tokens: {result.usage.input_tokens + result.usage.output_tokens}")
```

## ExecutionSummary

全チームの完了後に生成される最終集約情報です。

### フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| execution_id | str | ✅ | - | オーケストレーション実行識別子（UUID） |
| user_prompt | str | ✅ | - | ユーザプロンプト |
| team_results | list[RoundResult] | ❌ | [] | チーム結果リスト |
| best_team_id | str \| None | ❌ | None | 最高スコアチームID |
| best_score | float \| None | ❌ | None | 最高評価スコア（0.0-1.0） |
| total_execution_time_seconds | float | ✅ | - | 総実行時間（秒、>0） |
| failed_teams_info | list[FailedTeamInfo] | ❌ | [] | 失敗チームの詳細情報 |
| created_at | datetime | ❌ | 現在時刻(UTC) | サマリー作成日時 |

### Computed Fields

以下のフィールドは自動計算されます：

| フィールド | 型 | 計算式 | 説明 |
|-----------|-----|--------|------|
| total_teams | int | len(team_results) + len(failed_teams_info) | 総チーム数（成功+失敗） |
| completed_teams | int | len(team_results) | 完了チーム数（成功のみ） |
| failed_teams | int | len(failed_teams_info) | 失敗チーム数 |

### 使用例

```python
from mixseek.orchestrator.models import ExecutionSummary, RoundResult

summary = ExecutionSummary(
    execution_id="550e8400-e29b-41d4-a716-446655440000",
    user_prompt="最新のAI技術トレンドを調査してください",
    team_results=[result1, result2],
    best_team_id="research-team-001",
    best_score=0.92,
    total_execution_time_seconds=45.2,
)

# Computed fields
print(f"Total Teams: {summary.total_teams}")        # 2
print(f"Completed: {summary.completed_teams}")       # 2
print(f"Failed: {summary.failed_teams}")             # 0

# 最高スコアチームの取得
best_result = next(
    r for r in summary.team_results
    if r.team_id == summary.best_team_id
)
```

## OrchestratorSettings

オーケストレータ設定を表します。Feature 051の`OrchestratorSettings`（`BaseSettings`ベース）を使用します。

### 主要フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| workspace_path | Path | ✅ | ワークスペースパス |
| timeout_per_team_seconds | int | - | チーム単位タイムアウト（秒、デフォルト: 600） |
| max_retries_per_team | int | - | チームあたり最大リトライ数（デフォルト: 0） |
| teams | list[dict] | ✅ | チーム参照リスト（例: `[{"config": "team1.toml"}]`） |

### バリデーション

- `timeout_per_team_seconds`: 正の整数
- `teams`: 1つ以上のチーム参照が必要

### TOML形式

```toml
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/research-team.toml"

[[orchestrator.teams]]
config = "configs/analysis-team.toml"
```

### 使用例

```python
from pathlib import Path
from mixseek.orchestrator import load_orchestrator_settings

# TOMLファイルから読み込み
settings = load_orchestrator_settings(
    Path("orchestrator.toml"),
    workspace=Path("/path/to/workspace")
)

print(f"Timeout: {settings.timeout_per_team_seconds}s")
print(f"Teams: {len(settings.teams)}")
```

**Note**: `OrchestratorSettings`は`ConfigurationManager`経由で読み込まれ、トレーサビリティとバリデーションが自動適用されます。詳細は`specs/051-configuration/spec.md`を参照してください。

## FailedTeamInfo

失敗チームの情報を表します。

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| team_id | str | ✅ | チーム識別子 |
| team_name | str | ✅ | チーム名 |
| error_message | str | ✅ | エラーメッセージ |

### 使用例

```python
from mixseek.orchestrator.models import FailedTeamInfo

failed = FailedTeamInfo(
    team_id="analysis-team-002",
    team_name="Advanced Analysis Team",
    error_message="Timeout after 600 seconds",
)

print(f"{failed.team_name}: {failed.error_message}")
```

## データフロー図

全体のデータフローを以下に示します：

```{mermaid}
graph TD
    A[User: mixseek exec] --> B[OrchestratorTask]
    B --> C[Orchestrator]
    C --> D[TeamStatus 1: pending]
    C --> E[TeamStatus 2: pending]
    D --> F[TeamStatus 1: running]
    E --> G[TeamStatus 2: running]
    F --> H[RoundController 1]
    G --> I[RoundController 2]
    H --> J[RoundResult 1]
    I --> K[RoundResult 2]
    J --> L[TeamStatus 1: completed]
    K --> M[TeamStatus 2: completed]
    L --> N[ExecutionSummary]
    M --> N
    N --> O[Best Team Selection]
    O --> P[User Output]
```

## JSON表現

全モデルはPydanticモデルであり、JSON形式でシリアライズ可能です：

```python
# ExecutionSummaryのJSON出力
summary_json = summary.model_dump_json(indent=2)

# JSON読み込み
import json
summary_dict = json.loads(summary_json)
summary = ExecutionSummary.model_validate(summary_dict)
```

**JSON出力例**:

```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_prompt": "最新のAI技術トレンドを調査してください",
  "team_results": [
    {
      "execution_id": "550e8400-e29b-41d4-a716-446655440000",
      "team_id": "research-team-001",
      "team_name": "Research Team",
      "round_number": 1,
      "submission_content": "...",
      "evaluation_score": 0.92,
      "evaluation_feedback": "包括的な調査結果が提供されました。",
      "usage": {
        "input_tokens": 1500,
        "output_tokens": 3000,
        "requests": 5
      },
      "execution_time_seconds": 45.2,
      "completed_at": "2025-11-05T10:30:00Z"
    }
  ],
  "best_team_id": "research-team-001",
  "best_score": 0.92,
  "total_execution_time_seconds": 45.2,
  "failed_teams_info": [],
  "created_at": "2025-11-05T10:30:00Z"
}
```

## バリデーションルール

### Pydanticバリデーション

全モデルはPydanticのバリデーション機能を使用します：

```python
from pydantic import ValidationError

try:
    task = OrchestratorTask(
        user_prompt="",  # エラー: 空文字列
        team_configs=[],  # エラー: 空リスト
        timeout_seconds=-1,  # エラー: 負の値
    )
except ValidationError as e:
    print(e)
```

### カスタムバリデーター

特定のフィールドにはカスタムバリデーターが適用されます：

- **OrchestratorTask.user_prompt**: 空文字列チェック
- **OrchestratorTask.team_configs**: 非空リストチェック

## 次のステップ

- **[Orchestrator API](index.md)** - API詳細
- **[Orchestrator Guide](../../orchestrator-guide.md)** - 使い方ガイド

## 参照

- specs/007-orchestration/data-model.md
- `src/mixseek/orchestrator/models.py`
