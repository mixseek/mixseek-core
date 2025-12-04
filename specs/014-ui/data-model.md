# Data Model: Mixseek UI

**Feature**: 076-ui | **Date**: 2025-11-06 | **Phase**: 1 (Design & Contracts)

## Overview

本ドキュメントは、Mixseek UIで使用するデータモデルを定義する。すべてのモデルはPydantic v2を使用して型安全性を確保し、Article 16（Python Type Safety Mandate）に準拠する。

## Design Principles

1. **型安全性**: すべてのフィールドに明示的な型アノテーションを付与
2. **バリデーション**: Pydantic Validatorsで不正データを早期検出
3. **DRY**: 共通フィールドはBaseModelで定義
4. **シリアライズ可能性**: `st.session_state`格納のためpickle可能なオブジェクトのみ使用
5. **Article 9準拠**: デフォルト値の暗黙的使用を避け、必須フィールドは明示的に要求

## Entity Overview

| Entity | Purpose | Source |
|--------|---------|--------|
| ConfigFile | TOML設定ファイルのメタデータと内容 | `$MIXSEEK_WORKSPACE/configs/*.toml` |
| Orchestration | オーケストレーション定義 | TOML内の`[[orchestrations]]`セクション |
| MemberAgent | Member Agent定義 | TOML内の`[[member_agents]]`セクション |
| LeaderAgent | Leader Agent定義 | TOML内の`[[leader_agents]]`セクション |
| Execution | タスク実行レコード | `mixseek.db` executions テーブル |
| LeaderboardEntry | リーダーボードエントリ | `mixseek.db` teams テーブル |
| Submission | チームのサブミッション | `mixseek.db` submissions テーブル |
| HistoryEntry | 実行履歴エントリ | `mixseek.db` executions テーブル（履歴ページ用） |

---

## 1. Config File Models

### 1.1 ConfigFile

**Purpose**: TOML設定ファイルのメタデータと内容を保持

**File**: `src/mixseek/ui/models/config.py`

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from datetime import datetime


class ConfigFile(BaseModel):
    """TOML設定ファイルのメタデータ"""

    file_path: Path = Field(..., description="設定ファイルの絶対パス")
    file_name: str = Field(..., description="ファイル名（拡張子含む）")
    last_modified: datetime = Field(..., description="最終更新日時")
    content: str = Field(..., description="TOML文字列（生データ）")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: Path) -> Path:
        """ファイルパスが存在し、.toml拡張子を持つことを検証"""
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        if v.suffix != ".toml":
            raise ValueError(f"File must have .toml extension: {v}")
        return v

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """ファイル名が空でないことを検証"""
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v

    @property
    def display_name(self) -> str:
        """UIで表示するファイル名（拡張子なし）"""
        return self.file_name.replace(".toml", "")

    class Config:
        frozen = False  # Streamlit session_stateで変更可能にする
```

### 1.2 MemberAgent

**Purpose**: TOML内のMember Agent定義

**File**: `src/mixseek/ui/models/config.py`

```python
class MemberAgent(BaseModel):
    """Member Agent定義"""

    agent_id: str = Field(..., description="Agent識別子（TOML内のキー）")
    provider: str = Field(..., description="プロバイダー名（例: anthropic, google-adk）")
    model: str = Field(..., description="モデル名（例: claude-sonnet-4-5）")
    system_prompt: str | None = Field(None, description="システムプロンプト")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature設定")
    max_tokens: int | None = Field(None, gt=0, description="最大トークン数")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Agent IDが空でないことを検証"""
        if not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """プロバイダー名が空でないことを検証"""
        if not v.strip():
            raise ValueError("Provider cannot be empty")
        return v
```

### 1.3 LeaderAgent

**Purpose**: TOML内のLeader Agent定義

**File**: `src/mixseek/ui/models/config.py`

```python
class LeaderAgent(BaseModel):
    """Leader Agent定義"""

    agent_id: str = Field(..., description="Agent識別子（TOML内のキー）")
    provider: str = Field(..., description="プロバイダー名（例: anthropic, google-adk）")
    model: str = Field(..., description="モデル名（例: claude-sonnet-4-5）")
    system_prompt: str | None = Field(None, description="システムプロンプト")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature設定")
    max_tokens: int | None = Field(None, gt=0, description="最大トークン数")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Agent IDが空でないことを検証"""
        if not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """プロバイダー名が空でないことを検証"""
        if not v.strip():
            raise ValueError("Provider cannot be empty")
        return v
```

**Note**: MemberAgentとLeaderAgentは現状同一構造だが、将来的な拡張可能性（Leader固有の設定追加）を考慮し、別モデルとして定義する。

### 1.4 Orchestration

**Purpose**: TOML内のオーケストレーション定義

**File**: `src/mixseek/ui/models/config.py`

```python
class Orchestration(BaseModel):
    """オーケストレーション定義"""

    orchestration_id: str = Field(..., description="オーケストレーション識別子")
    leader_agent_id: str = Field(..., description="使用するLeader AgentのID")
    member_agent_ids: list[str] = Field(..., description="使用するMember AgentのIDリスト")
    description: str | None = Field(None, description="オーケストレーションの説明")

    @field_validator("orchestration_id")
    @classmethod
    def validate_orchestration_id(cls, v: str) -> str:
        """オーケストレーションIDが空でないことを検証"""
        if not v.strip():
            raise ValueError("Orchestration ID cannot be empty")
        return v

    @field_validator("leader_agent_id")
    @classmethod
    def validate_leader_agent_id(cls, v: str) -> str:
        """Leader Agent IDが空でないことを検証"""
        if not v.strip():
            raise ValueError("Leader Agent ID cannot be empty")
        return v

    @field_validator("member_agent_ids")
    @classmethod
    def validate_member_agent_ids(cls, v: list[str]) -> list[str]:
        """Member Agent IDリストが空でないことを検証"""
        if not v:
            raise ValueError("At least one member agent is required")
        if any(not agent_id.strip() for agent_id in v):
            raise ValueError("Member Agent ID cannot be empty")
        return v

    @property
    def display_name(self) -> str:
        """UIで表示する名前"""
        return self.orchestration_id
```

### 1.5 OrchestrationOption

**Purpose**: 実行ページのドロップダウン選択肢（ファイル名 + オーケストレーション名）

**File**: `src/mixseek/ui/models/config.py`

```python
class OrchestrationOption(BaseModel):
    """オーケストレーション選択肢（UI用）"""

    config_file_name: str = Field(..., description="設定ファイル名")
    orchestration_id: str = Field(..., description="オーケストレーションID")
    display_label: str = Field(..., description="UIに表示するラベル")

    @classmethod
    def from_config_and_orch(
        cls, config_file_name: str, orchestration: Orchestration
    ) -> "OrchestrationOption":
        """ConfigFileとOrchestrationから生成"""
        display_label = f"{config_file_name} - {orchestration.orchestration_id}"
        return cls(
            config_file_name=config_file_name,
            orchestration_id=orchestration.orchestration_id,
            display_label=display_label,
        )

    class Config:
        frozen = True  # イミュータブル
```

---

## 2. Execution Models

### 2.1 Execution

**Purpose**: タスク実行レコード（mixseek.db executions テーブル）

**File**: `src/mixseek/ui/models/execution.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """実行ステータス"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Execution(BaseModel):
    """タスク実行レコード"""

    execution_id: str = Field(..., description="実行ID（UUID）")
    prompt: str = Field(..., description="タスクプロンプト")
    orchestration_id: str = Field(..., description="使用したオーケストレーションID")
    config_file_name: str = Field(..., description="使用した設定ファイル名")
    status: ExecutionStatus = Field(..., description="実行ステータス")
    created_at: datetime = Field(..., description="実行開始日時")
    completed_at: datetime | None = Field(None, description="実行完了日時")
    error_message: str | None = Field(None, description="エラーメッセージ（失敗時）")
    result_summary: str | None = Field(None, description="結果サマリー（成功時）")

    @property
    def duration_seconds(self) -> float | None:
        """実行時間（秒）"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()

    @property
    def prompt_preview(self) -> str:
        """プロンプトのプレビュー（最初の100文字）"""
        max_length = 100
        if len(self.prompt) <= max_length:
            return self.prompt
        return self.prompt[:max_length] + "..."

    class Config:
        use_enum_values = True  # Enumを文字列値としてシリアライズ
```

---

## 3. Leaderboard Models

### 3.1 LeaderboardEntry

**Purpose**: リーダーボードエントリ（mixseek.db teams テーブル）

**File**: `src/mixseek/ui/models/leaderboard.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime


class LeaderboardEntry(BaseModel):
    """リーダーボードエントリ"""

    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    total_score: float = Field(..., description="合計スコア")
    rank: int = Field(..., ge=1, description="順位（1位からの整数）")
    last_updated: datetime = Field(..., description="最終更新日時")
    execution_id: str = Field(..., description="紐づく実行ID")

    @property
    def is_top(self) -> bool:
        """1位かどうか"""
        return self.rank == 1
```

### 3.2 Submission

**Purpose**: チームのサブミッション（mixseek.db submissions テーブル）

**File**: `src/mixseek/ui/models/leaderboard.py`

```python
class Submission(BaseModel):
    """サブミッション（チームの提出）"""

    submission_id: str = Field(..., description="サブミッションID")
    team_id: str = Field(..., description="チームID")
    execution_id: str = Field(..., description="実行ID")
    score: float = Field(..., description="スコア")
    content: str = Field(..., description="サブミッション内容")
    submitted_at: datetime = Field(..., description="提出日時")
    round_number: int | None = Field(None, ge=1, description="ラウンド番号（将来実装）")

    @property
    def content_preview(self) -> str:
        """内容のプレビュー（最初の200文字）"""
        max_length = 200
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
```

---

## 4. History Models

### 4.1 HistoryEntry

**Purpose**: 履歴ページの実行履歴エントリ（mixseek.db executions テーブルから生成）

**File**: `src/mixseek/ui/models/history.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from mixseek.ui.models.execution import ExecutionStatus


class HistoryEntry(BaseModel):
    """履歴ページ用の実行履歴エントリ"""

    execution_id: str = Field(..., description="実行ID")
    prompt_preview: str = Field(..., description="プロンプト概要（最初の100文字）")
    created_at: datetime = Field(..., description="実行開始日時")
    status: ExecutionStatus = Field(..., description="実行ステータス")
    orchestration_display: str = Field(
        ..., description="オーケストレーション表示名（ファイル名 - オーケストレーション名）"
    )
    config_file_name: str = Field(..., description="使用した設定ファイル名")
    orchestration_id: str = Field(..., description="使用したオーケストレーションID")

    @classmethod
    def from_execution(cls, execution: "Execution") -> "HistoryEntry":
        """Executionモデルから生成"""
        from mixseek.ui.models.execution import Execution

        orchestration_display = (
            f"{execution.config_file_name} - {execution.orchestration_id}"
        )
        return cls(
            execution_id=execution.execution_id,
            prompt_preview=execution.prompt_preview,
            created_at=execution.created_at,
            status=execution.status,
            orchestration_display=orchestration_display,
            config_file_name=execution.config_file_name,
            orchestration_id=execution.orchestration_id,
        )

    class Config:
        use_enum_values = True
```

---

## 5. Session State Models

### 5.1 SessionState

**Purpose**: Streamlit Session Stateの型定義（型安全性確保）

**File**: `src/mixseek/ui/models/session.py`

```python
from pydantic import BaseModel, Field
from mixseek.ui.models.execution import ExecutionStatus


class SessionState(BaseModel):
    """Streamlit Session Stateの型定義"""

    # 実行ページ
    selected_orchestration: str | None = Field(
        None, description="選択されたオーケストレーション（display_label）"
    )
    execution_status: ExecutionStatus = Field(
        ExecutionStatus.PENDING, description="実行ステータス"
    )
    current_execution_id: str | None = Field(None, description="現在の実行ID")
    task_prompt: str = Field("", description="タスクプロンプト")

    # 履歴ページ
    history_page_number: int = Field(1, ge=1, description="履歴ページ番号")
    history_sort_order: str = Field("desc", description="ソート順序（asc/desc）")
    history_status_filter: str | None = Field(None, description="ステータスフィルタ")

    # 設定ページ
    selected_config_file: str | None = Field(None, description="選択された設定ファイル名")

    class Config:
        use_enum_values = True
        validate_assignment = True  # 代入時もバリデーション
```

**Note**: この型定義は型ヒントとして使用するが、実際の`st.session_state`は辞書ライクなオブジェクトであるため、Pydanticモデルとして直接インスタンス化するのではなく、型チェックの参考として使用する。

---

## 6. TOML Template

### 6.1 TOML_TEMPLATE

**Purpose**: 新規設定ファイル作成時のテンプレート

**File**: `src/mixseek/ui/constants.py`

```python
TOML_TEMPLATE = """# Mixseek Configuration File
# Created at: {timestamp}

# Member Agents
[[member_agents]]
agent_id = "example_member"
provider = "anthropic"
model = "claude-sonnet-4"
system_prompt = "You are a helpful assistant."
temperature = 0.7
max_tokens = 4096

# Leader Agents
[[leader_agents]]
agent_id = "example_leader"
provider = "google-adk"
model = "gemini-2.0-flash-exp"
system_prompt = "You are a team leader."
temperature = 0.5
max_tokens = 8192

# Orchestrations
[[orchestrations]]
orchestration_id = "example_orch"
leader_agent_id = "example_leader"
member_agent_ids = ["example_member"]
description = "Example orchestration configuration"
"""
```

---

## 7. Data Flow

### 7.1 Config File Loading Flow

```
ConfigService.list_config_files()
  ↓
  Path.glob("*.toml")
  ↓
  [ConfigFile(file_path=..., file_name=..., last_modified=..., content=...)]
  ↓
ConfigService.parse_toml(content)
  ↓
  tomli.loads(content) → dict
  ↓
  Extract member_agents → [MemberAgent(...)]
  Extract leader_agents → [LeaderAgent(...)]
  Extract orchestrations → [Orchestration(...)]
```

### 7.2 Orchestration Selection Flow

```
OrchestrationSelector.get_options()
  ↓
  For each ConfigFile:
    Parse TOML → [Orchestration(...)]
    Create OrchestrationOption.from_config_and_orch(...)
  ↓
  [OrchestrationOption(display_label="config1.toml - orch_a", ...)]
  ↓
  st.selectbox(options=[option.display_label for option in options])
  ↓
  st.session_state.selected_orchestration = "config1.toml - orch_a"
```

### 7.3 Execution Flow

```
User clicks "実行" button
  ↓
ExecutionService.run_orchestration(prompt, selected_orchestration)
  ↓
  Parse selected_orchestration → (config_file_name, orchestration_id)
  ↓
  Load ConfigFile
  ↓
  Call mixseek-core library (existing)
  ↓
  Create Execution(execution_id=..., status=RUNNING, ...)
  ↓
  Update st.session_state.execution_status = RUNNING
  ↓
  On completion:
    Update Execution(status=COMPLETED, result_summary=...)
    Save to mixseek.db
  ↓
  Update st.session_state.execution_status = COMPLETED
```

### 7.4 Leaderboard Loading Flow

```
LeaderboardService.fetch_leaderboard(execution_id)
  ↓
  conn = get_read_connection()
  ↓
  SELECT team_id, team_name, total_score, rank, last_updated
  FROM teams WHERE execution_id = ?
  ORDER BY rank ASC
  ↓
  [LeaderboardEntry(...)]
  ↓
  st.dataframe(df)
```

### 7.5 History Loading Flow

```
HistoryService.fetch_history(page_number, sort_order, status_filter)
  ↓
  conn = get_read_connection()
  ↓
  SELECT execution_id, prompt, created_at, status, config_file_name, orchestration_id
  FROM executions
  WHERE status = ? (if filter)
  ORDER BY created_at {sort_order}
  LIMIT 50 OFFSET (page_number - 1) * 50
  ↓
  [Execution(...)]
  ↓
  [HistoryEntry.from_execution(exec) for exec in executions]
  ↓
  st.dataframe(df)
```

---

## Summary

### Model Files Structure

```
src/mixseek/ui/models/
├── __init__.py
├── config.py          # ConfigFile, MemberAgent, LeaderAgent, Orchestration, OrchestrationOption
├── execution.py       # Execution, ExecutionStatus
├── leaderboard.py     # LeaderboardEntry, Submission
├── history.py         # HistoryEntry
└── session.py         # SessionState (型ヒント用)

src/mixseek/ui/
├── constants.py       # TOML_TEMPLATE
└── ...
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pydantic v2使用 | 型安全性、バリデーション、Article 16準拠 |
| Enum for ExecutionStatus | タイプセーフな状態管理 |
| `@property`でプレビュー生成 | UIで長いテキストを短縮表示 |
| `frozen=True`でイミュータブル化 | OrchestrationOptionは変更不可にして安全性向上 |
| `from_execution()`クラスメソッド | HistoryEntryをExecutionから生成する明示的な変換 |
| `field_validator`で早期エラー検出 | 不正データを即座に検出（Article 9準拠） |

### Next Steps (Phase 1 Continuation)

1. **quickstart.md生成**: Streamlitアプリ起動方法、環境変数設定手順
2. **agent context更新**: Streamlit, Plotly, DuckDB技術コンテキスト追加

Phase 1完了後、`/speckit.tasks`でtasks.mdを生成し、Phase 2（実装）へ移行する。
