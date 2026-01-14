# API リファレンス

Member Agent APIの詳細なリファレンスです。

## データモデル

### AgentType

サポートされているMember Agentのタイプを定義する列挙型です。

```python
from mixseek.models.member_agent import AgentType

class AgentType(str, Enum):
    PLAIN = "plain"
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
```

利用可能な値：

- `PLAIN` - 基本的な推論エージェント
- `WEB_SEARCH` - Web検索機能付きエージェント
- `CODE_EXECUTION` - コード実行機能付きエージェント

### MemberAgentConfig

エージェントの設定を定義するPydanticモデルです。TOMLファイルから読み込まれます。

```python
from mixseek.models.member_agent import MemberAgentConfig, AgentInstructions

config = MemberAgentConfig(
    name="my-agent",
    type="plain",
    model="google-gla:gemini-2.5-flash",
    temperature=0.2,
    max_tokens=2048,
    instructions=AgentInstructions(text="You are a helpful assistant."),
    description="General purpose assistant"
)
```

フィールド：

- `name: str` - エージェントの一意な識別子（必須）
- `type: str` - エージェントタイプ（必須、標準タイプ: "plain", "web_search", "code_execution"、またはカスタム文字列）
- `model: str` - Pydantic AIモデル識別子（デフォルト: "google-gla:gemini-2.5-flash"）。標準タイプでは `google-gla:`, `google-vertex:`, `openai:`, `anthropic:`, `grok:`, `grok-responses:` のプレフィックスが必須。`type="custom"` では任意のプレフィックスが使用可能
- `temperature: float` - 応答のランダム性（0.0-1.0、デフォルト: 0.2）
- `max_tokens: int` - 最大トークン数（1-8192、デフォルト: 2048）
- `instructions: AgentInstructions` - エージェントへの指示（必須）
- `description: str` - 人間が読める説明文（デフォルト: ""）
- `timeout_seconds: int | None` - HTTPリクエストタイムアウト（秒、デフォルト: None）
- `max_retries: int` - LLM API呼び出しの最大リトライ回数（デフォルト: 3、Pydantic AIに委任）
- `tool_settings: ToolSettings | None` - ツール固有の設定（デフォルト: None）
- `plugin: PluginMetadata | None` - カスタムプラグイン設定（デフォルト: None）
- `metadata: dict[str, Any]` - カスタムプラグイン用の追加メタデータ（デフォルト: {}）

### MemberAgentResult

エージェント実行の結果を表すモデルです。

```python
from mixseek.models.member_agent import MemberAgentResult

# 成功結果の作成
result = MemberAgentResult.success(
    content="Response content",
    agent_name="my-agent",
    agent_type="plain",
    execution_time_ms=1500,
    usage_info={"total_tokens": 150}
)

# エラー結果の作成
error_result = MemberAgentResult.error(
    error_message="Failed to process request",
    agent_name="my-agent",
    agent_type="plain",
    error_code="EXECUTION_ERROR"
)
```

フィールド：

- `status: ResultStatus` - 実行ステータス（SUCCESS/ERROR/WARNING）
- `content: str` - メイン結果コンテンツ
- `agent_name: str` - エージェント名
- `agent_type: str` - エージェントタイプ
- `timestamp: datetime` - 結果生成タイムスタンプ
- `execution_time_ms: int | None` - 実行時間（ミリ秒）
- `usage_info: dict[str, Any] | None` - 使用量情報（トークン数など）
- `error_message: str | None` - エラーメッセージ
- `error_code: str | None` - エラーコード
- `warning_message: str | None` - 警告メッセージ
- `retry_count: int` - リトライ試行回数
- `max_retries_exceeded: bool` - 最大リトライ回数超過フラグ
- `metadata: dict[str, Any]` - 追加メタデータ

メソッド：

- `success(content, agent_name, agent_type, **kwargs) -> MemberAgentResult` - 成功結果を作成（クラスメソッド）
- `error(error_message, agent_name, agent_type, **kwargs) -> MemberAgentResult` - エラー結果を作成（クラスメソッド）
- `is_success() -> bool` - 成功判定
- `is_error() -> bool` - エラー判定

### PluginMetadata

カスタムプラグインの設定を定義するモデルです。

```python
from mixseek.models.member_agent import PluginMetadata

plugin = PluginMetadata(
    path="/path/to/plugin.py",
    agent_class="CustomAgent"
)
```

フィールド：

- `path: str` - プラグインファイルのパス（必須）
- `agent_class: str` - プラグインクラス名（必須）

### ToolSettings

ツール固有の設定を定義するモデルです。

```python
from mixseek.models.member_agent import ToolSettings, WebSearchToolConfig

tool_settings = ToolSettings(
    web_search=WebSearchToolConfig(max_results=10, timeout=30)
)
```

フィールド：

- `web_search: WebSearchToolConfig | None` - Web検索ツール設定
- `code_execution: CodeExecutionToolConfig | None` - コード実行ツール設定

### WebSearchToolConfig

Web検索ツールの設定を定義するモデルです。

```python
from mixseek.models.member_agent import WebSearchToolConfig

web_search_config = WebSearchToolConfig(
    max_results=10,
    timeout=30
)
```

フィールド：

- `max_results: int` - 最大検索結果数（1-50、デフォルト: 10）
- `timeout: int` - タイムアウト時間（秒、1-120、デフォルト: 30）

### CodeExecutionToolConfig

コード実行ツールの設定を定義するモデルです。

重要: このモデルのフィールドはドキュメント専用です。実際のセキュリティ制約はプロバイダー側で制御され、設定できません。

```python
from mixseek.models.member_agent import CodeExecutionToolConfig

code_config = CodeExecutionToolConfig(
    expected_min_timeout_seconds=300,
    expected_network_access=False
)
```

フィールド（すべてドキュメント専用）：

- `provider_controlled: Literal[True]` - プロバイダー制御フラグ（常にTrue）
- `expected_min_timeout_seconds: int` - 期待される最小タイムアウト（デフォルト: 300）
- `expected_available_modules: list[str]` - 期待される利用可能モジュールリスト
- `expected_network_access: Literal[False]` - 期待されるネットワークアクセス（常にFalse）

## エージェントクラス

### BaseMemberAgent

すべてのMember Agentの抽象基底クラスです。

```python
from mixseek.agents.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult
```

抽象メソッド：

- `async execute(task: str, context: dict[str, Any] | None, **kwargs) -> MemberAgentResult`
  - タスクを実行
  - **引数**:
    - `task: str` - 実行するタスクまたはプロンプト
    - `context: dict[str, Any] | None` - 実行コンテキスト情報（Leader Agent経由で呼び出される場合は自動的に注入されます）
      - `execution_id` (str): オーケストレーション実行識別子（UUID）
      - `team_id` (str): チームID
      - `round_number` (int): ラウンド番号
    - `**kwargs` - 追加の実行パラメータ
  - **戻り値**: `MemberAgentResult`
  - **例外**: サブクラスで実装されていない場合 `NotImplementedError`

オーバーライド可能なメソッド：

- `async initialize() -> None` - エージェントリソースの初期化
- `async cleanup() -> None` - エージェントリソースのクリーンアップ

プロパティ：

- `agent_name: str` - エージェント名
- `agent_type: str` - エージェントタイプ

### PlainMemberAgent

基本的な推論を行うエージェント実装です。

```python
from mixseek.agents.plain import PlainMemberAgent
from mixseek.models.member_agent import MemberAgentConfig

config = MemberAgentConfig.from_toml("plain_agent.toml")
agent = PlainMemberAgent(config)

result = await agent.execute("Explain recursion in programming")
if result.is_success():
    print(result.content)
```

コンストラクタ：

- `__init__(config: MemberAgentConfig)`
  - **引数**: `config` - 検証済みのエージェント設定
  - **例外**: `ValueError` - 認証失敗時

メソッド：

- `async execute(task: str, context: dict[str, Any] | None, **kwargs) -> MemberAgentResult`
  - タスクを実行
  - リトライロジック付き
  - 使用量制限チェック付き

### WebSearchMemberAgent

Web検索機能を持つエージェント実装です。

```python
from mixseek.agents.web_search import WebSearchMemberAgent
from mixseek.models.member_agent import MemberAgentConfig

config = MemberAgentConfig.from_toml("web_search_agent.toml")
agent = WebSearchMemberAgent(config)

result = await agent.execute("What are the latest AI developments?")
if result.is_success():
    print(result.content)
```

コンストラクタ：

- `__init__(config: MemberAgentConfig)`
  - **引数**: `config` - 検証済みのエージェント設定
  - **例外**: `ValueError` - 認証失敗時

メソッド：

- `async execute(task: str, context: dict[str, Any] | None, **kwargs) -> MemberAgentResult`
  - タスクを実行
  - Web検索ツールを自動的に使用
  - リトライロジック付き

### CodeExecutionMemberAgent

コード実行機能を持つエージェント実装です。

重要: Anthropic Claudeモデルのみサポート。

```python
from mixseek.agents.code_execution import CodeExecutionMemberAgent
from mixseek.models.member_agent import MemberAgentConfig

config = MemberAgentConfig.from_toml("code_execution_agent.toml")
agent = CodeExecutionMemberAgent(config)

result = await agent.execute("Calculate the factorial of 10")
if result.is_success():
    print(result.content)
```

コンストラクタ：

- `__init__(config: MemberAgentConfig)`
  - **引数**: `config` - 検証済みのエージェント設定
  - **例外**:
    - `ValueError` - Anthropic Claude以外のモデルを使用時
    - `ValueError` - 認証失敗時

メソッド：

- `async execute(task: str, context: dict[str, Any] | None, **kwargs) -> MemberAgentResult`
  - タスクを実行
  - コード実行ツールを自動的に使用
  - リトライロジック付き

## ファクトリクラス

### MemberAgentFactory

エージェントインスタンスを作成するファクトリクラスです。

```python
from mixseek.agents.factory import MemberAgentFactory
from mixseek.models.member_agent import MemberAgentConfig

config = MemberAgentConfig.from_toml("agent.toml")
agent = MemberAgentFactory.create_agent(config)

result = await agent.execute("Your task here")
```

クラスメソッド：

- `create_agent(config: MemberAgentConfig) -> BaseMemberAgent`
  - 設定に基づいてエージェントを作成
  - **引数**: `config` - 検証済みのエージェント設定
  - **戻り値**: 適切なタイプのエージェントインスタンス
  - **例外**: `ValueError` - サポートされていないエージェントタイプ

- `register_agent(agent_type: str, agent_class: type[BaseMemberAgent]) -> None`
  - カスタムエージェントタイプを登録
  - **引数**:
    - `agent_type` - 登録するエージェントタイプ（文字列識別子）
    - `agent_class` - エージェントクラス実装

- `get_supported_types() -> list[str]`
  - サポートされているエージェントタイプのリストを取得
  - **戻り値**: エージェントタイプの文字列リスト

## 設定ローダー

### MemberAgentLoader

TOMLファイルからエージェント設定を読み込むローダークラスです。

```python
from mixseek.config.member_agent_loader import MemberAgentLoader

loader = MemberAgentLoader()
config = loader.load_from_toml("agent.toml")
```

メソッド：

- `load_from_toml(file_path: str | Path) -> MemberAgentConfig`
  - TOMLファイルから設定を読み込む
  - **引数**: `file_path` - TOMLファイルパス
  - **戻り値**: 検証済みの `MemberAgentConfig`
  - **例外**:
    - `FileNotFoundError` - ファイルが存在しない
    - `ValueError` - TOML構文エラー
    - `ValidationError` - 設定検証エラー

- `load_from_dict(config_dict: dict[str, Any]) -> MemberAgentConfig`
  - 辞書から設定を読み込む
  - **引数**: `config_dict` - 設定辞書
  - **戻り値**: 検証済みの `MemberAgentConfig`
  - **例外**: `ValidationError` - 設定検証エラー

## 認証

### create_authenticated_model

認証済みのPydantic AIモデルを作成します。

```python
from mixseek.core.auth import create_authenticated_model

# Google Gemini
model = create_authenticated_model("google-gla:gemini-2.5-flash")

# Anthropic Claude
model = create_authenticated_model("anthropic:claude-sonnet-4-5-20250929")
```

関数：

- `create_authenticated_model(model_name: str) -> Model`
  - **引数**: `model_name` - Pydantic AIモデル識別子
  - **戻り値**: 認証済みモデルインスタンス
  - **例外**: `AuthenticationError` - 認証失敗時

サポートされているプロバイダー：

- Google Gemini: `google-gla:model-name`
  - 環境変数: `GOOGLE_API_KEY`
- Vertex AI: `google-vertex:model-name`
  - 環境変数: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- Anthropic Claude: `anthropic:model-name`
  - 環境変数: `ANTHROPIC_API_KEY`

## ロギング

### MemberAgentLogger

エージェント実行のロギングを管理します。

```python
from mixseek.utils.logging import MemberAgentLogger

logger = MemberAgentLogger(log_level="INFO", enable_file_logging=True)

# 実行開始ログ
execution_id = logger.log_execution_start(
    agent_name="my-agent",
    agent_type="plain",
    task="Sample task",
    model_id="google-gla:gemini-2.5-flash"
)

# 実行完了ログ
logger.log_execution_complete(
    execution_id=execution_id,
    result=result,
    usage_info={"total_tokens": 150}
)

# エラーログ
logger.log_error(
    execution_id=execution_id,
    error=exception,
    context={"task": "Sample task"}
)
```

メソッド：

- `log_execution_start(agent_name, agent_type, task, model_id, **kwargs) -> str`
  - 実行開始をログに記録
  - **戻り値**: 実行ID

- `log_execution_complete(execution_id, result, usage_info=None) -> None`
  - 実行完了をログに記録

- `log_error(execution_id, error, context=None) -> None`
  - エラーをログに記録

## 使用例

### 基本的な使用方法

```python
import asyncio
from mixseek.config.member_agent_loader import MemberAgentLoader
from mixseek.agents.factory import MemberAgentFactory

async def main():
    # 設定を読み込む
    loader = MemberAgentLoader()
    config = loader.load_from_toml("plain_agent.toml")

    # エージェントを作成
    agent = MemberAgentFactory.create_agent(config)

    # タスクを実行
    result = await agent.execute("Explain the benefits of type safety")

    if result.is_success():
        print(f"Success: {result.content}")
        print(f"Execution time: {result.execution_time_ms}ms")
        if result.usage_info:
            print(f"Tokens used: {result.usage_info.get('total_tokens')}")
    else:
        print(f"Error: {result.error_message}")
        print(f"Error code: {result.error_code}")

asyncio.run(main())
```

### カスタムエージェントの作成

```python
from mixseek.agents.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult, AgentInstructions
from mixseek.agents.factory import MemberAgentFactory

class CustomMemberAgent(BaseMemberAgent):
    """カスタム Member Agent 実装"""

    async def execute(self, task: str, context=None, **kwargs):
        # カスタムロジック
        return MemberAgentResult.success(
            content=f"Processed: {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type
        )

# カスタムタイプを登録（文字列で指定）
custom_type = "custom"
MemberAgentFactory.register_agent(custom_type, CustomMemberAgent)

# 使用
config = MemberAgentConfig(
    name="my-custom-agent",
    type=custom_type,
    model="google-gla:gemini-2.5-flash-lite",
    instructions=AgentInstructions(text="Custom instructions")
)
agent = MemberAgentFactory.create_agent(config)
```

### エラーハンドリング

```python
from mixseek.core.auth import AuthenticationError
from pydantic import ValidationError

try:
    config = loader.load_from_toml("agent.toml")
    agent = MemberAgentFactory.create_agent(config)
    result = await agent.execute("Task")

except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
except ValidationError as e:
    print(f"Invalid configuration: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValueError as e:
    print(f"Error: {e}")
```

## 参考資料

- [Member Agent ガイド](../../member-agents.md) - 使用方法とトラブルシューティング
- [開発者ガイド](../../developer-guide.md) - 開発環境のセットアップ
- ソースコード:
  - モデル定義: `src/mixseek/models/member_agent.py`
  - エージェント実装: `src/mixseek/agents/`
  - 設定ローダー: `src/mixseek/config/member_agent_loader.py`
