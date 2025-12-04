# Framework API

MixSeek-Coreフレームワークのコアコンポーネントに関するAPIリファレンスです。

## 概要

MixSeek-CoreフレームワークはTUMIXアルゴリズムに基づき、以下のコアコンポーネントで構成されます：

- **Orchestrator** (実装済み): 複数チームの並列実行管理
- **Round Controller** (実装済み): ラウンドライフサイクルと評価の管理
- **Evaluator** (実装済み): Submission評価とフィードバック生成
- **Verificator** (実装予定): Member Agent設定の検証

詳細なAPIリファレンスは [Orchestrator API](../orchestrator/index.md) を参照してください。

## Round Controller（実装済み）

Round Controllerは、単一チームのラウンドベース処理を管理します。

### 主要な機能

- Leader Agentの初期化と実行
- Message History管理
- Member Agent応答の集約
- Evaluatorによる評価実行
- DuckDBへのラウンド履歴保存
- リーダーボードへの結果記録

### API概要

詳細なAPIリファレンスは [RoundController API](../orchestrator/index.md#roundcontroller-api) を参照してください。

```python
class RoundController:
    """単一チームのラウンドライフサイクル管理"""

    def __init__(
        self,
        team_config_path: Path,
        workspace: Path,
        round_number: int = 1
    ):
        """Round Controller初期化

        Args:
            team_config_path: チーム設定TOMLファイルパス
            workspace: ワークスペースパス
            round_number: ラウンド番号（初期実装では常に1）
        """

    async def run_round(
        self,
        user_prompt: str,
        timeout_seconds: int,
        execution_id: str
    ) -> RoundResult:
        """1ラウンドを実行してRoundResultを返す

        Args:
            user_prompt: ユーザプロンプト
            timeout_seconds: タイムアウト（秒）
            execution_id: オーケストレーション実行識別子（UUID）
        """
```

### RoundResult

ラウンド実行結果を表すPydantic Model：

```python
class RoundResult(BaseModel):
    execution_id: str  # オーケストレーション実行識別子（UUID）
    team_id: str
    team_name: str
    round_number: int
    submission_content: str
    evaluation_score: float  # 0.0-1.0
    evaluation_feedback: str
    usage: RunUsage
    execution_time_seconds: float
    completed_at: datetime
```

詳細は [Data Models](../orchestrator/data-models.md#roundresult) を参照してください。

### DuckDB永続化

- ラウンド履歴: `round_history`テーブル
- リーダーボード: `leader_board`テーブル
- JSON型カラムでMessage HistoryとMember Agent応答を保存
- MVCC並列制御による同時書き込み対応

詳細は [データベーススキーマ](../../database-schema.md) を参照してください。

## Orchestrator（実装済み）

Orchestratorは複数チームの並列実行と結果集約を担当します。

### 主要な機能

- 複数チーム設定の読み込み（OrchestratorSettings）
- asyncio.gather()による並列実行
- チーム単位のタイムアウト管理
- 失敗チームの隔離と処理
- 最高スコアチームの自動選択
- リーダーボード生成

### API概要

詳細なAPIリファレンスは [Orchestrator API](../orchestrator/index.md#orchestrator-api) を参照してください。

```python
class Orchestrator:
    """複数チームの並列実行管理"""

    def __init__(
        self,
        settings: OrchestratorSettings,
        save_db: bool = True
    ):
        """Orchestrator初期化

        Args:
            settings: オーケストレータ設定
            save_db: DuckDBへの保存フラグ
        """

    async def execute(
        self,
        user_prompt: str,
        timeout_seconds: int | None = None
    ) -> ExecutionSummary:
        """ユーザプロンプトを複数チームで並列実行

        Args:
            user_prompt: ユーザプロンプト
            timeout_seconds: チーム単位タイムアウト（秒、Noneの場合は設定値使用）

        Returns:
            ExecutionSummary: 全チームの実行結果とランキング
        """
```

### ExecutionSummary

全チーム実行結果とランキングを表すPydantic Model：

```python
class ExecutionSummary(BaseModel):
    execution_id: str  # 実行識別子（UUID）
    user_prompt: str
    team_results: list[RoundResult]  # 成功したチームの結果
    best_team_id: str | None  # 最高スコアチームID
    best_score: float | None  # 最高評価スコア（0.0-1.0）
    total_execution_time_seconds: float
    failed_teams_info: list[FailedTeamInfo]  # 失敗チームの詳細情報
    created_at: datetime
```

詳細は [Data Models](../orchestrator/data-models.md#executionsummary) を参照してください。

### 並列実行の特徴

- **失敗隔離**: 1チームの失敗が他チームに影響しない
- **タイムアウト管理**: チーム単位の独立したタイムアウト
- **非同期実行**: asyncio.gather()による効率的な並列処理
- **トランザクション保証**: DuckDB MVCCによる同時書き込み対応

### リソース管理

現在の実装では以下を提供：

1. **チーム単位タイムアウト**
   - 各チームに独立したタイムアウト設定
   - デフォルト: 300秒
   - 設定: `timeout_seconds`パラメータまたはconfig

2. **失敗チーム隔離**
   - 失敗チームは`failed_teams`に記録
   - 成功チームのみでランキング生成
   - 詳細エラー情報の保存

3. **DuckDB並列書き込み**
   - MVCC制御による同時書き込み
   - エクスポネンシャルバックオフリトライ
   - トランザクション保証

## Evaluator（実装済み）

EvaluatorはLeader Agentが生成したSubmissionを評価し、0-100スケールのスコアとフィードバックを生成します。

### 主要な機能

- Pydantic AI Agentベースの評価
- 構造化スコアリング（Structured Output）
- 複数評価基準のサポート
- フィードバックコメント生成
- DuckDBへの評価結果保存

### API概要

```python
class Evaluator:
    """Submission評価とフィードバック生成"""

    def __init__(
        self,
        workspace_path: Path,
        config: EvaluationConfig | None = None
    ):
        """Evaluator初期化"""

    async def evaluate_submission(
        self,
        user_prompt: str,
        submission_content: str
    ) -> tuple[int, str, RunUsage]:
        """Submissionを評価してスコア、フィードバック、使用量を返す

        Returns:
            - score: 0-100の整数スコア
            - feedback: 評価フィードバックコメント
            - usage: LLM使用量
        """
```

### EvaluationConfig

評価設定を表すPydantic Model：

```python
class EvaluationConfig(BaseModel):
    model_name: str = "google-gla:gemini-2.5-flash"
    temperature: float = 0.0
    max_output_tokens: int = 2000
```

### スコアリング

- **入力**: User Prompt、Submission Content
- **出力**: 0-100の整数スコア、フィードバックコメント
- **変換**: 100スケール → 0.0-1.0スケール（DuckDB保存時）

評価基準：
- **Accuracy**: タスク要求への適合度
- **Completeness**: 必要情報の網羅性
- **Clarity**: 説明の明瞭さ

### Structured Output

Pydantic AI Structured Outputによる型安全な評価結果：

```python
class EvaluationResponse(BaseModel):
    score: int = Field(ge=0, le=100)  # 0-100の整数
    feedback: str = Field(min_length=1)
```

### DuckDB統合

評価結果は`leader_board`テーブルに保存されます：

```sql
INSERT INTO leader_board (
    team_id, team_name, round_number,
    evaluation_score,  -- 0.0-1.0スケール
    evaluation_feedback,
    submission_content,
    usage_info
) VALUES (?, ?, ?, ?, ?, ?, ?)
```

詳細は [データベーススキーマ](../../database-schema.md#leader_board-テーブル) を参照してください。

## Verificator（実装予定）

VerificatorはMember Agent設定の検証と品質保証を行います。

### 検証機能

#### 構文チェック

- TOML構文の検証
- 必須フィールドの確認
- データ型の検証

#### 基本妥当性検証

- モデル名の検証
- パラメータ範囲の検証
- 依存関係の検証

#### 品質保証テスト

- 接続確認
- 応答性テスト
- 機能検証
- セキュリティ脆弱性診断
- 宣言されたCapabilityの検証

### 計画されているインターフェース

```python
class Verificator:
    """Member Agent設定の検証"""

    async def validate_syntax(
        self,
        config_path: str
    ) -> ValidationResult:
        """TOML構文検証"""
        pass

    async def validate_semantics(
        self,
        config: MemberAgentConfig
    ) -> ValidationResult:
        """意味的妥当性検証"""
        pass

    async def run_quality_tests(
        self,
        agent: BaseMemberAgent
    ) -> QualityTestResult:
        """品質保証テスト実行"""
        pass

    async def verify_security(
        self,
        agent: BaseMemberAgent
    ) -> SecurityTestResult:
        """セキュリティ診断"""
        pass
```

### 検証プロセス

1. ユーザがTOMLファイル作成
2. Verificatorが検証実行
   - 構文チェック
   - 妥当性検証
   - 品質保証テスト
   - セキュリティテスト
3. システムが設定読み込み
4. チーム割り当て可能化

## Leader Board（実装予定）

Leader Boardはチームパフォーマンスを追跡し、Submissionをランキングします。

### 主要機能

- Submission保存
- スコアリング
- ランキング管理
- ダッシュボード表示

### 計画されているインターフェース

```python
class LeaderBoard:
    """Submissionランキング管理"""

    async def add_submission(
        self,
        submission: Submission,
        evaluation: EvaluationResult
    ) -> None:
        """Submissionを追加"""
        pass

    async def get_rankings(
        self,
        limit: int = 10
    ) -> list[RankedSubmission]:
        """ランキング取得"""
        pass

    async def get_team_performance(
        self,
        team_id: str
    ) -> TeamPerformance:
        """チームパフォーマンス取得"""
        pass
```

## 設定

フレームワークコンポーネントの設定例：

```toml
[orchestration]
max_concurrent_teams = 5
system_timeout_seconds = 3600

[round_controller]
max_rounds = 10
save_message_history = true
database_url = "sqlite:///mixseek.db"

[[evaluators]]
type = "llm"
model = "google-gla:gemini-2.5-flash"
criteria = ["accuracy", "completeness", "clarity"]

[[evaluators]]
type = "custom"
function = "my_module.check_format"

[leader_board]
database_url = "postgresql://localhost/mixseek"
cache_ttl_seconds = 300
```

## 関連リソース

- [API概要](../index.md) - MixSeek-Core API全体
- [Agents API](../agents/index.md) - エージェント関連API
- [Models API](../models/index.md) - データモデルAPI
- [仕様書](https://github.com/your-org/mixseek-core/specs/001-specs/spec.md) - 詳細な機能仕様
