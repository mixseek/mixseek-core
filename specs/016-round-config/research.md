# Research: Round Configuration in TOML

**Feature**: 101-round-config
**Date**: 2025-11-18
**Status**: Completed

## Overview

本ドキュメントは、OrchestratorTaskのラウンド設定フィールド（max_rounds、min_rounds、submission_timeout_seconds、judgment_timeout_seconds）をTOML経由で設定可能にするための技術調査結果をまとめる。

## Research Tasks

### 1. Pydantic Settings Field Validation Patterns

**調査対象**: `src/mixseek/config/schema.py:523-580` - OrchestratorSettings実装

**発見事項**:

```python
class OrchestratorSettings(WorkspaceValidatorMixin, MixSeekBaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",  # 未定義フィールドを拒否
        validate_default=True,  # デフォルト値もバリデーション
    )

    timeout_per_team_seconds: int = Field(
        default=300,
        ge=10,  # Greater than or equal
        le=3600,  # Less than or equal
        description="チームごとのタイムアウト（秒）",
    )
```

**ベストプラクティス**:
- `Field()`で`default`、`ge`（>=）、`le`（<=）、`gt`（>）制約を定義
- `extra="forbid"`で未知のフィールドを拒否し、設定ミスを防ぐ
- `validate_default=True`でデフォルト値も制約に準拠することを保証
- `description`で各フィールドの用途を明確に文書化

### 2. Environment Variable Naming Convention

**調査対象**: Pydantic Settings v2のenv_prefix機能

**発見事項**:
- `env_prefix="MIXSEEK_"`により、環境変数名が自動生成される
- フィールド名は大文字に変換される
- 例:
  - `max_rounds` → `MIXSEEK_MAX_ROUNDS`
  - `min_rounds` → `MIXSEEK_MIN_ROUNDS`
  - `submission_timeout_seconds` → `MIXSEEK_SUBMISSION_TIMEOUT_SECONDS`
  - `judgment_timeout_seconds` → `MIXSEEK_JUDGMENT_TIMEOUT_SECONDS`

**命名規則**:
- 環境変数: `MIXSEEK_<FIELD_NAME_UPPER>`
- TOMLファイル: `<field_name_lower>` （そのまま）

**優先順位** (Pydantic Settings標準):
1. 環境変数（最優先）
2. TOMLファイル
3. デフォルト値（最低優先度）

### 3. Cross-Field Validation Best Practices

**調査対象**: `src/mixseek/orchestrator/models.py:43-50` - OrchestratorTaskのmin_rounds検証

**発見事項**:

```python
@field_validator("min_rounds")
@classmethod
def validate_min_rounds(cls, v: int, info: Any) -> int:
    """Validate min_rounds <= max_rounds"""
    max_rounds = info.data.get("max_rounds")
    if max_rounds is not None and v > max_rounds:
        raise ValueError(f"min_rounds ({v}) must be <= max_rounds ({max_rounds})")
    return v
```

**Pydantic v2パターン**:
- `@field_validator`デコレータで個別フィールドを検証
- `info.data.get()`で他のフィールド値にアクセス
- 検証失敗時は`ValueError`を raise
- エラーメッセージに具体的な値を含めてデバッグを容易にする

**代替アプローチ** (model_validator):
```python
from pydantic import model_validator

@model_validator(mode='after')
def validate_rounds(self) -> 'OrchestratorSettings':
    if self.min_rounds > self.max_rounds:
        raise ValueError(f"min_rounds ({self.min_rounds}) must be <= max_rounds ({self.max_rounds})")
    return self
```

`@model_validator(mode='after')`はすべてのフィールドが初期化された後に実行されるため、複数フィールド間の複雑な検証に適している。

### 4. Orchestrator Configuration Pass-Through Pattern

**調査対象**: `src/mixseek/orchestrator/orchestrator.py:128-139` - OrchestratorTask生成

**現在の実装**:

```python
task = OrchestratorTask(
    execution_id=execution_id,
    user_prompt=user_prompt,
    team_configs=[ref.config for ref in self.config.teams],
    timeout_seconds=timeout,  # self.config.timeout_per_team_secondsから取得
)
```

**必要な変更**:

```python
task = OrchestratorTask(
    execution_id=execution_id,
    user_prompt=user_prompt,
    team_configs=[ref.config for ref in self.config.teams],
    timeout_seconds=timeout,
    # 追加: ラウンド設定フィールドの受け渡し
    max_rounds=self.config.max_rounds,
    min_rounds=self.config.min_rounds,
    submission_timeout_seconds=self.config.submission_timeout_seconds,
    judgment_timeout_seconds=self.config.judgment_timeout_seconds,
)
```

**パターン**:
- OrchestratorSettings（設定スキーマ）からOrchestratorTask（ランタイムタスク）へ明示的に値を渡す
- ConfigurationManagerが設定読み込みを処理し、Orchestratorは単に値を転送する
- OrchestratorTaskのデフォルト値はOrchestratorSettingsで上書きされる

## Decisions

### Decision 1: Validation Strategy

**Question**: OrchestratorSettingsとOrchestratorTaskの両方でバリデーションを実装するか？

**Decision**: **両方で実装（二重検証）**

**Rationale**:
- **OrchestratorSettings**: 設定読み込み時の早期エラー検出（Article 9: Data Accuracy準拠）
- **OrchestratorTask**: 防御的プログラミング（既存実装を維持）
- Clarification Session 2025-11-18で明確化された要件に準拠

**Implementation**:
- OrchestratorSettings: Pydantic Field制約 + @model_validator
- OrchestratorTask: 既存の@field_validator実装を保持

### Decision 2: Default Value Source of Truth

**Question**: デフォルト値の単一情報源はどこか？

**Decision**: **OrchestratorTaskをSource of Truthとし、OrchestratorSettingsで同じ値を使用**

**Rationale**:
- OrchestratorTaskは012-round-controllerで既にデフォルト値を定義している
- OrchestratorSettingsは設定インターフェースとしてこれらの値を継承する
- Article 10 (DRY)に従い、デフォルト値の重複を避ける

**Implementation**:
```python
# OrchestratorTask (Source of Truth)
max_rounds: int = Field(default=5, ge=1, le=10, ...)

# OrchestratorSettings (継承)
max_rounds: int = Field(default=5, ge=1, le=10, ...)
```

**Note**: 現時点では値を重複定義するが、将来的には共有定数として抽出することを検討する（DRY原則の完全な適用）。

### Decision 3: Error Message Format

**Question**: バリデーションエラーメッセージの形式は？

**Decision**: **具体的な値を含む明確な日本語メッセージ**

**Rationale**:
- Article 9 (Data Accuracy)に従い、明示的なエラー伝達
- ユーザー体験を向上させるため、デバッグに必要な情報を提供

**Examples**:
```python
# Good:
f"min_rounds ({v}) must be <= max_rounds ({max_rounds})"

# Bad:
"Invalid min_rounds value"
```

### Decision 4: Timeout Relationship Validation

**Question**: timeout_per_team_secondsとラウンドタイムアウトの相互検証は必要か？

**Decision**: **相互検証は不要**

**Rationale**:
- Clarification Session 2025-11-18で確認済み
- timeout_per_team_seconds（オーケストレータレベル）とsubmission_timeout_seconds/judgment_timeout_seconds（ラウンドレベル）は異なるレイヤーで独立に適用される
- システムの柔軟性を保つため、厳密な制約を課さない

## Implementation Notes

### Files to Modify

1. **src/mixseek/config/schema.py**:
   - OrchestratorSettingsクラスにラウンド設定フィールドを追加
   - @model_validatorでmin_rounds <= max_roundsを検証

2. **src/mixseek/orchestrator/orchestrator.py**:
   - execute()メソッドでOrchestratorTask生成時にラウンド設定を渡す

### Files to Reference (No Changes)

1. **src/mixseek/orchestrator/models.py**:
   - OrchestratorTaskの既存ラウンド設定フィールド定義を参照
   - 既存のバリデーションロジックを保持

2. **src/mixseek/round_controller/controller.py**:
   - RoundControllerがOrchestratorTaskのラウンド設定を既に使用していることを確認
   - 変更不要

### Backwards Compatibility

**TOML Files**:
- 新しいフィールドはオプション（デフォルト値あり）
- 既存のorchestrator.tomlファイルはそのまま動作する
- 後方互換性: ✅ 保証

**Environment Variables**:
- MIXSEEK_MAX_ROUNDS等の環境変数は新規追加
- 既存の環境変数設定に影響なし
- 後方互換性: ✅ 保証

## Alternatives Considered

### Alternative 1: OrchestratorSettingsのみでバリデーション

**Rejected Reason**:
- OrchestratorTaskの既存バリデーションを削除すると、防御的プログラミングが失われる
- 仕様のClarifications（Session 2025-11-18）で二重検証が明示的に推奨されている

### Alternative 2: 共有定数ファイルでデフォルト値を管理

**Deferred Reason**:
- DRY原則の完全な適用には有効だが、本機能のスコープを超える
- 将来のリファクタリングタスクとして検討

### Alternative 3: @model_validator(mode='before')

**Rejected Reason**:
- `mode='before'`は生の入力データで動作するため、型変換前の値を扱う必要がある
- `mode='after'`の方がすべてのフィールドが初期化済みで扱いやすい

## References

- Feature 012-round-controller: OrchestratorTaskのラウンド設定定義
- Feature 051-configuration: ConfigurationManagerインフラストラクチャ
- Pydantic v2 Documentation: Field validators and model validators
- Constitution Article 9: Data Accuracy Mandate
- Constitution Article 10: DRY Principle
- Spec Clarifications (Session 2025-11-18)

## Next Steps

1. ✅ research.md完了
2. ⏭ data-model.mdを生成（OrchestratorSettings拡張の詳細設計）
3. ⏭ quickstart.mdを生成（TOML設定例とトラブルシューティング）
4. ⏭ agent contextを更新
