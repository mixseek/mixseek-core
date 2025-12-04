# Data Model: Round Configuration in TOML

**Feature**: 101-round-config
**Date**: 2025-11-18
**Status**: Design

## Overview

本ドキュメントは、OrchestratorSettingsモデルへのラウンド設定フィールド追加の詳細設計を定義する。Pydantic v2を使用した型安全な設定スキーマとバリデーション制約を記述する。

## Entity: OrchestratorSettings (Extended)

### Location

`src/mixseek/config/schema.py:523-580`

### Pydantic Model Definition

```python
from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict

class OrchestratorSettings(WorkspaceValidatorMixin, MixSeekBaseSettings):
    """Orchestrator用の設定スキーマ。

    オーケストレーション全体の設定を管理します。
    すべての環境（dev/staging/prod）でデフォルト値は同一です（FR-007準拠）。

    Note:
        WorkspaceValidatorMixinによりworkspace_pathのバリデーションを継承
        （Article 10: DRY原則準拠）
    """

    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # === 既存フィールド（変更なし） ===
    workspace_path: Path = Field(...)
    timeout_per_team_seconds: int = Field(default=300, ge=10, le=3600, ...)
    max_concurrent_teams: int = Field(default=4, ge=1, le=100, ...)
    max_retries_per_team: int = Field(default=2, ge=0, le=10, ...)
    teams: list[dict[str, str]] = Field(default_factory=list, ...)

    # === 新規追加: ラウンド設定フィールド（Feature 101-round-config） ===
    max_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of rounds per team (matches OrchestratorTask default)",
    )

    min_rounds: int = Field(
        default=2,
        ge=1,
        description="Minimum number of rounds before LLM-based judgment (matches OrchestratorTask default)",
    )

    submission_timeout_seconds: int = Field(
        default=300,
        gt=0,
        description="Timeout for team submission in each round (seconds, matches OrchestratorTask default)",
    )

    judgment_timeout_seconds: int = Field(
        default=60,
        gt=0,
        description="Timeout for evaluation judgment in each round (seconds, matches OrchestratorTask default)",
    )

    # === Cross-field validation ===
    @model_validator(mode='after')
    def validate_round_configuration(self) -> 'OrchestratorSettings':
        """Validate min_rounds <= max_rounds constraint.

        Raises:
            ValueError: If min_rounds exceeds max_rounds

        Note:
            This validation is also implemented in OrchestratorTask for defensive programming.
            (Clarifications Session 2025-11-18: 二重検証による早期エラー検出)
        """
        if self.min_rounds > self.max_rounds:
            raise ValueError(
                f"min_rounds ({self.min_rounds}) must be <= max_rounds ({self.max_rounds})"
            )
        return self
```

### Field Definitions

#### max_rounds

**Type**: `int`
**Default**: `5`
**Constraints**:
- `ge=1` (greater than or equal to 1)
- `le=10` (less than or equal to 10)

**Purpose**: チームがタスクに取り組む最大ラウンド数を定義する。この制限に達した場合、システムはその時点での最高スコアSubmissionを返す。

**Validation Rules**:
- 値は1から10の範囲内でなければならない
- min_rounds以上でなければならない（cross-field validation）

**Source**: OrchestratorTask（Feature 012-round-controller）のデフォルト値と一致

#### min_rounds

**Type**: `int`
**Default**: `2`
**Constraints**:
- `ge=1` (greater than or equal to 1)

**Purpose**: LLMベースの終了判定が実行される前に、チームが最低限実行しなければならないラウンド数を定義する。これにより、早すぎる終了を防ぐ。

**Validation Rules**:
- 値は1以上でなければならない
- max_rounds以下でなければならない（cross-field validation）

**Source**: OrchestratorTask（Feature 012-round-controller）のデフォルト値と一致

#### submission_timeout_seconds

**Type**: `int`
**Default**: `300` (5分)
**Constraints**:
- `gt=0` (greater than 0)

**Purpose**: 各ラウンドでチームがSubmissionを生成するための最大時間を定義する。この時間を超えた場合、そのラウンドはタイムアウトエラーで終了する。

**Validation Rules**:
- 値は正の整数でなければならない

**Independent**: timeout_per_team_seconds（オーケストレータレベル）とは独立したタイムアウト（Clarifications Session 2025-11-18）

**Source**: OrchestratorTask（Feature 012-round-controller）のデフォルト値と一致

#### judgment_timeout_seconds

**Type**: `int`
**Default**: `60` (1分)
**Constraints**:
- `gt=0` (greater than 0)

**Purpose**: 各ラウンドでEvaluatorがSubmissionを評価するための最大時間を定義する。この時間を超えた場合、システムはフォールバック動作を実行する。

**Validation Rules**:
- 値は正の整数でなければならない

**Independent**: timeout_per_team_seconds（オーケストレータレベル）とは独立したタイムアウト（Clarifications Session 2025-11-18）

**Source**: OrchestratorTask（Feature 012-round-controller）のデフォルト値と一致

### Cross-Field Validation

#### min_rounds <= max_rounds

**Implementation**: `@model_validator(mode='after')`

**Rationale**:
- `mode='after'`を使用することで、すべてのフィールドが初期化された後に検証を実行
- `mode='before'`と異なり、型変換済みの値を扱うため実装が簡潔

**Error Message Format**:
```python
f"min_rounds ({self.min_rounds}) must be <= max_rounds ({self.max_rounds})"
```

**Design Note**:
この検証はOrchestratorTaskでも実装されており、二重検証アプローチを採用している（Clarifications Session 2025-11-18）：
- OrchestratorSettings: 設定読み込み時の早期エラー検出
- OrchestratorTask: 防御的プログラミング

## Environment Variable Mapping

### Auto-Generated Names

Pydantic Settings `env_prefix="MIXSEEK_"`により、以下の環境変数名が自動生成される：

| Field Name | Environment Variable | TOML Key |
|------------|---------------------|----------|
| `max_rounds` | `MIXSEEK_MAX_ROUNDS` | `max_rounds` |
| `min_rounds` | `MIXSEEK_MIN_ROUNDS` | `min_rounds` |
| `submission_timeout_seconds` | `MIXSEEK_SUBMISSION_TIMEOUT_SECONDS` | `submission_timeout_seconds` |
| `judgment_timeout_seconds` | `MIXSEEK_JUDGMENT_TIMEOUT_SECONDS` | `judgment_timeout_seconds` |

### Configuration Precedence

Pydantic Settingsの標準的な優先順位：

1. **Environment Variables** (最優先)
   - 例: `MIXSEEK_MAX_ROUNDS=7`
   - 用途: 環境固有の調整（dev/staging/prod）

2. **TOML File** (中優先)
   - ファイル: `orchestrator.toml`
   - 例: `max_rounds = 10`
   - 用途: プロジェクト標準設定

3. **Default Values** (最低優先度)
   - Pydantic Field定義の`default`パラメータ
   - 用途: システムデフォルト値

### Example Configurations

#### TOML Configuration

```toml
# orchestrator.toml

# === Round Configuration (Feature 101-round-config) ===
max_rounds = 10
min_rounds = 3
submission_timeout_seconds = 600  # 10 minutes
judgment_timeout_seconds = 120    # 2 minutes

# === Existing Configuration ===
workspace = "/path/to/workspace"
timeout_per_team_seconds = 300
max_concurrent_teams = 4

[[teams]]
config = "path/to/team1.toml"

[[teams]]
config = "path/to/team2.toml"
```

#### Environment Variable Override

```bash
# Override max_rounds for development environment
export MIXSEEK_MAX_ROUNDS=7

# Override timeouts for quick testing
export MIXSEEK_SUBMISSION_TIMEOUT_SECONDS=60
export MIXSEEK_JUDGMENT_TIMEOUT_SECONDS=30

# Run orchestrator (env vars take precedence over TOML)
mixseek exec "Analyze data trends"
```

#### Python Code Usage

```python
from mixseek.config.manager import ConfigurationManager

# Load configuration with precedence: ENV > TOML > Defaults
config_manager = ConfigurationManager(workspace_path=Path("/workspace"))
orchestrator_settings = config_manager.get_orchestrator_settings()

# Access round configuration
print(f"Max rounds: {orchestrator_settings.max_rounds}")
print(f"Min rounds: {orchestrator_settings.min_rounds}")
print(f"Submission timeout: {orchestrator_settings.submission_timeout_seconds}s")
print(f"Judgment timeout: {orchestrator_settings.judgment_timeout_seconds}s")
```

## Validation Error Examples

### Example 1: max_rounds out of range

**Input**:
```toml
max_rounds = 0
```

**Error**:
```
ValidationError: 1 validation error for OrchestratorSettings
max_rounds
  Input should be greater than or equal to 1 [type=greater_than_equal, input_value=0, input_type=int]
```

### Example 2: min_rounds > max_rounds

**Input**:
```toml
max_rounds = 3
min_rounds = 5
```

**Error**:
```
ValidationError: 1 validation error for OrchestratorSettings
  Value error, min_rounds (5) must be <= max_rounds (3) [type=value_error, input_value={'workspace_path': '/...', ...}, input_type=dict]
```

### Example 3: Negative timeout

**Input**:
```toml
submission_timeout_seconds = -100
```

**Error**:
```
ValidationError: 1 validation error for OrchestratorSettings
submission_timeout_seconds
  Input should be greater than 0 [type=greater_than, input_value=-100, input_type=int]
```

## Integration with OrchestratorTask

### Data Flow

```
ConfigurationManager
  ↓ (reads TOML + ENV)
OrchestratorSettings
  ↓ (validated fields)
Orchestrator.execute()
  ↓ (passes config values)
OrchestratorTask
  ↓ (re-validates for defensive programming)
RoundController
  ↓ (uses round configuration)
Round Execution
```

### Code Integration Point

**File**: `src/mixseek/orchestrator/orchestrator.py`

**Before** (current):
```python
task = OrchestratorTask(
    execution_id=execution_id,
    user_prompt=user_prompt,
    team_configs=[ref.config for ref in self.config.teams],
    timeout_seconds=timeout,
    # Uses OrchestratorTask defaults
)
```

**After** (101-round-config):
```python
task = OrchestratorTask(
    execution_id=execution_id,
    user_prompt=user_prompt,
    team_configs=[ref.config for ref in self.config.teams],
    timeout_seconds=timeout,
    # Pass round configuration from OrchestratorSettings
    max_rounds=self.config.max_rounds,
    min_rounds=self.config.min_rounds,
    submission_timeout_seconds=self.config.submission_timeout_seconds,
    judgment_timeout_seconds=self.config.judgment_timeout_seconds,
)
```

## Backwards Compatibility

### Existing TOML Files

**Compatibility**: ✅ **Full backwards compatibility guaranteed**

**Reason**:
- すべてのラウンド設定フィールドはオプション（デフォルト値あり）
- 既存のorchestrator.tomlファイルにラウンド設定が含まれていなくても正常に動作
- デフォルト値はOrchestratorTaskの既存値と一致

**Example**:
```toml
# Existing orchestrator.toml (no round config)
workspace = "/workspace"
timeout_per_team_seconds = 300

[[teams]]
config = "team1.toml"

# ↓ This file will continue to work with defaults:
# max_rounds = 5 (default)
# min_rounds = 2 (default)
# submission_timeout_seconds = 300 (default)
# judgment_timeout_seconds = 60 (default)
```

### Pydantic Settings Behavior

**`extra="forbid"`**:
- 未知のフィールドがTOMLに含まれている場合、エラーを発生させる
- これにより、タイプミス（例: `max_round`）を早期に検出できる

**`validate_default=True`**:
- デフォルト値も制約に準拠することを保証
- システムの一貫性を維持

## Testing Strategy

### Unit Tests

**File**: `tests/config/test_orchestrator_settings.py`

**Test Cases**:
1. **Valid configurations**: デフォルト値、TOML値、環境変数値
2. **Field constraints**: max_rounds範囲外、負のタイムアウト
3. **Cross-field validation**: min_rounds > max_rounds
4. **Environment variable precedence**: ENV > TOML > Default
5. **Backwards compatibility**: ラウンド設定なしのTOMLファイル

### Integration Tests

**File**: `tests/orchestrator/test_orchestrator.py`

**Test Cases**:
1. **Configuration pass-through**: OrchestratorSettings → OrchestratorTask
2. **Round execution**: 設定されたmax_roundsまで実行される
3. **Timeout enforcement**: submission_timeout_secondsが適用される

## References

- [research.md](./research.md): 技術調査結果
- [spec.md](./spec.md): 機能要件（FR-001～FR-010）
- Feature 012-round-controller: OrchestratorTask実装
- Feature 051-configuration: ConfigurationManager実装
- Pydantic v2 Documentation: Field validators and model validators

## Next Steps

1. ✅ data-model.md完了
2. ⏭ quickstart.mdを生成（TOML設定例とトラブルシューティング）
3. ⏭ agent contextを更新
