# Agents API

エージェント関連のAPIリファレンスです。

## 概要

MixSeek-Coreのエージェントシステムは、Leader AgentとMember Agentの2層構造で構成されます：

- **Leader Agent**: タスク分解、Member Agent調整、結果統合を担当
- **Member Agent**: 特定ドメインに特化したタスク実行を担当

## Member Agents

```{toctree}
:maxdepth: 2

member-agents
```

Member Agentは特定の機能やドメインに特化したエージェントです。

### 実装済みのMember Agent

現在、以下の3種類のMember Agentが実装されています：

#### Plain Agent

基本的な推論と分析を行うエージェントです。

- **用途**: 一般的な質問応答、テキスト分析、論理的推論
- **ツール**: なし（モデルの推論能力のみ）
- **実装**: `src/mixseek/agents/plain.py`

#### Web Search Agent

Web検索機能を持つエージェントです。

- **用途**: 最新情報の調査、事実確認、情報収集
- **ツール**: Pydantic AI WebSearchTool
- **実装**: `src/mixseek/agents/web_search.py`

#### Code Execution Agent

Pythonコードを実行できるエージェントです。

- **用途**: 数値計算、データ分析、統計処理
- **ツール**: Pydantic AI CodeExecutionTool
- **制限**: Anthropic Claudeモデルのみサポート
- **実装**: `src/mixseek/agents/code_execution.py`

### Member Agent 共通インターフェース

すべてのMember Agentは `BaseMemberAgent` を継承し、共通のインターフェースを実装します：

```python
from mixseek.agents.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult

class CustomMemberAgent(BaseMemberAgent):
    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> MemberAgentResult:
        # タスク実行の実装
        pass
```

主要なメソッド：

- `execute(task, context, **kwargs)` - タスク実行（必須実装）
- `initialize()` - エージェント初期化（オプション）
- `cleanup()` - リソースクリーンアップ（オプション）

### Member Agent Factory

エージェントインスタンスを作成するファクトリクラスです：

```python
from mixseek.agents.factory import MemberAgentFactory
from mixseek.models.member_agent import MemberAgentConfig

config = MemberAgentConfig.from_toml("agent.toml")
agent = MemberAgentFactory.create_agent(config)
```

主要なメソッド：

- `create_agent(config)` - エージェント作成
- `register_agent(agent_type, agent_class)` - カスタムエージェント登録
- `get_supported_types()` - サポートされているエージェントタイプ一覧

詳細なAPIリファレンスは [Member Agent API](member-agents.md) を参照してください。

## Leader Agents（将来実装予定）

Leader Agentは複数のMember Agentを調整し、タスクを分解して割り当て、結果を統合します。

### 計画されている機能

- タスク分解とサブタスク生成
- Member Agentへの作業割当
- 進捗管理とモニタリング
- 結果の統合とSubmission生成
- エラーハンドリングとリトライ

### Leader Agent インターフェース（計画）

```python
class LeaderAgent:
    async def plan_task(self, user_prompt: str) -> TaskPlan:
        """タスクをサブタスクに分解"""
        pass

    async def delegate_to_members(
        self,
        subtasks: list[SubTask]
    ) -> list[MemberAgentResult]:
        """Member Agentにサブタスクを割り当て"""
        pass

    async def synthesize_results(
        self,
        results: list[MemberAgentResult]
    ) -> Submission:
        """結果を統合してSubmissionを生成"""
        pass
```

## 設定

エージェントの設定はTOMLファイルで管理されます：

```toml
[agent]
name = "my-agent"
type = "plain"
model = "google-gla:gemini-2.5-flash"
temperature = 0.2
max_tokens = 2048

[agent.instructions]
text = "You are a helpful assistant."
timeout_seconds = 30
max_retries = 1
```

設定の詳細は [Member Agent ガイド](../../member-agents.md) を参照してください。

## 使用例

### 基本的な使用

```python
import asyncio
from mixseek.config.member_agent_loader import MemberAgentLoader
from mixseek.agents.factory import MemberAgentFactory

async def main():
    # 設定を読み込み
    loader = MemberAgentLoader()
    config = loader.load_from_toml("plain_agent.toml")

    # エージェントを作成
    agent = MemberAgentFactory.create_agent(config)

    # タスクを実行
    result = await agent.execute("Explain Python decorators")

    if result.is_success():
        print(result.content)
    else:
        print(f"Error: {result.error_message}")

asyncio.run(main())
```

### カスタムMember Agentの作成

```python
from mixseek.agents.base import BaseMemberAgent
from mixseek.models.member_agent import AgentType, MemberAgentResult
from mixseek.agents.factory import MemberAgentFactory

class DatabaseMemberAgent(BaseMemberAgent):
    """データベースクエリを実行するカスタムエージェント"""

    async def execute(self, task: str, context=None, **kwargs):
        # データベースクエリ実行ロジック
        query_result = await self._execute_query(task)

        return MemberAgentResult.success(
            content=query_result,
            agent_name=self.agent_name,
            agent_type=self.agent_type.value
        )

    async def _execute_query(self, query: str) -> str:
        # 実際のクエリ実行
        pass

# カスタムタイプを登録
custom_type = AgentType("database")
MemberAgentFactory.register_agent(custom_type, DatabaseMemberAgent)
```

## 関連リソース

- [Member Agent API詳細](member-agents.md) - 詳細なAPIリファレンス
- [Member Agent ガイド](../../member-agents.md) - 使用方法とチュートリアル
- [開発者ガイド](../../developer-guide.md) - 開発環境のセットアップ
