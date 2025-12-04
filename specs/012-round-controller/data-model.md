# Data Model: Round Controller - ラウンドライフサイクル管理

**日付**: 2025-11-10
**ステータス**: 完了

## Phase 1: Design & Contracts

本ドキュメントでは、Round Controller機能で使用するエンティティ（Pydantic Model）とDuckDBテーブル定義を記述します。

---

## Pydantic Models

### 0. ExecutionSummary（拡張）

Orchestratorが全チーム完了後に生成する最終集約情報。`team_results`フィールドを`list[LeaderBoardEntry]`に変更します。

**ファイル**: `src/mixseek/orchestrator/models.py`

```python
from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field


class ExecutionSummary(BaseModel):
    """全チームの完了後に生成される最終集約情報"""

    execution_id: str = Field(description="実行識別子(UUID)")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_results: list[LeaderBoardEntry] = Field(default_factory=list, description="各チームの最高スコアSubmission")  # 変更: RoundResult → LeaderBoardEntry
    best_team_id: str | None = Field(default=None, description="最高スコアチームID")
    best_score: float | None = Field(default=None, ge=0.0, le=100.0, description="最高評価スコア（0-100スケール）")  # 変更: 0-1 → 0-100
    total_execution_time_seconds: float = Field(gt=0, description="総実行時間（秒）")
    failed_teams_info: list[FailedTeamInfo] = Field(default_factory=list, description="失敗チームの詳細情報")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="サマリー作成日時",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_teams(self) -> int:
        """総チーム数"""
        return len(self.team_results) + len(self.failed_teams_info)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completed_teams(self) -> int:
        """完了チーム数"""
        return len(self.team_results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_teams(self) -> int:
        """失敗チーム数"""
        return len(self.failed_teams_info)
```

**変更点**:
- `team_results`: `list[RoundResult]` → `list[LeaderBoardEntry]`に変更（各チームの最高スコアSubmission）
- `best_score`: 0.0-1.0 → 0.0-100.0に変更

---

### 1. OrchestratorTask（拡張）

オーケストレータから受け取るタスク定義。ラウンド設定フィールドを追加します。

**ファイル**: `src/mixseek/orchestrator/models.py`

```python
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class OrchestratorTask(BaseModel):
    """ユーザプロンプトから生成されるタスク定義"""

    execution_id: str = Field(default_factory=lambda: str(uuid4()), description="実行一意識別子(UUID)")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_configs: list[Path] = Field(description="チーム設定TOMLパスリスト")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="作成日時")
    timeout_seconds: int = Field(gt=0, description="チーム単位タイムアウト（秒）")

    # 新規追加: ラウンド設定
    max_rounds: int = Field(default=5, ge=1, description="最大ラウンド数")
    min_rounds: int = Field(default=2, ge=1, description="最小ラウンド数（LLM判定前の必須ラウンド数）")
    submission_timeout_seconds: int = Field(default=300, gt=0, description="Submissionタイムアウト（秒）")
    judgment_timeout_seconds: int = Field(default=60, gt=0, description="次ラウンド判定タイムアウト（秒）")

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_prompt cannot be empty")
        return v

    @field_validator("team_configs")
    @classmethod
    def validate_team_configs(cls, v: list[Path]) -> list[Path]:
        if not v:
            raise ValueError("team_configs must have at least one config")
        return v

    @field_validator("min_rounds")
    @classmethod
    def validate_min_rounds(cls, v: int, info) -> int:
        """min_rounds <= max_rounds を検証"""
        # info.dataから他のフィールドにアクセス可能
        max_rounds = info.data.get("max_rounds")
        if max_rounds is not None and v > max_rounds:
            raise ValueError(f"min_rounds ({v}) must be <= max_rounds ({max_rounds})")
        return v
```

**変更点**:
- `max_rounds`: 最大ラウンド数（デフォルト: 5）
- `min_rounds`: 最小ラウンド数（デフォルト: 2、LLM判定前の必須ラウンド数）
- `submission_timeout_seconds`: Submissionタイムアウト（デフォルト: 300秒）
- `judgment_timeout_seconds`: 次ラウンド判定タイムアウト（デフォルト: 60秒）
- `validate_min_rounds`: min_rounds <= max_rounds のバリデーション

**理由**: Article 9（Data Accuracy Mandate）準拠。ラウンド設定をTOMLファイルからタスクに統合し、明示的なデータソースから取得します。

---

### 2. ImprovementJudgment（新規）

LLMによる改善見込み判定結果。

**ファイル**: `src/mixseek/round_controller/models.py`

```python
from pydantic import BaseModel, Field


class ImprovementJudgment(BaseModel):
    """LLMによる改善見込み判定結果"""

    should_continue: bool = Field(description="次ラウンドに進むべきか")
    reasoning: str = Field(description="判定理由の詳細説明")
    confidence_score: float = Field(ge=0.0, le=1.0, description="信頼度スコア（0.0-1.0の範囲）")
```

**理由**:
- Pydantic Field制約（`ge=0.0, le=1.0`）で自動検証
- EvaluatorのLLM-as-a-Judgeパターンと同じ構造

---

### 3. RoundState（新規）

各ラウンドの完全な状態を保持するdataclass。

**ファイル**: `src/mixseek/round_controller/models.py`

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RoundState(BaseModel):
    """各ラウンドの完全な状態"""

    round_number: int = Field(ge=1, description="ラウンド番号")
    submission_content: str = Field(description="Submission内容")
    evaluation_score: float = Field(ge=0.0, le=100.0, description="評価スコア（0-100スケール）")
    evaluation_feedback: str = Field(description="評価フィードバック")
    improvement_judgment: ImprovementJudgment | None = Field(default=None, description="改善見込み判定結果")
    round_started_at: datetime = Field(description="ラウンド開始日時")
    round_ended_at: datetime = Field(description="ラウンド終了日時")
    message_history: list[dict[str, Any]] = Field(default_factory=list, description="Message History（JSON形式）")
```

**理由**:
- 各ラウンドの完全な状態を保持し、DuckDBに永続化
- 長期実行時のメモリ負荷を削減

---

### 4. LeaderBoardEntry（新規）

`leader_board`テーブルのレコード。

**ファイル**: `src/mixseek/models/leaderboard.py`

```python
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class LeaderBoardEntry(BaseModel):
    """leader_boardテーブルのレコード"""

    id: int | None = Field(default=None, description="自動採番される一意なID")
    execution_id: str = Field(description="タスクID（単一のユーザクエリに紐づくID）")
    team_id: str = Field(description="team_id")
    team_name: str = Field(description="チーム名")
    round_number: int = Field(ge=1, description="ラウンド番号")
    submission_content: str = Field(description="チームからのSubmission内容")
    submission_format: str = Field(default="md", description="Submissionのフォーマット情報（デフォルト: md）")
    score: float = Field(ge=0.0, le=100.0, description="Evaluatorからの評価スコア（0-100）")
    score_details: dict[str, Any] = Field(description="Evaluatorからの各評価指標のスコア内訳、コメント（JSON形式）")
    final_submission: bool = Field(default=False, description="最終ラウンドのSubmissionかどうかを示すフラグ")
    exit_reason: str | None = Field(default=None, description="ラウンド終了の理由（例: 'max rounds reached', 'no improvement expected'）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="レコード作成日時")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="レコード更新日時")
```

**理由**:
- Round Controllerの最終アウトプットとしてオーケストレータに返される
- DuckDBの`leader_board`テーブルと1:1対応

---

### 5. RoundResult（廃止予定）

既存の`RoundResult`は単一ラウンドの内部表現として使用されますが、**Round Controllerの最終戻り値としては使用しません**。

複数ラウンド対応では、Round Controllerは**最高スコアのラウンドの`LeaderBoardEntry`**をOrchestratorに返します（FR-007準拠）。

**既存実装との互換性**:
- 内部的には各ラウンドの状態を`RoundState`で管理
- 最終的に最高スコアのラウンドを特定し、`LeaderBoardEntry`として返す
- `RoundResult`は既存コードとの互換性のため一時的に保持される可能性がありますが、本仕様では使用しません

---

## DuckDBテーブル定義

### 1. round_status（新規）

チームがどのように行動したかを記録する役割を持つ。

```sql
CREATE TABLE IF NOT EXISTS round_status (
    id INTEGER PRIMARY KEY,
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,
    should_continue BOOLEAN NULL,
    reasoning TEXT NULL,
    confidence_score FLOAT NULL,
    round_started_at TIMESTAMP NULL,
    round_ended_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (execution_id, team_id, round_number)
);

CREATE INDEX IF NOT EXISTS idx_round_status_execution_team_round
ON round_status (execution_id, team_id, round_number DESC);
```

**カラム説明**:
- `id`: 自動採番される一意なID
- `execution_id`: タスクID（単一のユーザクエリに紐づくID）
- `team_id`: team_id
- `team_name`: チーム名
- `round_number`: ラウンド番号
- `should_continue`: 改善見込み判定結果（TRUE: 継続すべき、FALSE: 終了すべき、NULL: 未判定）
- `reasoning`: 判定理由の詳細説明
- `confidence_score`: 信頼度スコア（0-1の範囲）
- `round_started_at`: ラウンド開始日時
- `round_ended_at`: ラウンド終了日時
- `created_at`: レコード作成日時
- `updated_at`: レコード更新日時

**UNIQUE制約**: `(execution_id, team_id, round_number)` の組み合わせで一意性を保証

**INDEX**: `execution_id, team_id, round_number DESC` でラウンド履歴照会を最適化

---

### 2. leader_board（新規）

各チーム、各ラウンドのSubmissionと評価結果を記録する役割を持つ。

```sql
CREATE TABLE IF NOT EXISTS leader_board (
    id INTEGER PRIMARY KEY,
    execution_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    round_number INTEGER NOT NULL,
    submission_content TEXT NOT NULL,
    submission_format VARCHAR NOT NULL DEFAULT 'md',
    score FLOAT NOT NULL,
    score_details JSON NOT NULL,
    final_submission BOOLEAN NOT NULL DEFAULT FALSE,
    exit_reason VARCHAR NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (execution_id, team_id, round_number)
);

CREATE INDEX IF NOT EXISTS idx_leader_board_execution_score
ON leader_board (execution_id, score DESC, round_number DESC);
```

**カラム説明**:
- `id`: 自動採番される一意なID
- `execution_id`: タスクID（単一のユーザクエリに紐づくID）
- `team_id`: team_id
- `team_name`: チーム名
- `round_number`: ラウンド番号
- `submission_content`: チームからのSubmission内容
- `submission_format`: Submissionのフォーマット情報（デフォルト: md）
- `score`: Evaluatorからの評価スコア（0-100）
- `score_details`: Evaluatorからの各評価指標のスコア内訳、コメント（JSON形式）
- `final_submission`: 最終ラウンドのSubmissionかどうかを示すフラグ
- `exit_reason`: ラウンド終了の理由（例: "max rounds reached", "no improvement expected"）
- `created_at`: レコード作成日時
- `updated_at`: レコード更新日時

**UNIQUE制約**: `(execution_id, team_id, round_number)` の組み合わせで一意性を保証

**INDEX**: `execution_id, score DESC, round_number DESC` でタスクごとのランキング照会とタイブレークを最適化

---

## エンティティ関係図

```
┌─────────────────────────────────────────────────────────────────┐
│                        Orchestrator                              │
│  - 各チームにOrchestratorTaskを渡す                               │
│  - 各チームからLeaderBoardEntryを受け取る（最終戻り値）           │
│  - ExecutionSummary.team_results = list[LeaderBoardEntry]       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     OrchestratorTask                             │
│  - execution_id: str                                             │
│  - max_rounds: int                                               │
│  - min_rounds: int                                               │
│  - submission_timeout_seconds: int                               │
│  - judgment_timeout_seconds: int                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Round Controller                             │
│  - 複数ラウンドをループ実行                                      │
│  - 各ラウンドでRoundStateを生成                                  │
│  - 最終的に最高スコアのLeaderBoardEntryを返す ←★ 最終戻り値     │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ↓                       ↓
      ┌──────────────────┐    ┌──────────────────┐
      │   RoundState     │    │ ImprovementJudgment│
      │  (各ラウンド)     │    │  (LLM判定結果)    │
      ├──────────────────┤    ├──────────────────┤
      │ round_number     │    │ should_continue  │
      │ submission       │    │ reasoning        │
      │ score (0-100)    │    │ confidence_score │
      │ feedback         │    │                  │
      │ judgment         │───►│                  │
      └──────────────────┘    └──────────────────┘
                │
                ↓
      ┌──────────────────┐
      │ LeaderBoardEntry │ ←★ Round Controllerの最終戻り値
      │  (最高スコア)     │    Orchestratorに返される
      ├──────────────────┤
      │ execution_id     │
      │ team_id          │
      │ round_number     │
      │ score (0-100)    │
      │ final_submission │ ← TRUE
      │ exit_reason      │ ← "max rounds reached" など
      └──────────────────┘
                │
                ↓
      ┌──────────────────┐
      │  DuckDB Tables   │
      ├──────────────────┤
      │ round_status     │ ← すべてのラウンドの判定結果
      │ leader_board     │ ← すべてのラウンドのSubmission、最終フラグ付き
      └──────────────────┘
```

**データフロー**:
1. Orchestrator → OrchestratorTaskを各RoundControllerに渡す
2. RoundController → 複数ラウンドを実行し、各ラウンドでRoundStateを生成
3. RoundController → 各ラウンド終了後にImprovementJudgmentを実行
4. RoundController → すべてのラウンド終了後、最高スコアのLeaderBoardEntryを特定
5. RoundController → LeaderBoardEntryをOrchestratorに返す（FR-007準拠）
6. Orchestrator → すべてのチームからLeaderBoardEntryを受け取り、ExecutionSummaryを生成

---

## バリデーションルール

### 1. OrchestratorTask
- `user_prompt`: 空文字列不可
- `team_configs`: 最低1つのチーム設定必須
- `max_rounds`: 1以上
- `min_rounds`: 1以上かつ`max_rounds`以下
- `submission_timeout_seconds`: 正の整数
- `judgment_timeout_seconds`: 正の整数

### 2. ImprovementJudgment
- `confidence_score`: 0.0以上1.0以下

### 3. RoundState
- `round_number`: 1以上
- `evaluation_score`: 0.0以上100.0以下

### 4. LeaderBoardEntry
- `round_number`: 1以上
- `score`: 0.0以上100.0以下

---

## データフロー

### 複数ラウンド実行フロー

1. **Orchestrator** → `OrchestratorTask`作成（execution_id、ラウンド設定含む）
2. **Orchestrator** → `RoundController`にタスクを渡す
3. **RoundController** → **ラウンドループ開始**（最大max_roundsまで）

   **各ラウンドで以下を実行**:
   - Leader Agentを実行してSubmissionを取得
   - Evaluatorで評価し、`RoundState`に保存
   - `round_status`テーブルに記録（round_started_at、round_ended_at）
   - `leader_board`テーブルに記録（スコア、submission_content）

4. **RoundController** → 改善見込み判定を実行（ラウンド終了後）
   - **(a)** 最小ラウンド数到達確認（min_rounds未満なら次ラウンドへ）
   - **(b)** LLM-as-a-Judgeによる改善見込み判定（Pydantic AI）
   - **(c)** 最大ラウンド数到達確認（max_rounds到達なら終了）

5. **RoundController** → 判定結果を`round_status`テーブルに更新（should_continue、reasoning、confidence_score）

6. **RoundController** → 次ラウンド継続または終了判定
   - 継続の場合: プロンプトを整形（過去のSubmission履歴、評価フィードバック、ランキング情報）して次ラウンドへ
   - 終了の場合: 最高スコアのラウンドを特定

7. **RoundController** → 終了時の処理
   - 最高スコアのラウンドの`leader_board`レコードを取得
   - `final_submission`フラグをTRUEに更新
   - `exit_reason`を記録（"max rounds reached"、"no improvement expected"）
   - 該当する**`LeaderBoardEntry`をOrchestratorに返す**（FR-007準拠）

8. **Orchestrator** → 各チームから`LeaderBoardEntry`を受け取る
9. **Orchestrator** → 全チーム間で最高スコアのチームを特定
10. **Orchestrator** → `ExecutionSummary`を生成（`team_results`は各チームの`LeaderBoardEntry`のリスト）

---

## 実装ファイル対応表

| エンティティ | ファイルパス | 用途 |
|-------------|-------------|------|
| ExecutionSummary | `src/mixseek/orchestrator/models.py` | Orchestratorの最終集約情報（変更: team_resultsをLeaderBoardEntryのリストに） |
| OrchestratorTask | `src/mixseek/orchestrator/models.py` | オーケストレータタスク（変更: ラウンド設定追加） |
| ImprovementJudgment | `src/mixseek/round_controller/models.py` | LLM改善見込み判定結果（新規） |
| RoundState | `src/mixseek/round_controller/models.py` | 各ラウンドの完全な状態（新規） |
| LeaderBoardEntry | `src/mixseek/models/leaderboard.py` | Round Controllerの最終戻り値、DuckDBレコード（新規） |
| round_status DDL | `src/mixseek/storage/schema.py` | DuckDBスキーマ定義（新規） |
| leader_board DDL | `src/mixseek/storage/schema.py` | DuckDBスキーマ定義（新規） |

---

## Phase 1完了

data-model.mdの生成が完了しました。次にcontracts/ディレクトリにDuckDBスキーマ定義を出力します。
