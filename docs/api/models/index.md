# Models API

MixSeek-Coreのデータモデルに関するAPIリファレンスです。

## 概要

MixSeek-Coreは型安全性を重視し、すべてのデータ構造をPydantic Modelで定義しています。これにより、ランタイム検証と自動ドキュメント生成が可能になります。

## 実装済みモデル

```{toctree}
:maxdepth: 2

member-agent
```

### Member Agent関連

Member Agentに関連するモデルは現在実装されています。

#### 主要モデル

**設定モデル**:
- **MemberAgentConfig** - エージェント設定（TOML読み込み）
- **AgentInstructions** - エージェント指示

**実行結果モデル**:
- **MemberAgentResult** - エージェント実行結果
- **ResultStatus** - 結果ステータス列挙型

**ツール設定モデル**:
- **ToolSettings** - ツール設定
- **WebSearchToolConfig** - Web検索ツール設定
- **CodeExecutionToolConfig** - コード実行ツール設定

**列挙型**:
- **AgentType** - エージェントタイプ（PLAIN/WEB_SEARCH/CODE_EXECUTION）

詳細は [Member Agent モデル詳細](member-agent.md) を参照してください。

#### 簡易使用例

```python
from mixseek.models.member_agent import (
    MemberAgentConfig,
    AgentType,
    AgentInstructions,
    MemberAgentResult
)

# 設定の作成
config = MemberAgentConfig(
    name="my-agent",
    type=AgentType.PLAIN,
    model="google-gla:gemini-2.5-flash",
    temperature=0.2,
    max_tokens=2048,
    instructions=AgentInstructions(text="You are a helpful assistant.")
)

# 実行結果の作成
result = MemberAgentResult.success(
    content="Response",
    agent_name="my-agent",
    agent_type="plain"
)

# 結果の判定
if result.is_success():
    print(result.content)
```

## 計画中のモデル

以下のモデルは将来実装予定です。

### Submission（実装予定）

チームが生成する最終出力を表すモデルです。

#### フィールド

必須フィールド：
- `content: str` - Submissionの主要コンテンツ

デフォルト値を持つフィールド：
- `format: str` - 出力形式（markdown/json/csv/html、デフォルト: markdown）
- `metadata: dict[str, Any]` - 追加メタデータ（デフォルト: 空dict）

自動生成フィールド：
- `generated_at: datetime` - 生成日時（システムが自動設定）
- `team_id: str` - チームID（Round Controllerが設定）
- `team_name: str` - チーム名（Round Controllerが設定）
- `round_number: int` - ラウンド番号（Round Controllerが設定）

#### 計画されているインターフェース

```python
class Submission(BaseModel):
    """チームが生成する最終出力"""

    # 必須フィールド
    content: str = Field(..., description="主要コンテンツ")

    # デフォルト値を持つフィールド
    format: Literal["markdown", "json", "csv", "html"] = Field(
        default="markdown",
        description="出力形式"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="追加メタデータ"
    )

    # 自動生成フィールド
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="生成日時"
    )
    team_id: str = Field(..., description="チームID")
    team_name: str = Field(..., description="チーム名")
    round_number: int = Field(..., description="ラウンド番号")

    @classmethod
    def create(
        cls,
        content: str,
        team_id: str,
        team_name: str,
        round_number: int,
        format: str = "markdown",
        metadata: dict[str, Any] | None = None
    ) -> "Submission":
        """Submissionを作成"""
        pass
```

#### バリデーション

- Pydanticが自動的に型チェックとバリデーションを実行
- Leader Agentが生成に失敗した場合、Pydantic AI ReflectionがValidationErrorをフィードバック
- 最大リトライ回数は設定可能

### EvaluationResult（実装予定）

Evaluatorの出力を定義するモデルです。

#### フィールド

- `score: float` - 定量的スコア（0.0-1.0）
- `feedback: str` - 定性的フィードバックコメント
- `criteria_scores: dict[str, float]` - 基準ごとのスコア
- `evaluator_type: str` - 評価器タイプ（llm/custom）
- `metadata: dict[str, Any]` - 追加メタデータ
- `timestamp: datetime` - 評価日時

#### 計画されているインターフェース

```python
class EvaluationResult(BaseModel):
    """Evaluatorの評価結果"""

    score: float = Field(..., ge=0.0, le=1.0, description="総合スコア")
    feedback: str = Field(..., min_length=10, description="フィードバック")
    criteria_scores: dict[str, float] = Field(
        default_factory=dict,
        description="基準ごとのスコア"
    )
    evaluator_type: Literal["llm", "custom"] = Field(
        ...,
        description="評価器タイプ"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="追加メタデータ"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="評価日時"
    )

    @classmethod
    def from_evaluator(
        cls,
        score: float,
        feedback: str,
        evaluator_type: str,
        criteria_scores: dict[str, float] | None = None
    ) -> "EvaluationResult":
        """評価結果を作成"""
        pass
```

### RoundState（実装予定）

各ラウンドの完全な状態を保持するデータクラスです。

#### フィールド

- `round_number: int` - ラウンド番号
- `submission: Submission` - 生成されたSubmission
- `evaluation_score: float` - 評価スコア
- `evaluation_feedback: str` - 評価フィードバック
- `message_history: list[dict[str, Any]]` - Message History
- `timestamp: datetime` - ラウンド完了日時
- `execution_time_ms: int` - 実行時間（ミリ秒）

#### 計画されているインターフェース

```python
@dataclass
class RoundState:
    """ラウンド状態"""

    round_number: int
    submission: Submission
    evaluation_score: float
    evaluation_feedback: str
    message_history: list[dict[str, Any]]
    timestamp: datetime
    execution_time_ms: int

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換（データベース保存用）"""
        pass

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoundState":
        """辞書から復元"""
        pass

    def to_json(self) -> str:
        """JSON文字列に変換"""
        pass
```

#### 永続化

- SQLiteまたはPostgreSQLに保存
- JSON形式でシリアライズ
- 完了ラウンドはアーカイブテーブルに保存

### TeamConfig（実装予定）

チーム設定を定義するモデルです。

#### フィールド

チーム全体設定：
- `name: str` - チーム名
- `description: str` - チーム説明
- `max_rounds: int` - 最大ラウンド数
- `member_agent_limit: int` - Member Agent数上限

Leader Agent設定：
- `leader_model: str` - Leader Agentのモデル
- `leader_instructions: str` - Leader Agentへの指示

Member Agent設定：
- `members: list[MemberAgentConfig]` - Member Agentリスト

Evaluator設定：
- `evaluators: list[EvaluatorConfig]` - Evaluatorリスト

#### 計画されているインターフェース

```python
class TeamConfig(BaseModel):
    """チーム設定"""

    # チーム全体設定
    name: str = Field(..., description="チーム名")
    description: str = Field(..., description="チーム説明")
    max_rounds: int = Field(default=10, ge=1, le=100, description="最大ラウンド数")
    member_agent_limit: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Member Agent数上限"
    )

    # Leader Agent設定
    leader_model: str = Field(..., description="Leader Agentモデル")
    leader_instructions: str = Field(..., description="Leader Agent指示")

    # Member Agent設定
    members: list[MemberAgentConfig] = Field(
        ...,
        min_items=1,
        description="Member Agentリスト"
    )

    # Evaluator設定
    evaluators: list[EvaluatorConfig] = Field(
        ...,
        min_items=1,
        description="Evaluatorリスト"
    )

    @field_validator("members")
    @classmethod
    def validate_member_limit(
        cls,
        v: list[MemberAgentConfig],
        info: ValidationInfo
    ) -> list[MemberAgentConfig]:
        """Member Agent数上限を検証"""
        if len(v) > info.data["member_agent_limit"]:
            raise ValueError(
                f"Member Agent数が上限を超えています: "
                f"{len(v)} > {info.data['member_agent_limit']}"
            )
        return v
```

#### TOML設定例

```toml
[team]
name = "analysis-team"
description = "Data analysis team"
max_rounds = 10
member_agent_limit = 15

[team.leader]
model = "google-gla:gemini-2.5-flash"
instructions = "Coordinate analysis tasks with member agents"

[[team.members]]
name = "data-analyst"
type = "code_execution"
model = "anthropic:claude-sonnet-4-5-20250929"

[[team.members]]
name = "researcher"
type = "web_search"
model = "google-gla:gemini-2.5-flash"

[[team.evaluators]]
type = "llm"
model = "google-gla:gemini-2.5-flash"
criteria = ["accuracy", "completeness"]
```

## モデル検証

すべてのPydantic Modelは以下の機能を提供します：

### 自動検証

```python
from pydantic import ValidationError

try:
    config = MemberAgentConfig(**data)
except ValidationError as e:
    print(e.errors())
```

### スキーマ生成

```python
schema = MemberAgentConfig.model_json_schema()
```

### JSONシリアライズ

```python
# オブジェクト → JSON
json_str = config.model_dump_json()

# JSON → オブジェクト
config = MemberAgentConfig.model_validate_json(json_str)
```

## 型安全性

MixSeek-Coreは厳格な型安全性を実現しています：

- すべてのモデルフィールドに型注釈
- mypyによる静的型チェック
- Pydanticによるランタイム検証
- 包括的なバリデーションルール

## 関連リソース

- [Member Agent API](../agents/member-agents.md) - Member Agentモデルの詳細
- [Framework API](../framework/index.md) - Frameworkモデルの詳細
- [API概要](../index.md) - MixSeek-Core API全体
- [開発者ガイド](../../developer-guide.md) - 型安全性のベストプラクティス
