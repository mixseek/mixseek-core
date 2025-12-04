# Pydantic AI 実装ガイド

このガイドでは、MixSeek-Coreで使用されているPydantic AIの主要な概念と実装パターンを解説します。

## 目次

1. [Pydantic AIとは](#pydantic-aiとは)
2. [Agent作成](#agent作成)
3. [Agent Delegation](#agent-delegation)
4. [Tool / Toolset](#tool--toolset)
5. [Usage Limits](#usage-limits)
6. [Run Usage](#run-usage)
7. [依存性注入（Dependencies）](#依存性注入dependencies)
8. [Message History](#message-history)
9. [実装例](#実装例)

## Pydantic AIとは

Pydantic AIは、型安全なエージェント開発を実現するPythonフレームワークです。

**主な特徴**:
- Pydanticの型システムによる型安全性
- Agent Delegationによる柔軟なエージェント連携
- Usage Limitsによるリソース管理
- Message Historyの永続化と復元

**MixSeek-Coreでの役割**:
- Leader AgentとMember Agentの実装基盤
- エージェント間通信の型安全な実装
- リソース使用量の追跡と制限

## Agent作成

### 基本的なAgent作成

```python
from pydantic_ai import Agent

# 最もシンプルなAgent
agent = Agent(
    model="gemini-2.5-flash-lite",
    system_prompt="あなたは研究アシスタントです。"
)

# 実行
result = await agent.run("Pythonの型ヒントについて教えて")
print(result.output)
```

### 依存性注入を使ったAgent作成

```python
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

class TeamDependencies(BaseModel):
    team_id: str
    submissions: list[dict] = []

# 依存性注入型を指定したAgent
agent = Agent(
    model="gemini-2.5-flash-lite",
    deps_type=TeamDependencies,
    system_prompt="あなたはチームリーダーです。"
)

# 依存性を渡して実行
deps = TeamDependencies(team_id="team-001")
result = await agent.run("タスクを分析して", deps=deps)
```

**参照実装**: `src/mixseek/agents/leader/agent.py:36`

## Agent Delegation

Agent Delegationは、Leader AgentがToolを通じて必要なMember Agentを動的に選択・実行するパターンです。

### なぜAgent Delegationが必要か

**従来の並列実行の問題点**:
- すべてのAgentを毎回実行するため、リソースが無駄
- タスクに不要なAgentも実行される
- コストと実行時間が増大

**Agent Delegationの利点**:
- LLMがタスクを分析し、必要なAgentのみ選択
- リソース効率の向上
- 柔軟なタスク実行

### Agent Delegationの仕組み

```text
User Prompt
    ↓
Leader Agent（LLMが判断）
    ↓
必要なToolのみ選択・実行
    ├─→ Tool: plain_agent_research
    ├─→ Tool: web_search_agent_latest_news
    └─→ Tool: code_exec_agent_calculation
         ↓
Member Agentが実行され、結果を返す
```

**参照実装**: `src/mixseek/agents/leader/tools.py:23`

## Tool / Toolset

ToolはPydantic AIにおけるエージェント間通信の仕組みです。各Member AgentはToolとして登録され、Leader Agentから呼び出されます。

### Toolの基本構造

```python
from pydantic_ai import Agent, RunContext

leader_agent = Agent("gemini-2.5-flash-lite")

@leader_agent.tool
async def research_tool(ctx: RunContext, task: str) -> str:
    """リサーチタスクを実行するツール

    Args:
        ctx: RunContext（依存性とUsage情報を含む）
        task: 実行するタスクの説明

    Returns:
        リサーチ結果のテキスト
    """
    # Member Agentを実行
    result = await member_agent.run(task)
    return result.output
```

### Tool動的登録パターン（MixSeek-Core）

MixSeek-CoreではTOML設定から動的にToolを生成・登録します。

```python
def register_member_tools(
    leader_agent: Agent[TeamDependencies, str],
    team_config: TeamConfig,
    member_agents: dict[str, Agent]
) -> None:
    """TOML設定からMember Agent ToolをLeader Agentに登録"""

    for member_config in team_config.members:
        tool_name = member_config.get_tool_name()
        member_agent = member_agents[member_config.agent_name]

        # Toolクロージャー生成
        def make_tool_func(mc: MemberAgentConfig, ma: Agent):
            async def tool_func(ctx: RunContext[TeamDependencies], task: str) -> str:
                # Member Agent実行（Usage統合）
                result = await ma.run(
                    task,
                    deps=ctx.deps,
                    usage=ctx.usage  # 重要: Leader AgentのUsageに統合
                )

                # 結果を記録
                ctx.deps.submissions.append({
                    "agent_name": mc.agent_name,
                    "content": result.output,
                    "usage": result.usage()
                })

                return str(result.output)

            # Tool関数のメタデータ設定
            tool_func.__name__ = tool_name
            tool_func.__doc__ = mc.tool_description

            return tool_func

        # Tool登録
        tool = make_tool_func(member_config, member_agent)
        leader_agent.tool(tool)
```

**重要なポイント**:
- `usage=ctx.usage` で Leader Agent の Usage に統合
- Tool関数の `__name__` と `__doc__` を設定（LLMがToolを選択する際の情報）
- クロージャーを使って設定情報をキャプチャ

**参照実装**: `src/mixseek/agents/leader/tools.py:23`

## Run Usage

Run UsageはPydantic AIのリソース使用量測定データです。各Agent実行後に取得できます。

### Run Usageの取得

```python
# Agent実行
result = await agent.run("タスクを実行")

# Run Usage取得
usage = result.usage()

print(f"Input tokens: {usage.total_tokens()}")
print(f"Output tokens: {usage.details['output_tokens']}")
print(f"Requests: {usage.requests}")
```

### Member Agent実行での統合

```python
async def tool_func(ctx: RunContext[TeamDependencies], task: str) -> str:
    """Member AgentをToolとして実行"""

    # Member Agent実行（Leader AgentのUsageに統合）
    result = await member_agent.run(
        task,
        deps=ctx.deps,
        usage=ctx.usage  # ★ これでLeader AgentのUsageに統合される
    )

    # MemberSubmissionに記録
    submission = MemberSubmission(
        agent_name="research-agent",
        agent_type="plain",
        content=result.output,
        usage=result.usage(),  # Run Usageを記録
        timestamp=datetime.now(UTC)
    )
    ctx.deps.submissions.append(submission)

    return str(result.output)
```

**記録される情報**:
- `input_tokens`: 入力トークン数
- `output_tokens`: 出力トークン数
- `requests`: リクエスト数
- `total_tokens()`: 総トークン数

**参照実装**: `src/mixseek/agents/leader/tools.py:74`

## 依存性注入（Dependencies）

依存性注入は、Agent実行時にチーム固有のデータを渡す仕組みです。

### 依存性型の定義

```python
from pydantic import BaseModel

class TeamDependencies(BaseModel):
    """チーム固有の依存性データ"""

    team_id: str
    submissions: list[MemberSubmission] = []
    context: dict[str, Any] = {}
```

### Agent作成時に依存性型を指定

```python
leader_agent = Agent(
    model="gemini-2.5-flash-lite",
    deps_type=TeamDependencies,  # ★ 依存性型を指定
    system_prompt="..."
)
```

### Tool内で依存性にアクセス

```python
@leader_agent.tool
async def research_tool(ctx: RunContext[TeamDependencies], task: str) -> str:
    # 依存性からチームIDを取得
    team_id = ctx.deps.team_id

    # Member Agent実行
    result = await member_agent.run(task, deps=ctx.deps)

    # 依存性にSubmissionを追加
    ctx.deps.submissions.append(
        MemberSubmission(agent_name="research", content=result.output)
    )

    return result.output
```

### Agent実行時に依存性を渡す

```python
# 依存性インスタンス作成
deps = TeamDependencies(team_id="team-001")

# Agent実行
result = await leader_agent.run(
    "市場調査を実施して",
    deps=deps
)

# 依存性に記録されたSubmissionsを取得
for submission in deps.submissions:
    print(f"{submission.agent_name}: {submission.content}")
```

**依存性注入の利点**:
- Agent間でデータを共有
- 型安全なデータアクセス
- テストでのモック化が容易

**参照実装**: `src/mixseek/agents/leader/dependencies.py`

## Message History

Message HistoryはPydantic AI形式のメッセージ履歴です。Leader AgentとMember Agent間のやり取り、ツール実行結果などを記録します。

### Message Historyの構造

```python
from pydantic_ai import ModelMessagesTypeAdapter

# Message HistoryはPydantic AIの内部形式
# - ユーザーメッセージ
# - アシスタントメッセージ
# - ツール実行結果
# - システムメッセージ
```

### Message HistoryのDuckDB永続化

```python
import duckdb
from pydantic_ai import ModelMessagesTypeAdapter

# Message HistoryをJSON形式でDuckDBに保存
conn = duckdb.connect("mixseek.db")

# テーブル作成（JSON型を使用）
conn.execute("""
    CREATE TABLE IF NOT EXISTS round_states (
        team_id VARCHAR,
        round_number INTEGER,
        message_history JSON,  -- ★ ネイティブJSON型
        PRIMARY KEY (team_id, round_number)
    )
""")

# Message Historyを保存
message_history_json = ModelMessagesTypeAdapter.dump_json(result.all_messages())
conn.execute(
    "INSERT INTO round_states VALUES (?, ?, ?)",
    [team_id, round_number, message_history_json]
)
```

### Message Historyの復元

```python
# DuckDBから読み込み
row = conn.execute(
    "SELECT message_history FROM round_states WHERE team_id = ? AND round_number = ?",
    [team_id, round_number]
).fetchone()

# JSONからPydantic AI Message構造に復元
message_history = ModelMessagesTypeAdapter.validate_json(row[0])

# 復元したMessage Historyを使ってAgent実行
result = await agent.run(
    "次のタスク",
    message_history=message_history
)
```

**Message History永続化の目的**:
- 長期実行時のメモリ負荷削減
- ラウンド間での会話履歴の引き継ぎ
- デバッグとトラブルシューティング

**MVCCによる並列書き込み対応**:
- DuckDBはMVCC（Multi-Version Concurrency Control）を採用
- 複数チームが同時にMessage Historyを書き込んでもロック競合を回避

**参照**:
- {term}`Message History`
- {term}`DuckDB`
- {term}`MVCC`

## 実装例

### 完全な実装例: Plain Member Agent

```python
from pydantic_ai import Agent
from mixseek.agents.base import BaseMemberAgent
from mixseek.models.member_agent import (
    MemberAgentConfig,
    MemberAgentResult,
    AgentType
)

class PlainAgent(BaseMemberAgent):
    """Plain Member Agent実装"""

    def __init__(self, config: MemberAgentConfig):
        super().__init__(config)

        # Pydantic AI Agent作成
        self.agent = Agent(
            model=config.model,
            system_prompt=config.instructions.text if config.instructions else None
        )

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> MemberAgentResult:
        """タスクを実行"""
        # Agent実行
        return await self._execute_agent(task, context)

    async def _execute_agent(
        self,
        task: str,
        context: dict[str, Any] | None = None
    ) -> MemberAgentResult:
        """Agent実行（内部メソッド）"""

        start_time = datetime.now(UTC)

        # Pydantic AI Agent実行
        result = await self.agent.run(task)

        end_time = datetime.now(UTC)
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        # Usage記録
        usage = result.usage()
        self.record_usage(usage.total_tokens())

        # 成功結果を返す
        return MemberAgentResult.success(
            content=result.output,
            agent_name=self.agent_name,
            agent_type=self.agent_type.value,
            execution_time_ms=execution_time_ms,
            usage_info={
                "input_tokens": usage.details.get("input_tokens", 0),
                "output_tokens": usage.details.get("output_tokens", 0),
                "requests": usage.requests
            }
        )
```

**参照実装**: `src/mixseek/agents/plain.py`

### 完全な実装例: Leader Agent + Tool登録

```python
from pydantic_ai import Agent, RunContext
from mixseek.agents.leader.config import TeamConfig
from mixseek.agents.leader.dependencies import TeamDependencies

def create_leader_agent(
    team_config: TeamConfig,
    member_agents: dict[str, Agent]
) -> Agent[TeamDependencies, str]:
    """Leader Agent作成"""

    # system_prompt取得
    system_prompt = team_config.leader.system_prompt or DEFAULT_LEADER_SYSTEM_PROMPT

    # Leader Agent作成
    leader_agent = Agent(
        model=team_config.leader.model,
        deps_type=TeamDependencies,
        system_prompt=system_prompt
    )

    # Member Agent Toolを動的登録
    register_member_tools(leader_agent, team_config, member_agents)

    return leader_agent

def register_member_tools(
    leader_agent: Agent[TeamDependencies, str],
    team_config: TeamConfig,
    member_agents: dict[str, Agent]
) -> None:
    """Member Agent Tool登録"""

    for member_config in team_config.members:
        tool_name = member_config.get_tool_name()
        member_agent = member_agents[member_config.agent_name]

        # Toolクロージャー生成
        def make_tool_func(mc, ma):
            async def tool_func(ctx: RunContext[TeamDependencies], task: str) -> str:
                # Member Agent実行（Usage統合）
                result = await ma.run(task, deps=ctx.deps, usage=ctx.usage)

                # Submission記録
                submission = MemberSubmission(
                    agent_name=mc.agent_name,
                    agent_type=mc.agent_type,
                    content=result.output,
                    usage=result.usage(),
                    timestamp=datetime.now(UTC)
                )
                ctx.deps.submissions.append(submission)

                return str(result.output)

            tool_func.__name__ = tool_name
            tool_func.__doc__ = mc.tool_description
            return tool_func

        # Tool登録
        tool = make_tool_func(member_config, member_agent)
        leader_agent.tool(tool)

# 使用例
team_config = TeamConfig.load_from_toml("team.toml")
member_agents = {...}  # Member Agentマップ

leader_agent = create_leader_agent(team_config, member_agents)

# Leader Agent実行
deps = TeamDependencies(team_id="team-001")
result = await leader_agent.run("市場調査を実施して", deps=deps)

# Submissionsを取得
for submission in deps.submissions:
    print(f"{submission.agent_name}: {submission.content}")
```

**参照実装**: `src/mixseek/agents/leader/agent.py`

## まとめ

Pydantic AIの主要な概念:

1. **Agent** - 型安全なエージェント実装
2. **Agent Delegation** - 動的なAgent選択・実行パターン
3. **Tool** - エージェント間通信の仕組み
4. **Usage Limits** - リソース使用量の制限
5. **Run Usage** - リソース使用量の測定
6. **Dependencies** - チーム固有データの依存性注入
7. **Message History** - 会話履歴の永続化と復元

MixSeek-Coreでは、これらの機能を組み合わせて、効率的で柔軟なマルチエージェントシステムを実現しています。

## 関連リソース

- [用語集](../glossary.md)
- Leader Agent実装: `src/mixseek/agents/leader/agent.py`
- Member Agent基底クラス: `src/mixseek/agents/base.py`
- データモデル: `src/mixseek/models/member_agent.py`
