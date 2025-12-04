# Member Agent モデル

Member Agent関連のデータモデルの詳細なリファレンスです。

## 概要

Member Agentシステムは、設定、実行結果、リソース管理などのデータ構造をPydantic Modelで定義しています。すべてのモデルは型安全で、ランタイム検証を提供します。

## 設定モデル

### MemberAgentConfig

エージェント設定を定義する中核モデルです。TOMLファイルから読み込まれます。

**ソースコード**: `src/mixseek/models/member_agent.py:273`

#### フィールド

**必須フィールド**:

- `name: str` - エージェントの一意な識別子
- `type: AgentType` - エージェントタイプ（plain/web_search/code_execution）
- `instructions: AgentInstructions` - エージェントへの指示

**モデル設定** (デフォルト値あり):

- `model: str` - Pydantic AIモデル識別子（デフォルト: "google-gla:gemini-2.5-flash-lite"）
- `temperature: float | None` - 応答のランダム性（0.0-2.0、デフォルト: None = モデルのデフォルト値を使用）
- `max_tokens: int | None` - 最大トークン数（> 0、デフォルト: None = モデルのデフォルト値を使用）
- `stop_sequences: list[str] | None` - 生成を停止するシーケンスのリスト（デフォルト: None）
- `top_p: float | None` - Top-pサンプリングパラメータ（0.0-1.0、デフォルト: None = モデルのデフォルト値を使用）
- `seed: int | None` - ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート、デフォルト: None）

**動作設定**:

- `description: str` - 人間が読める説明文（デフォルト: ""）
- `timeout_seconds: int | None` - HTTPリクエストタイムアウト（秒、>= 1、デフォルト: None = デフォルトタイムアウト使用）
- `max_retries: int` - LLM API呼び出しの最大リトライ回数（>= 0、デフォルト: 3、Pydantic AIに委任）
- `tool_settings: ToolSettings | None` - ツール固有の設定（デフォルト: None）
- `plugin: PluginMetadata | None` - カスタムプラグイン設定（デフォルト: None）

**メタデータ**:

- `metadata: dict[str, Any]` - カスタムプラグイン用の追加メタデータ（デフォルト: {}）

#### バリデーション

- `model`: モデル識別子の形式検証（`google-gla:`, `openai:`, `anthropic:` プレフィックス）
- `temperature`: 0.0-2.0の範囲（Noneも許可）
- `max_tokens`: > 0（Noneも許可、上限なし）
- `top_p`: 0.0-1.0の範囲（Noneも許可）

#### 使用例

```python
from mixseek.models.member_agent import MemberAgentConfig, AgentType

config = MemberAgentConfig(
    name="my-agent",
    type=AgentType.PLAIN,
    model="google-gla:gemini-2.5-flash-lite",
    temperature=0.7,  # Optional: None uses model default
    max_tokens=4096,  # Optional: None uses model default
    stop_sequences=["END", "STOP"],  # Optional
    top_p=0.9,  # Optional: None uses model default
    seed=42,  # Optional: for reproducibility
    system_instruction="You are a helpful assistant.",  # str | None
    description="General purpose assistant"
)
```

### AgentInstructions

エージェントへの指示を定義するモデルです。

**ソースコード**: `src/mixseek/models/member_agent.py:27`

#### フィールド

- `text: str` - システム指示テキスト（最小10文字）

#### バリデーション

- `min_length=10`: 最小10文字必須

#### 使用例

```python
from mixseek.models.member_agent import AgentInstructions

instructions = AgentInstructions(
    text="You are a data analyst. Analyze data and provide insights."
)
```

### RetryConfig

リトライ動作を設定するモデルです。

**ソースコード**: `src/mixseek/models/member_agent.py:33`

#### フィールド

- `max_retries: int` - 最大リトライ回数（0-10、デフォルト: 1）
- `initial_delay: float` - 初期遅延時間（秒、0.1-60.0、デフォルト: 1.0）
- `backoff_factor: float` - バックオフ係数（1.0-10.0、デフォルト: 2.0）

#### 使用例

```python
from mixseek.models.member_agent import RetryConfig

retry_config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0
)
```

リトライ遅延の計算:
- 1回目: initial_delay × (backoff_factor^0) = 1.0秒
- 2回目: initial_delay × (backoff_factor^1) = 2.0秒
- 3回目: initial_delay × (backoff_factor^2) = 4.0秒

## 実行結果モデル

### MemberAgentResult

エージェント実行結果を表すモデルです。

**ソースコード**: `src/mixseek/models/member_agent.py:51`

#### フィールド

**ステータスと結果**:

- `status: ResultStatus` - 実行ステータス（SUCCESS/ERROR/WARNING）
- `content: str` - メイン結果コンテンツ

**メタデータ**:

- `agent_name: str` - エージェント名
- `agent_type: str` - エージェントタイプ

**タイミング**:

- `timestamp: datetime` - 結果生成タイムスタンプ（自動生成）
- `execution_time_ms: int | None` - 実行時間（ミリ秒）

**使用量**:

- `usage_info: dict[str, Any] | None` - 使用量情報（トークン数など）

**エラー情報**:

- `error_message: str | None` - エラーメッセージ
- `error_code: str | None` - エラーコード

**警告情報**:

- `warning_message: str | None` - 警告メッセージ

**リトライ情報**:

- `retry_count: int` - リトライ試行回数（デフォルト: 0）
- `max_retries_exceeded: bool` - 最大リトライ回数超過フラグ（デフォルト: False）

**追加コンテキスト**:

- `metadata: dict[str, Any]` - 追加メタデータ（デフォルト: {}）

#### ファクトリメソッド

**success()** - 成功結果を作成:

```python
result = MemberAgentResult.success(
    content="Response content",
    agent_name="my-agent",
    agent_type="plain",
    execution_time_ms=1500,
    usage_info={"total_tokens": 150},
    retry_count=0,
    metadata={"version": "1.0"}
)
```

**error()** - エラー結果を作成:

```python
result = MemberAgentResult.error(
    error_message="Failed to process request",
    agent_name="my-agent",
    agent_type="plain",
    error_code="EXECUTION_ERROR",
    execution_time_ms=500,
    retry_count=2,
    max_retries_exceeded=True
)
```

#### ヘルパーメソッド

- `is_success() -> bool` - 成功判定
- `is_error() -> bool` - エラー判定

#### 使用例

```python
from mixseek.models.member_agent import MemberAgentResult

# 成功結果の作成
result = MemberAgentResult.success(
    content="Analysis complete",
    agent_name="data-analyst",
    agent_type="plain",
    execution_time_ms=2500
)

# 結果の判定
if result.is_success():
    print(f"Success: {result.content}")
    print(f"Execution time: {result.execution_time_ms}ms")
else:
    print(f"Error: {result.error_message}")
```

### ResultStatus

実行結果ステータスを定義する列挙型です。

**ソースコード**: `src/mixseek/models/member_agent.py:43`

#### 値

- `SUCCESS = "success"` - 成功
- `ERROR = "error"` - エラー
- `WARNING = "warning"` - 警告

#### 使用例

```python
from mixseek.models.member_agent import ResultStatus

status = ResultStatus.SUCCESS
```

## ツール設定モデル

### ToolSettings

ツール固有の設定を定義するモデルです。

**ソースコード**: `src/mixseek/models/member_agent.py:194`

#### フィールド

- `web_search: WebSearchToolConfig | None` - Web検索ツール設定（デフォルト: None）
- `code_execution: CodeExecutionToolConfig | None` - コード実行ツール設定（デフォルト: None）

#### 使用例

```python
from mixseek.models.member_agent import ToolSettings, WebSearchToolConfig

tool_settings = ToolSettings(
    web_search=WebSearchToolConfig(max_results=10, timeout=30)
)
```

### WebSearchToolConfig

Web検索ツールの設定を定義するモデルです。

**ソースコード**: `src/mixseek/models/member_agent.py:141`

#### フィールド

- `max_results: int` - 最大検索結果数（1-50、デフォルト: 10）
- `timeout: int` - タイムアウト時間（秒、1-120、デフォルト: 30）

#### 使用例

```python
from mixseek.models.member_agent import WebSearchToolConfig

web_config = WebSearchToolConfig(
    max_results=10,
    timeout=30
)
```

### CodeExecutionToolConfig

コード実行ツールの設定を定義するモデルです。

**重要**: このモデルのフィールドはドキュメント専用です。実際のセキュリティ制約はプロバイダー側（Anthropic）で制御され、設定できません。

**ソースコード**: `src/mixseek/models/member_agent.py:148`

#### フィールド（すべてドキュメント専用）

- `provider_controlled: Literal[True]` - プロバイダー制御フラグ（常にTrue）
- `expected_min_timeout_seconds: int` - 期待される最小タイムアウト（デフォルト: 300）
- `expected_available_modules: list[str]` - 期待される利用可能モジュールリスト
- `expected_network_access: Literal[False]` - 期待されるネットワークアクセス（常にFalse）

#### 使用例

```python
from mixseek.models.member_agent import CodeExecutionToolConfig

# 注意: これらの設定は実際には適用されません（ドキュメント専用）
code_config = CodeExecutionToolConfig(
    expected_min_timeout_seconds=300,
    expected_network_access=False
)
```

## 列挙型

### AgentType

サポートされているエージェントタイプを定義する列挙型です。

**ソースコード**: `src/mixseek/models/member_agent.py:15`

#### 値

- `PLAIN = "plain"` - 基本的な推論エージェント
- `WEB_SEARCH = "web_search"` - Web検索機能付きエージェント
- `CODE_EXECUTION = "code_execution"` - コード実行機能付きエージェント

#### 使用例

```python
from mixseek.models.member_agent import AgentType

agent_type = AgentType.PLAIN
print(str(agent_type))  # "plain"
```

## TOMLファイルとの連携

### 設定ファイル例

```toml
[agent]
name = "my-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash"
temperature = 0.2
max_tokens = 2048
description = "General purpose assistant"

system_instruction = "You are a helpful assistant."
timeout_seconds = 60
max_retries = 3

[agent.tool_settings.web_search]
max_results = 10
timeout = 30

[agent.metadata]
version = "1.0.0"
author = "Your Name"
```

### 設定の読み込み

```python
from mixseek.config.member_agent_loader import MemberAgentLoader

loader = MemberAgentLoader()
config = loader.load_from_toml("agent.toml")

# configはMemberAgentConfigインスタンス
print(config.name)  # "my-agent"
print(config.type)  # AgentType.PLAIN
```

## モデル検証

すべてのPydantic Modelは自動検証機能を提供します：

### バリデーションエラー

```python
from pydantic import ValidationError
from mixseek.models.member_agent import MemberAgentConfig

try:
    config = MemberAgentConfig(
        name="test",
        type="invalid_type",  # 無効なタイプ
        instructions={"text": "test"}
    )
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

すべてのモデルは型安全性を保証します：

- **静的型チェック**: mypyによる検証
- **ランタイム検証**: Pydanticによる自動検証
- **包括的なバリデーション**: フィールド検証、範囲チェック、カスタムバリデーター

## 関連リソース

- [Member Agent API](../agents/member-agents.md) - Member Agentの使用方法
- [Agents API](../agents/index.md) - エージェント関連API
- [Models API概要](index.md) - モデルAPI全体
- [開発者ガイド](../../developer-guide.md) - 型安全性のベストプラクティス
