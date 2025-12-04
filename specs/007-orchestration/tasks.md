# Implementation Tasks: MixSeek-Core Orchestrator

**Feature**: MixSeek-Core Orchestrator - マルチチーム協調実行
**Branch**: `025-mixseek-core-orchestration`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

**⚠️ IMPORTANT NOTE (2025-11)**:
このドキュメントは歴史的な実装タスクリストです。以下のクラス/関数は**Feature 101で廃止・削除されました**：
- `OrchestratorConfig` → `OrchestratorSettings`に統合
- `TeamReference` → `OrchestratorSettings.teams`に統合
- `load_orchestrator_config()` → `load_orchestrator_settings()`にリネーム

現在の実装については`specs/016-round-config/`を参照してください。

このドキュメントは、TDD（Test-Driven Development）アプローチに基づいた実装タスクリストです。

## Task Execution Strategy

- **Test-First**: Article 3に従い、すべての実装タスクの前にテストを作成
- **User Story順**: P1 → P2 → P3 の優先順位で実装
- **並列可能タスク**: `[P]`マーカーで明示
- **Independent Testing**: 各User Storyは独立してテスト可能

## Phase 1: Setup & Infrastructure

### T001: プロジェクト構造セットアップ
**File**: `src/mixseek/orchestrator/__init__.py`
**Description**: orchestratorディレクトリとパッケージ初期化ファイルを作成

```python
# src/mixseek/orchestrator/__init__.py
"""MixSeek-Core Orchestrator - マルチチーム協調実行"""

from mixseek.orchestrator.models import (
    ExecutionSummary,
    OrchestratorTask,
    RoundResult,
    TeamStatus,
)
from mixseek.orchestrator.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.orchestrator.round_controller import RoundController

__all__ = [
    "Orchestrator",
    "RoundController",
    "OrchestratorTask",
    "TeamStatus",
    "RoundResult",
    "ExecutionSummary",
    "load_orchestrator_settings",
]
```

**Dependencies**: なし
**Checkpoint**: パッケージ構造が正しく作成されている

---

### T002: テストディレクトリセットアップ
**File**: `tests/unit/orchestrator/__init__.py`, `tests/integration/test_orchestrator_e2e.py`
**Description**: テスト用ディレクトリとファイルを作成

```bash
mkdir -p tests/unit/orchestrator
touch tests/unit/orchestrator/__init__.py
touch tests/unit/orchestrator/test_models.py
touch tests/unit/orchestrator/test_orchestrator.py
touch tests/unit/orchestrator/test_round_controller.py
touch tests/integration/test_orchestrator_e2e.py
```

**Dependencies**: なし
**Checkpoint**: テストディレクトリ構造が作成されている

---

## Phase 2: Foundational Models (Blocking Prerequisites)

これらのモデルはすべてのUser Storyで使用されるため、最初に実装する必要があります。

### T003 [P]: [US1] OrchestratorTask モデルのテスト作成
**Story**: User Story 1 - プロンプト受信とマルチチーム起動
**File**: `tests/unit/orchestrator/test_models.py`
**Description**: OrchestratorTaskモデルのユニットテストを作成（TDD: Red phase）

```python
import pytest
from pathlib import Path
from mixseek.orchestrator.models import OrchestratorTask

def test_orchestrator_task_creation():
    """OrchestratorTask作成テスト"""
    task = OrchestratorTask(
        user_prompt="テストプロンプト",
        team_configs=[Path("team1.toml"), Path("team2.toml")],
        timeout_seconds=600,
    )
    assert task.user_prompt == "テストプロンプト"
    assert len(task.team_configs) == 2
    assert task.timeout_seconds == 600
    assert task.task_id is not None  # UUIDが自動生成される
    assert task.created_at is not None

def test_orchestrator_task_validation():
    """OrchestratorTask バリデーションテスト"""
    with pytest.raises(ValueError):
        OrchestratorTask(
            user_prompt="",  # 空文字列
            team_configs=[],
            timeout_seconds=600,
        )

    with pytest.raises(ValueError):
        OrchestratorTask(
            user_prompt="テスト",
            team_configs=[],  # 空リスト
            timeout_seconds=600,
        )
```

**Dependencies**: なし
**Expected**: テスト失敗（Red）

---

### T004 [P]: [US1] TeamStatus モデルのテスト作成
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_models.py`
**Description**: TeamStatusモデルのユニットテストを作成

```python
def test_team_status_creation():
    """TeamStatus作成テスト"""
    status = TeamStatus(
        team_id="team-001",
        team_name="Test Team",
    )
    assert status.team_id == "team-001"
    assert status.status == "pending"
    assert status.current_round == 0

def test_team_status_transitions():
    """TeamStatus ステータス遷移テスト"""
    status = TeamStatus(team_id="team-001", team_name="Test Team")
    status.status = "running"
    assert status.status == "running"

    status.status = "completed"
    assert status.status == "completed"
```

**Dependencies**: なし
**Expected**: テスト失敗（Red）

---

### T005 [P]: [US2] RoundResult モデルのテスト作成
**Story**: User Story 2 - ラウンド進行管理と終了判定
**File**: `tests/unit/orchestrator/test_models.py`
**Description**: RoundResultモデルのユニットテストを作成

```python
from pydantic_ai import RunUsage

def test_round_result_creation():
    """RoundResult作成テスト"""
    result = RoundResult(
        team_id="team-001",
        team_name="Test Team",
        round_number=1,
        submission_content="テストSubmission",
        evaluation_score=0.85,
        evaluation_feedback="良好",
        usage=RunUsage(input_tokens=100, output_tokens=200, requests=1),
        execution_time_seconds=30.5,
    )
    assert result.team_id == "team-001"
    assert result.evaluation_score == 0.85
    assert result.execution_time_seconds == 30.5

def test_round_result_validation():
    """RoundResult バリデーションテスト"""
    with pytest.raises(ValueError):
        RoundResult(
            team_id="team-001",
            team_name="Test Team",
            round_number=1,
            submission_content="テスト",
            evaluation_score=1.5,  # 範囲外
            evaluation_feedback="",
            usage=RunUsage(),
            execution_time_seconds=30.0,
        )
```

**Dependencies**: なし
**Expected**: テスト失敗（Red）

---

### T006 [P]: [US3] ExecutionSummary モデルのテスト作成
**Story**: User Story 3 - 実行全体の完了集約と終了通知
**File**: `tests/unit/orchestrator/test_models.py`
**Description**: ExecutionSummaryモデルのユニットテストを作成

```python
def test_execution_summary_creation():
    """ExecutionSummary作成テスト"""
    result1 = RoundResult(...)  # 略
    result2 = RoundResult(...)  # 略

    summary = ExecutionSummary(
        task_id="task-123",
        user_prompt="テストプロンプト",
        team_results=[result1, result2],
        best_team_id="team-001",
        best_score=0.92,
        total_execution_time_seconds=45.3,
    )

    assert summary.total_teams == 2
    assert summary.completed_teams == 2
    assert summary.failed_teams == 0
```

**Dependencies**: T005完了
**Expected**: テスト失敗（Red）

---

### T007 [P]: [US1] OrchestratorConfig モデルのテスト作成
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_models.py`
**Description**: OrchestratorConfigモデルのユニットテストを作成

```python
def test_orchestrator_config_creation():
    """OrchestratorConfig作成テスト"""
    config = OrchestratorConfig(
        timeout_per_team_seconds=600,
        teams=[
            TeamReference(config=Path("team1.toml")),
            TeamReference(config=Path("team2.toml")),
        ],
    )
    assert config.timeout_per_team_seconds == 600
    assert len(config.teams) == 2

def test_orchestrator_config_validation():
    """OrchestratorConfig バリデーションテスト"""
    with pytest.raises(ValueError):
        OrchestratorConfig(
            timeout_per_team_seconds=-1,  # 負の値
            teams=[],
        )
```

**Dependencies**: なし
**Expected**: テスト失敗（Red）

---

### T008: [Foundational] データモデル実装
**File**: `src/mixseek/orchestrator/models.py`
**Description**: 全データモデルを実装（TDD: Green phase）

```python
"""Orchestrator data models"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic_ai import RunUsage


class OrchestratorTask(BaseModel):
    """ユーザプロンプトから生成されるタスク定義"""

    task_id: str = Field(default_factory=lambda: str(uuid4()), description="タスク一意識別子")
    user_prompt: str = Field(description="ユーザプロンプト")
    team_configs: list[Path] = Field(description="チーム設定TOMLパスリスト")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="作成日時")
    timeout_seconds: int = Field(gt=0, description="チーム単位タイムアウト（秒）")

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


class TeamStatus(BaseModel):
    """特定チームの実行状態"""

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


class RoundResult(BaseModel):
    """1ラウンドの実行結果"""

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


class ExecutionSummary(BaseModel):
    """全チームの完了後に生成される最終集約情報"""

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
        """完了チーム数"""
        return sum(1 for r in self.team_results if r.evaluation_score is not None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_teams(self) -> int:
        """失敗チーム数"""
        return self.total_teams - self.completed_teams


class TeamReference(BaseModel):
    """チーム参照"""

    config: Path = Field(description="チーム設定TOMLファイルパス")


class OrchestratorConfig(BaseModel):
    """オーケストレータ設定"""

    timeout_per_team_seconds: int = Field(gt=0, description="チーム単位タイムアウト（秒）")
    teams: list[TeamReference] = Field(min_length=1, description="チーム参照リスト")
```

**Dependencies**: T003-T007完了
**Verification**: `pytest tests/unit/orchestrator/test_models.py` が全てパス（Green）
**Checkpoint**: ✅ Foundational Models完成

---

## Phase 3: User Story 1 - プロンプト受信とマルチチーム起動 (P1)

**Goal**: ユーザプロンプトを受け取り、複数チームのラウンドコントローラを起動してDuckDBに記録

### T009: [US1] RoundController テスト作成（モック版）
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_round_controller.py`
**Description**: RoundControllerの初期化とチーム情報取得のテストを作成

```python
import pytest
from pathlib import Path
from mixseek.orchestrator import RoundController

def test_round_controller_initialization():
    """RoundController初期化テスト"""
    controller = RoundController(
        team_config_path=Path("tests/fixtures/team1.toml"),
        workspace=Path("workspace"),
        round_number=1,
    )
    assert controller.get_team_id() is not None
    assert controller.get_team_name() is not None

def test_round_controller_invalid_config():
    """RoundController 不正な設定ファイルテスト"""
    with pytest.raises(FileNotFoundError):
        RoundController(
            team_config_path=Path("nonexistent.toml"),
            workspace=Path("workspace"),
        )
```

**Dependencies**: T008完了
**Expected**: テスト失敗（Red）

---

### T010: [US1] RoundController 基本実装
**Story**: User Story 1
**File**: `src/mixseek/orchestrator/round_controller.py`
**Description**: RoundControllerの初期化と基本メソッドを実装

```python
"""Round Controller - 単一チームの1ラウンド実行管理"""

import asyncio
import time
from pathlib import Path

from mixseek.agents.leader.config import TeamConfig, load_team_config
from mixseek.orchestrator.models import RoundResult


class RoundController:
    """単一チームの1ラウンド実行を管理"""

    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        round_number: int = 1,
    ) -> None:
        """RoundControllerインスタンス作成

        Args:
            team_config_path: チーム設定TOMLファイルパス
            workspace: ワークスペースパス
            round_number: ラウンド番号（初期実装では常に1）

        Raises:
            FileNotFoundError: team_config_pathが存在しない場合
            ValidationError: チーム設定が不正な場合
        """
        self.team_config = load_team_config(team_config_path, workspace)
        self.workspace = workspace
        self.round_number = round_number

    def get_team_id(self) -> str:
        """チーム識別子を取得"""
        return self.team_config.team_id

    def get_team_name(self) -> str:
        """チーム名を取得"""
        return self.team_config.team_name

    async def run_round(
        self,
        user_prompt: str,
        timeout_seconds: int,
    ) -> RoundResult:
        """1ラウンドを実行し、結果を返す（後続タスクで実装）"""
        raise NotImplementedError("T014で実装")
```

**Dependencies**: T009完了
**Verification**: `pytest tests/unit/orchestrator/test_round_controller.py` がパス
**Checkpoint**: RoundController基本実装完了

---

### T011: [US1] Orchestrator テスト作成（タスク生成）
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_orchestrator.py`
**Description**: Orchestratorのタスク生成テストを作成

```python
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from mixseek.orchestrator import Orchestrator, OrchestratorConfig, TeamReference

@pytest.fixture
def orchestrator_config():
    """テスト用オーケストレータ設定"""
    return OrchestratorConfig(
        timeout_per_team_seconds=600,
        teams=[
            TeamReference(config=Path("tests/fixtures/team1.toml")),
            TeamReference(config=Path("tests/fixtures/team2.toml")),
        ],
    )

def test_orchestrator_initialization(orchestrator_config):
    """Orchestrator初期化テスト"""
    orchestrator = Orchestrator(config=orchestrator_config, workspace=Path("workspace"))
    assert orchestrator.config == orchestrator_config

@pytest.mark.asyncio
async def test_orchestrator_execute_task_creation(orchestrator_config):
    """Orchestrator タスク生成テスト"""
    orchestrator = Orchestrator(config=orchestrator_config, workspace=Path("workspace"))

    # モックでRoundControllerを差し替え
    with patch("mixseek.orchestrator.orchestrator.RoundController") as mock_rc:
        mock_rc.return_value.run_round = AsyncMock(return_value=Mock())

        summary = await orchestrator.execute(user_prompt="テストプロンプト")

        # タスクが生成されていることを確認
        assert summary.user_prompt == "テストプロンプト"
```

**Dependencies**: T010完了
**Expected**: テスト失敗（Red）

---

### T012: [US1] Orchestrator 基本実装
**Story**: User Story 1
**File**: `src/mixseek/orchestrator/orchestrator.py`
**Description**: Orchestratorの初期化とタスク生成を実装

```python
"""Orchestrator - 複数チームの並列実行管理"""

import asyncio
import os
import time
from pathlib import Path

from mixseek.orchestrator.models import (
    ExecutionSummary,
    OrchestratorConfig,
    OrchestratorTask,
    RoundResult,
    TeamStatus,
)
from mixseek.orchestrator.round_controller import RoundController


def load_orchestrator_config(config_path: Path) -> OrchestratorConfig:
    """オーケストレータ設定TOML読み込み

    Args:
        config_path: 設定TOMLファイルパス

    Returns:
        OrchestratorConfig

    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    import tomllib

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return OrchestratorConfig(
        timeout_per_team_seconds=data["orchestrator"]["timeout_per_team_seconds"],
        teams=[
            {"config": Path(team["config"])}
            for team in data["orchestrator"]["teams"]
        ],
    )


class Orchestrator:
    """複数チームのラウンドコントローラを管理"""

    def __init__(
        self,
        config: OrchestratorConfig,
        workspace: Path | None = None,
    ) -> None:
        """Orchestratorインスタンス作成

        Args:
            config: オーケストレータ設定
            workspace: ワークスペースパス（Noneの場合はMIXSEEK_WORKSPACE環境変数から取得）

        Raises:
            EnvironmentError: MIXSEEK_WORKSPACE未設定時
        """
        self.config = config
        self.workspace = self._get_workspace(workspace)
        self.team_statuses: dict[str, TeamStatus] = {}

    def _get_workspace(self, workspace: Path | None) -> Path:
        """ワークスペースパス取得"""
        if workspace is not None:
            return workspace

        if "MIXSEEK_WORKSPACE" not in os.environ:
            raise OSError(
                "MIXSEEK_WORKSPACE environment variable is not set.\n"
                "Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace"
            )

        return Path(os.environ["MIXSEEK_WORKSPACE"])

    async def execute(
        self,
        user_prompt: str,
        timeout_seconds: int | None = None,
    ) -> ExecutionSummary:
        """ユーザプロンプトを受け取り、複数チームを並列実行（後続タスクで実装）"""
        raise NotImplementedError("T016で実装")

    async def get_team_status(self, team_id: str) -> TeamStatus:
        """特定チームのステータス取得"""
        if team_id not in self.team_statuses:
            raise KeyError(f"Team not found: {team_id}")
        return self.team_statuses[team_id]

    async def get_all_team_statuses(self) -> list[TeamStatus]:
        """全チームのステータス取得"""
        return list(self.team_statuses.values())
```

**Dependencies**: T011完了
**Verification**: `pytest tests/unit/orchestrator/test_orchestrator.py` がパス
**Checkpoint**: Orchestrator基本実装完了

---

### T013: [US1] 既存Evaluatorの統合テスト作成
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_evaluator_integration.py`
**Description**: 既存Evaluator（src/mixseek/evaluator/）がorchestratorコンテキストで正しく動作することを確認

**設計判断**:
- SimpleEvaluatorの代わりに既存実装（src/mixseek/evaluator/Evaluator）を使用
- DRY原則遵守（Article 10）: 評価ロジックの重複を回避
- 一貫性保証: すべてのチームで同じ評価基準を適用

```python
"""既存Evaluatorの統合テスト"""

from pathlib import Path

import pytest

from mixseek.evaluator import Evaluator, EvaluationRequest, EvaluationResult


def test_evaluator_basic_usage(tmp_path: Path) -> None:
    """既存Evaluatorの基本的な使用方法をテスト"""
    evaluator = Evaluator(workspace_path=tmp_path)

    request = EvaluationRequest(
        user_query="Pythonとは何ですか？",
        submission="Pythonは高水準プログラミング言語です。",
        team_id="test-team-001",
    )

    result: EvaluationResult = evaluator.evaluate(request)

    # EvaluationResultの検証
    assert isinstance(result, EvaluationResult)
    assert 0.0 <= result.overall_score <= 100.0  # 0-100スケール
    assert len(result.metrics) >= 1

    # MetricScoreの検証
    for metric in result.metrics:
        assert 0.0 <= metric.score <= 100.0
        assert isinstance(metric.metric_name, str)
        assert isinstance(metric.evaluator_comment, str)


def test_evaluator_result_structure() -> None:
    """EvaluationResultの構造が期待通りであることを確認"""
    evaluator = Evaluator()

    request = EvaluationRequest(
        user_query="Pythonの利点は何ですか？",
        submission="Pythonは読みやすく、豊富なライブラリがあり、コミュニティが活発です。",
        team_id="team-alpha-001",
    )

    result = evaluator.evaluate(request)

    # EvaluationResult構造の検証
    assert hasattr(result, "metrics")
    assert hasattr(result, "overall_score")
    assert isinstance(result.metrics, list)
    assert isinstance(result.overall_score, float)
```

**Dependencies**: T012完了
**Verification**: `pytest tests/unit/orchestrator/test_evaluator_integration.py` がパス
**Checkpoint**: 既存Evaluator統合テスト完了

---

### T014: [US1] RoundController.run_round() テスト作成
**Story**: User Story 1
**File**: `tests/unit/orchestrator/test_round_controller.py`
**Description**: RoundController.run_round()のテストを作成（既存Evaluatorを使用）

```python
from mixseek.evaluator import EvaluationResult
from mixseek.models.evaluation_result import MetricScore

@pytest.mark.asyncio
@patch("mixseek.orchestrator.round_controller.create_leader_agent")
@patch("mixseek.orchestrator.round_controller.AggregationStore")
@patch("mixseek.orchestrator.round_controller.Evaluator")
async def test_run_round_with_evaluator(
    mock_evaluator_class: MagicMock,
    mock_store_class: MagicMock,
    mock_create_leader: MagicMock,
    tmp_path: Path,
) -> None:
    """run_round()が既存Evaluatorを使用して正しく動作することをテスト"""

    # Leader Agentのモック
    mock_agent = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "テストSubmission"
    mock_result.all_messages.return_value = []
    mock_result.usage.return_value = MagicMock(input_tokens=100, output_tokens=50, requests=1)
    mock_agent.run.return_value = mock_result
    mock_create_leader.return_value = mock_agent

    # AggregationStoreのモック
    mock_store = AsyncMock()
    mock_store_class.return_value = mock_store

    # Evaluatorのモック（既存Evaluator）
    mock_evaluator = MagicMock()
    mock_evaluation_result = EvaluationResult(
        metrics=[
            MetricScore(metric_name="ClarityCoherence", score=85.5, evaluator_comment="明瞭です"),
            MetricScore(metric_name="Relevance", score=90.0, evaluator_comment="関連性が高い"),
        ],
        overall_score=87.75,  # 0-100スケール
    )
    mock_evaluator.evaluate.return_value = mock_evaluation_result
    mock_evaluator_class.return_value = mock_evaluator

    # RoundControllerの実行
    controller = RoundController(
        team_config_path=Path("tests/fixtures/team1.toml"),
        workspace=tmp_path,
        round_number=1,
    )

    result = await controller.run_round(
        user_prompt="テストプロンプト",
        timeout_seconds=60,
    )

    # 結果の検証（0-100スケール）
    assert result.evaluation_score == 87.75
    assert "明瞭です" in result.evaluation_feedback
```

**Dependencies**: T013完了
**Verification**: `pytest tests/unit/orchestrator/test_round_controller.py::test_run_round_with_evaluator` がパス
**Expected**: テスト失敗（Red）

---

### T015: [US1] RoundController.run_round() 実装
**Story**: User Story 1
**File**: `src/mixseek/orchestrator/round_controller.py`
**Description**: RoundController.run_round()を実装（Leader Agent実行、Evaluator実行、DuckDB記録）

```python
async def run_round(
    self,
    user_prompt: str,
    timeout_seconds: int,
) -> RoundResult:
    """1ラウンドを実行し、結果を返す"""
    start_time = time.time()

    # 1. Leader Agent実行
    from mixseek.agents.leader.agent import create_leader_agent
    from mixseek.agents.leader.dependencies import TeamDependencies

    # Member Agentマップ準備（簡易実装）
    member_agents = {}  # TODO: Member Agent実装後に追加

    leader_agent = create_leader_agent(self.team_config, member_agents)
    deps = TeamDependencies(
        team_id=self.team_config.team_id,
        team_name=self.team_config.team_name,
        workspace=self.workspace,
        round_number=self.round_number,
    )

    result = await leader_agent.run(user_prompt, deps=deps)
    submission_content = result.data
    message_history = result.all_messages()
    usage = result.usage()

    # 2. DuckDB記録（round_history）
    from mixseek.storage.aggregation_store import AggregationStore
    from mixseek.agents.leader.models import MemberSubmissionsRecord

    store = AggregationStore(db_path=self.workspace / "mixseek.db")

    # Member Agent応答記録（簡易版）
    member_record = MemberSubmissionsRecord(
        team_id=self.team_config.team_id,
        team_name=self.team_config.team_name,
        round_number=self.round_number,
        submissions=[],
    )

    await store.save_aggregation(member_record, message_history)

    # 3. Evaluator実行（既存Evaluatorを使用）
    from mixseek.evaluator import Evaluator, EvaluationRequest

    evaluator = Evaluator(workspace_path=self.workspace)
    request = EvaluationRequest(
        user_query=user_prompt,
        submission=submission_content,
        team_id=self.team_config.team_id,
    )

    # 同期メソッドを非同期コンテキストで実行
    result = await asyncio.to_thread(evaluator.evaluate, request)

    # 0-100スケールのスコアを取得
    evaluation_score = result.overall_score

    # 各メトリクスのコメントを統合してフィードバックを作成
    evaluation_feedback = "\n".join(
        [f"{metric.metric_name} ({metric.score:.2f}): {metric.evaluator_comment}" for metric in result.metrics]
    )

    # 4. DuckDB記録（leader_board）
    await store.save_to_leader_board(
        team_id=self.team_config.team_id,
        team_name=self.team_config.team_name,
        round_number=self.round_number,
        evaluation_score=evaluation_score,
        evaluation_feedback=evaluation_feedback,
        submission=submission_content,
        usage_info={
            "input_tokens": usage.input_tokens or 0,
            "output_tokens": usage.output_tokens or 0,
            "requests": usage.requests or 0,
        },
    )

    # 5. RoundResult生成
    execution_time = time.time() - start_time

    return RoundResult(
        team_id=self.team_config.team_id,
        team_name=self.team_config.team_name,
        round_number=self.round_number,
        submission_content=submission_content,
        evaluation_score=evaluation_score,
        evaluation_feedback=evaluation_feedback,
        usage=usage,
        execution_time_seconds=execution_time,
    )
```

**Dependencies**: T014完了
**Verification**: `pytest tests/unit/orchestrator/test_round_controller.py` がパス
**Checkpoint**: ✅ User Story 1 - RoundController完成

---

### T016: [US1] Orchestrator.execute() 実装
**Story**: User Story 1
**File**: `src/mixseek/orchestrator/orchestrator.py`
**Description**: Orchestrator.execute()を実装（複数チーム並列実行）

```python
async def execute(
    self,
    user_prompt: str,
    timeout_seconds: int | None = None,
) -> ExecutionSummary:
    """ユーザプロンプトを受け取り、複数チームを並列実行"""
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt cannot be empty")

    timeout = timeout_seconds or self.config.timeout_per_team_seconds

    # タスク生成
    task = OrchestratorTask(
        user_prompt=user_prompt,
        team_configs=[ref.config for ref in self.config.teams],
        timeout_seconds=timeout,
    )

    # TeamStatus初期化
    for ref in self.config.teams:
        # 一時的にチームIDを取得（設定読み込み）
        temp_config = load_team_config(ref.config, self.workspace)
        self.team_statuses[temp_config.team_id] = TeamStatus(
            team_id=temp_config.team_id,
            team_name=temp_config.team_name,
        )

    # RoundController作成
    controllers = [
        RoundController(
            team_config_path=ref.config,
            workspace=self.workspace,
            round_number=1,
        )
        for ref in self.config.teams
    ]

    # 並列実行
    start_time = time.time()

    results = await asyncio.gather(
        *[
            self._run_team(controller, user_prompt, timeout)
            for controller in controllers
        ],
        return_exceptions=True,
    )

    execution_time = time.time() - start_time

    # 結果収集
    team_results: list[RoundResult] = []
    for result in results:
        if isinstance(result, RoundResult):
            team_results.append(result)
            # TeamStatus更新
            self.team_statuses[result.team_id].status = "completed"
            self.team_statuses[result.team_id].completed_at = result.completed_at
        elif isinstance(result, Exception):
            # エラー処理（失格）
            pass

    # 最高スコアチーム特定
    best_team_id = None
    best_score = None

    if team_results:
        best_result = max(team_results, key=lambda r: r.evaluation_score)
        best_team_id = best_result.team_id
        best_score = best_result.evaluation_score

    # ExecutionSummary生成
    return ExecutionSummary(
        task_id=task.task_id,
        user_prompt=user_prompt,
        team_results=team_results,
        best_team_id=best_team_id,
        best_score=best_score,
        total_execution_time_seconds=execution_time,
    )

async def _run_team(
    self,
    controller: RoundController,
    user_prompt: str,
    timeout_seconds: int,
) -> RoundResult:
    """チーム単位の実行（タイムアウト付き）"""
    team_id = controller.get_team_id()

    # ステータス更新: running
    self.team_statuses[team_id].status = "running"
    self.team_statuses[team_id].started_at = datetime.now(UTC)

    try:
        result = await asyncio.wait_for(
            controller.run_round(user_prompt, timeout_seconds),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        self.team_statuses[team_id].status = "timeout"
        self.team_statuses[team_id].error_message = f"Timeout after {timeout_seconds}s"
        raise
    except Exception as e:
        self.team_statuses[team_id].status = "failed"
        self.team_statuses[team_id].error_message = str(e)
        raise
```

**Dependencies**: T015完了
**Verification**: `pytest tests/unit/orchestrator/test_orchestrator.py` がパス
**Checkpoint**: ✅ User Story 1 完成

---

## Phase 4: User Story 2 - ラウンド進行管理と終了判定 (P2)

**Note**: 初期実装では1ラウンドのみのため、このUser Storyは簡略化されます。将来的に複数ラウンド対応時に拡張します。

### T017: [US2] ラウンド終了条件判定の設計
**Story**: User Story 2
**File**: `docs/future-enhancements.md`
**Description**: 将来の複数ラウンド対応のための設計ドキュメントを作成

```markdown
# Future Enhancements: Multiple Round Support

## Overview
初期実装は1ラウンドのみだが、将来的に複数ラウンド対応を行う際の設計指針。

## RoundController拡張
- `should_continue_round()`: ラウンド継続判定
- `load_previous_round()`: 前ラウンド結果読み込み
- `update_round_state()`: ラウンド状態更新

## Orchestrator拡張
- ラウンド進行状況の監視
- ラウンド間のフィードバック統合

## 実装時の考慮事項
- FR-003: ラウンドコントローラへの委譲
- FR-004: 終了条件判定
```

**Dependencies**: T016完了
**Checkpoint**: ✅ User Story 2 設計完了（実装は将来）

---

## Phase 5: User Story 3 - 実行全体の完了集約と終了通知 (P3)

### T018: [US3] CLI exec コマンドのテスト作成
**Story**: User Story 3
**File**: `tests/integration/test_orchestrator_e2e.py`
**Description**: CLIコマンドのE2Eテストを作成

```python
import subprocess
import json
from pathlib import Path

def test_mixseek_exec_help():
    """mixseek exec --helpテスト"""
    result = subprocess.run(
        ["mixseek", "exec", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "USER_PROMPT" in result.stdout

def test_mixseek_exec_json_output(tmp_path):
    """mixseek exec JSON出力テスト"""
    # テスト用設定ファイル準備
    # ...

    result = subprocess.run(
        ["mixseek", "exec", "テストプロンプト", "--output", "json"],
        capture_output=True,
        text=True,
        env={"MIXSEEK_WORKSPACE": str(tmp_path)},
    )

    if result.returncode == 0:
        output = json.loads(result.stdout)
        assert "task_id" in output
        assert "user_prompt" in output
```

**Dependencies**: T016完了
**Expected**: テスト失敗（Red）

---

### T019: [US3] CLI exec コマンド実装
**Story**: User Story 3
**File**: `src/mixseek/cli/commands/exec.py`
**Description**: `mixseek exec`コマンドを実装

```python
"""mixseek exec コマンド実装"""

import asyncio
import json
import sys
from pathlib import Path

import typer

from mixseek.orchestrator import Orchestrator, load_orchestrator_config


def exec(
    user_prompt: str = typer.Argument(..., help="ユーザプロンプト"),
    config: Path = typer.Option(
        "workspace/configs/orchestrator.toml",
        "--config",
        help="オーケストレータ設定TOMLファイルパス",
    ),
    timeout: int | None = typer.Option(
        None,
        "--timeout",
        help="チーム単位タイムアウト（秒）",
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        help="ワークスペースパス（デフォルト: $MIXSEEK_WORKSPACE）",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        help="出力フォーマット（text/json）",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="詳細ログ表示",
    ),
) -> None:
    """ユーザプロンプトを複数チームで並列実行

    Note: exec コマンドではリーダーボード機能のため、常に DuckDB に保存されます。
    """

    async def _execute() -> None:
        try:
            # 設定読み込み
            orchestrator_config = load_orchestrator_config(config)

            # Orchestrator作成
            orchestrator = Orchestrator(
                config=orchestrator_config,
                workspace=workspace,
            )

            # 実行
            if output == "text":
                typer.echo("🚀 MixSeek Orchestrator")
                typer.echo("━" * 60)
                typer.echo(f"\n📝 Task: {user_prompt}\n")
                typer.echo(f"🔄 Running {len(orchestrator_config.teams)} teams in parallel...\n")

            summary = await orchestrator.execute(
                user_prompt=user_prompt,
                timeout_seconds=timeout,
            )

            # 出力
            if output == "json":
                print(summary.model_dump_json(indent=2))
            else:
                _print_text_summary(summary)

        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(_execute())


def _print_text_summary(summary) -> None:
    """テキスト形式でサマリーを表示"""
    # チーム結果表示
    for result in summary.team_results:
        typer.echo(f"✅ Team {result.team_id}: {result.team_name} (completed in {result.execution_time_seconds:.1f}s)")
        typer.echo(f"   Score: {result.evaluation_score:.2f}")
        typer.echo(f"   Feedback: {result.evaluation_feedback}\n")

    # 最高スコアチーム表示
    if summary.best_team_id:
        typer.echo("━" * 60)
        typer.echo(f"🏆 Best Result (Team {summary.best_team_id}, Score: {summary.best_score:.2f})")
        typer.echo("━" * 60)

        best_result = next(r for r in summary.team_results if r.team_id == summary.best_team_id)
        typer.echo(f"\n{best_result.submission_content}\n")

    # サマリー表示
    typer.echo("━" * 60)
    typer.echo("📊 Summary")
    typer.echo("━" * 60)
    typer.echo(f"\nTotal Teams:      {summary.total_teams}")
    typer.echo(f"Completed Teams:  {summary.completed_teams}")
    typer.echo(f"Failed Teams:     {summary.failed_teams}")
    typer.echo(f"Execution Time:   {summary.total_execution_time_seconds:.1f}s")
    typer.echo(f"\n💾 Results saved to DuckDB")
```

**Dependencies**: T018完了

---

### T020: [US3] CLI main.pyにexecコマンド登録
**Story**: User Story 3
**File**: `src/mixseek/cli/main.py`
**Description**: main.pyにexecコマンドを登録

```python
# 既存のインポート
from mixseek.cli.commands import evaluate as evaluate_module
from mixseek.cli.commands import init as init_module
from mixseek.cli.commands import member as member_module
from mixseek.cli.commands import team as team_module
from mixseek.cli.commands import validate_models as validate_models_module
from mixseek.cli.commands import exec as exec_module  # 追加

# 既存のコマンド登録
app.command(name="init")(init_module.init)
app.command(name="member")(member_module.member)
app.command(name="team")(team_module.team)
app.command(name="validate-models")(validate_models_module.validate_models)
app.command(name="evaluate")(evaluate_module.evaluate)
app.command(name="exec")(exec_module.exec)  # 追加
```

**Dependencies**: T019完了
**Verification**: `pytest tests/integration/test_orchestrator_e2e.py` がパス
**Checkpoint**: ✅ User Story 3 完成

---

## Phase 6: Polish & Cross-Cutting Concerns

### T021 [P]: 型チェック（mypy）
**File**: 全ファイル
**Description**: mypy strict modeで型チェックを実行し、エラーを修正

```bash
mypy src/mixseek/orchestrator/
```

**Dependencies**: T020完了

---

### T022 [P]: コードフォーマット（ruff）
**File**: 全ファイル
**Description**: ruffでコードフォーマットとリントを実行

```bash
ruff check --fix src/mixseek/orchestrator/
ruff format src/mixseek/orchestrator/
```

**Dependencies**: T020完了

---

### T023: 統合テストの実行
**File**: 全テスト
**Description**: 全テストを実行して品質を確認

```bash
pytest tests/unit/orchestrator/
pytest tests/integration/test_orchestrator_e2e.py
```

**Dependencies**: T021, T022完了
**Checkpoint**: ✅ 全テストパス

---

## Dependencies Graph

```
Phase 1: Setup
T001 → T002 → Phase 2

Phase 2: Foundational Models (blocking all user stories)
T003 [P]  ┐
T004 [P]  ├→ T008 → Phase 3
T005 [P]  ├→ (T006依存)
T006 [P]  │
T007 [P]  ┘

Phase 3: User Story 1 (P1)
T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016

Phase 4: User Story 2 (P2) - Simplified
T016 → T017

Phase 5: User Story 3 (P3)
T016 → T018 → T019 → T020

Phase 6: Polish
T020 → T021 [P]
T020 → T022 [P]
T021, T022 → T023
```

## Parallel Execution Opportunities

### Phase 2: Foundational Models
- **T003-T007**: 5つのモデルテストを並列作成可能

### Phase 6: Polish
- **T021, T022**: 型チェックとフォーマットを並列実行可能

## Implementation Strategy

1. **MVP Scope**: User Story 1のみ（T001-T016）
   - 基本的なオーケストレータ機能
   - 1ラウンドの実行
   - DuckDB記録

2. **Full v1.0 Scope**: User Story 1-3（T001-T023）
   - CLIコマンド実装
   - 完了通知と結果表示
   - 全品質チェック

3. **Future**: User Story 2の完全実装（複数ラウンド対応）

## Task Summary

- **Total Tasks**: 23
- **User Story 1 (P1)**: 12 tasks (T003-T016)
- **User Story 2 (P2)**: 1 task (T017 - design only)
- **User Story 3 (P3)**: 3 tasks (T018-T020)
- **Setup**: 2 tasks (T001-T002)
- **Foundational**: 6 tasks (T003-T008)
- **Polish**: 3 tasks (T021-T023)
- **Parallel Opportunities**: 7 tasks (5 in Phase 2, 2 in Phase 6)

## Suggested MVP

**T001-T016** (16 tasks) で基本的なオーケストレータ機能が動作します:
- ユーザプロンプト受信
- 複数チーム並列実行
- DuckDB記録
- 結果集約

CLIコマンドを含む完全版は **T001-T023** (23 tasks) です。
