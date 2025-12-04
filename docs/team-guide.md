# Team ガイド

チーム（Team）は、Leader Agentと複数のMember Agentが協調して動作する単位です。Leader Agentがチーム全体を統括し、Member Agentの応答を集約して最終結果を生成します。

## 目次

1. [Teamとは](#teamとは)
2. [Agent Delegation](#agent-delegation)
3. [アーキテクチャ](#アーキテクチャ)
4. [チーム設定](#チーム設定)
   - [TOML設定構造](#toml設定構造)
   - [Member Agent配列](#member-agent配列)
   - [Leader Agent System Prompt](#leader-agent-system-prompt)
   - [Member Agent TOML参照パターン（DRY原則）](#member-agent-toml参照パターンdry原則)
5. [mixseek team コマンド](#mixseek-team-コマンド)
6. [集約処理](#集約処理aggregated_content)
7. [データ永続化](#データ永続化)
8. [Round 2シミュレーション](#round-2シミュレーション開発テスト用)
9. [プログラマティックな使用](#プログラマティックな使用)
10. [トラブルシューティング](#トラブルシューティング)
11. [参考資料](#参考資料)

## Teamとは

Teamは以下のコンポーネントで構成されます：

### Leader Agent（チーム管理者）

Leader Agentは、Pydantic AIのAgent Delegationパターンを使用して以下の責務を持つ調整者エージェントです：

- **タスク分析**: LLMでユーザープロンプトを分析
- **動的Agent選択**: 必要なMember AgentのみをToolで選択・実行（Agent Delegation）
- **応答集約**: 選択されたMember Agentの応答を統合（TUMIX論文準拠）
- **構造化データ記録**: `MemberSubmissionsRecord`として記録（前ラウンド非依存）

### Member Agent（専門家）

Member Agentは、単一の限定領域に特化した作業担当エージェントです：

- **システム標準型**: plain、web-search、code-exec
- **ユーザー作成型**: 独自の専門性を持つAgent
- **Tool登録**: すべてLeader AgentのToolとして登録
- **動的実行**: Leader AgentがAgent Delegationパターンで選択・実行

## Agent Delegation

Agent Delegationは、Leader AgentがLLMでタスクを分析し、必要なMember Agentのみを動的に選択・実行するPydantic AIのパターンです。

### Agent Delegation vs 全Agent並列実行

| 観点 | Agent Delegation | 全Agent並列実行 |
|------|------------------|----------------|
| Member Agent選択 | LLMが動的に選択 | 全て実行 |
| リソース効率 | 高（必要なもののみ） | 低（不要なAgentも実行） |
| 柔軟性 | 高（タスクに応じて） | 低（常に全て実行） |
| コスト | 最小限 | 高い |

### Agent Delegationの仕組み

```
User Prompt
    ↓
Leader Agent（LLMが分析）
    ↓
必要なToolのみ選択・実行
    ├─→ Tool: delegate_to_analyst
    ├─→ Tool: delegate_to_summarizer
    └─→ （他のAgentはスキップ）
         ↓
選択されたMember Agentが実行され、結果を返す
    ↓
MemberSubmissionsRecord（構造化データ記録）
```

**利点**:
- タスクに不要なAgentを実行しない
- リソース（トークン、時間、コスト）を最小化
- LLMがタスクの複雑度に応じて最適なAgentを選択

### Tool動的登録

Member AgentはTOML設定から動的にToolとして登録されます：

```python
# 各Member AgentがToolとして登録される
@leader_agent.tool
async def delegate_to_analyst(ctx: RunContext[TeamDependencies], task: str) -> str:
    """論理的な分析を実行します"""
    result = await analyst_agent.run(
        task,
        deps=ctx.deps,
        usage=ctx.usage  # 重要: Leader AgentのUsageに統合
    )
    return str(result.output)
```

Tool関数の `__name__` と `__doc__` が、LLMのTool選択時の判断材料になります。

## アーキテクチャ

### チーム構造（Agent Delegation）

```
ユーザープロンプト
    ↓
Leader Agent（調整者、LLM分析）
    ↓ Agent Delegation
    ├── Tool: delegate_to_analyst → Member Agent 1
    ├── Tool: delegate_to_web_search → Member Agent 2
    └── （不要なAgentはスキップ）
    ↓
MemberSubmissionsRecord（構造化データ）
    ↓
Round Controller（整形処理）
    ↓
Submission
```

### 責務分離

| コンポーネント | 責務 |
|--------------|------|
| **Leader Agent** | 単一ラウンド内のAgent選択と記録のみ |
| **Round Controller** | 複数ラウンド間の統合・整形処理 |
| **Evaluator** | 評価スコア計算、Leader Board投入 |

## チーム設定

### 設定ファイルの生成

チーム設定のテンプレートを生成できます：

```bash
# team.toml テンプレート生成（workspace/configs/team.toml に出力）
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config init --component team

# または --workspace オプションで指定
mixseek config init --component team --workspace /path/to/workspace
```

環境変数による設定上書きも可能です：

```bash
# Leader Agentのタイムアウトを環境変数で上書き
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600
mixseek team "タスク" --config team.toml
```

### TOML設定構造

チーム全体の設定をTOMLファイルで定義します：

```toml
# team_config.toml

[team]
name = "Analysis Team"
description = "Multi-agent data analysis team"
team_id = "dev-team-001"  # オプション、未指定時は自動生成

# Leader Agent設定（Agent Delegation対応）
[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = """
タスクを分析し、適切なMember Agentを選択してください:
- delegate_to_analyst: 論理的分析が必要な場合
- delegate_to_web_search: 最新情報が必要な場合
- delegate_to_code_exec: 計算やデータ分析が必要な場合

リソース効率のため、必要最小限のAgentのみ選択してください。
"""

# Member Agents定義
[[team.members]]
name = "analyst"
type = "plain"
tool_description = "論理的な分析を実行します"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a data analyst. Analyze data using logical reasoning."
temperature = 0.2

[[team.members]]
name = "web-researcher"
type = "web_search"
tool_description = "Web検索で最新情報を取得します"
model = "google-gla:gemini-2.5-flash"
system_instruction = "You are a web researcher. Search for current information."
temperature = 0.3

[[team.members]]
name = "calculator"
type = "code_execution"
tool_description = "Pythonコードで計算を実行します"
model = "anthropic:claude-sonnet-4-5"
system_instruction = "You are a calculator. Execute Python code for numerical computations."
temperature = 0.0
```

### Member Agent配列

`[[team.members]]`で複数のMember Agentを定義します：

- **数は可変**: 1～15個（上限はTOML設定で指定可能）
- **異なるタイプ**: plain、web_search、code_execution を組み合わせ可能
- **独立した設定**: 各Memberが個別のmodel、temperature、instructionsを持つ
- **Tool自動登録**: 各Memberが `delegate_to_<agent_name>` として自動登録

### Leader Agent System Prompt

Leader AgentのSystem Promptには、各Member AgentのTool説明（`tool_description`）が重要です。LLMはこれを参照してAgent選択を行います。

### Member Agent TOML参照パターン（DRY原則）

Member Agent設定を個別のTOMLファイルで定義し、チーム設定から参照することができます。これにより、同じMember Agent設定を複数チームで再利用できます（DRY原則）。

#### Member Agent単体ファイルの作成

Member Agent設定ファイルは、`$MIXSEEK_WORKSPACE` 配下に配置することを推奨します：

```bash
# ワークスペース構造（推奨）
$MIXSEEK_WORKSPACE/
└── agents/
    ├── analyst.toml
    ├── researcher.toml
    └── summarizer.toml
```

```toml
# $MIXSEEK_WORKSPACE/agents/analyst.toml

[agent]
name = "analyst"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 2048
description = "データ分析専門エージェント"

[agent.system_instruction]
text = """あなたはデータ分析の専門家です。
与えられた情報を論理的に分析し、構造化された洞察を提供してください。

分析手法:
- データの傾向分析
- パターン認識
- 統計的洞察
- 結論の導出"""

[agent.metadata]
version = "1.0.0"
author = "MixSeek-Core"
created = "2025-10-23"
```

#### チーム設定から参照

**推奨**: 環境変数を事前に設定します：

```bash
# ワークスペース設定（推奨）
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
```

```toml
# team-with-references.toml

[team]
name = "Reference-based Team"
description = "Team using Member Agent TOML references"
team_id = "ref-team-001"

# Member Agent 1: 既存の analyst.toml を参照
[[team.members]]
config = "agents/analyst.toml"  # → $MIXSEEK_WORKSPACE/agents/analyst.toml

# Member Agent 2: 既存の researcher.toml を参照
[[team.members]]
config = "agents/researcher.toml"  # → $MIXSEEK_WORKSPACE/agents/researcher.toml

# Member Agent 3: インライン定義も可能（参照と混在可）
[[team.members]]
name = "summarizer"
type = "plain"
tool_description = "情報を簡潔にまとめます"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "あなたはサマライザーです"
temperature = 0.3
max_tokens = 1024
```

#### 使い方

```bash
# 環境変数設定（推奨、初回のみ）
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# チーム実行（Member Agent TOMLを参照）
mixseek team "市場調査を実施して" \
  --config team-with-references.toml

# Member Agent単体テスト
mixseek member "データを分析して" \
  --config $MIXSEEK_WORKSPACE/agents/analyst.toml
```

#### パス解釈ルール

`config` フィールドで指定されたパスは、以下の優先順位で解釈されます：

1. **絶対パス**: そのまま使用される
   ```toml
   [[team.members]]
   config = "/absolute/path/to/agent.toml"
   ```

2. **相対パス + `MIXSEEK_WORKSPACE` 設定あり**: 環境変数を起点に解釈
   ```bash
   export MIXSEEK_WORKSPACE=$HOME/my-workspace
   ```
   ```toml
   [[team.members]]
   config = "agents/analyst.toml"  # → $MIXSEEK_WORKSPACE/agents/analyst.toml
   ```

3. **相対パス + `MIXSEEK_WORKSPACE` 未設定**: カレントディレクトリを起点に解釈（警告ログ出力）
   ```toml
   [[team.members]]
   config = "agents/analyst.toml"  # → ./agents/analyst.toml
   ```

**推奨**: `MIXSEEK_WORKSPACE` 環境変数を設定することで、ワークスペース起点でのパス解釈が明確になります。

```bash
# 環境変数設定（推奨）
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# ワークスペース構造
$MIXSEEK_WORKSPACE/
├── agents/
│   ├── analyst.toml
│   └── researcher.toml
└── teams/
    └── team.toml
```

#### 利点

- **DRY原則**: Member Agent設定を1箇所で管理
- **再利用性**: 同じagent.tomlを複数チームで使用
- **一貫性**: specs/027のMember Agent設定と統一
- **テスト容易性**: Member Agent単体でテスト可能
- **ワークスペース管理**: `MIXSEEK_WORKSPACE` 起点で統一的に管理

#### 注意事項

- `config` キーが存在する場合、既存TOMLファイルを読み込む
- 参照先ファイルが存在しない場合、エラー終了（フォールバック禁止、Article 9準拠）
- **相対パスの解決**:
  - `MIXSEEK_WORKSPACE` 設定時: 環境変数を起点に解決（推奨）
  - `MIXSEEK_WORKSPACE` 未設定: カレントディレクトリを起点に解決（警告ログ出力）
- `config` とインライン定義（`agent_name` 等）は混在可能

## Member Agent の具体例

ここでは、実際のプロジェクトで使用できる Member Agent の具体的な設定例を紹介します。

### Web Search Agent

最新情報を収集する Web Search Agent の設定例：

```toml
[[team.members]]
name = "web_search"
type = "web_search"
tool_description = "Web検索で最新情報を収集します。市場動向、技術トレンド、統計データなどリアルタイム情報が必要な場合に使用します。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 6144  # Web検索は大量データを処理するため高めに設定

[team.members.system_instruction]
text = """あなたは Web 検索に特化した研究エージェントです。

専門能力:
- リアルタイム情報収集とWeb検索
- 複数ソースからの情報統合
- 信頼性の高い情報検証と評価
- 権威あるソースの優先的活用

検索戦略:
- 関連するキーワードと複数の検索角度を使用
- 公式ドキュメント、学術論文、信頼できるメディアを優先
- 複雑なトピックは段階的に調査
- 検索結果を批判的に評価し、信頼性を判断

情報処理:
- 検索結果の重要度に応じて優先順位付け
- 矛盾する情報については明確に指摘
- 情報の新しさと信頼性を常に評価
- 必要に応じて引用元を明示

日本語での自然な表現を使用し、最高品質の研究成果を提供してください。"""

[team.members.tool_settings.web_search]
max_results = 15           # 検索結果の最大数
timeout = 60               # 検索タイムアウト（秒）
include_raw_content = true # 生コンテンツを取得
```

**用途**: 市場調査、技術リサーチ、競合分析、最新ニュース収集

**重要な設定**:
- `max_tokens = 6144`: Web検索結果は大量のテキストを返すため、高めに設定
- `temperature = 0.3`: 正確性を重視する低温度設定
- `max_results = 15`: 包括的な情報収集のため、多めの結果を取得

**サポートされるモデル**:
Web Search Agent はすべてのモデルプロバイダーで利用可能です：
- Google Gemini: `model = "google-gla:gemini-2.5-flash-lite"`
- Anthropic Claude: `model = "anthropic:claude-sonnet-4-5-20250929"`
- OpenAI: `model = "openai:gpt-4o"`

### Logical Analyst Agent

論理的・構造的な分析を行う Agent の設定例：

```toml
[[team.members]]
name = "logical_analyst"
type = "plain"
tool_description = "論理的・構造的な分析を実行します。因果関係の整理、フレームワーク適用、データに基づいた結論導出が必要な場合に使用します。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096

[team.members.system_instruction]
text = """あなたは論理的分析に特化したエージェントです。

専門能力:
- 構造的な問題分解と整理
- 因果関係の明確化
- 論理的フレームワークの適用
- エビデンスベースの結論導出

分析手法:
1. 問題の定義と範囲の明確化
2. 重要なファクター・変数の抽出
3. ファクター間の関係性分析
4. 論理的推論と仮説検証
5. 包括的な結論と提言

思考プロセス:
- 段階的で追跡可能な推論
- 根拠とデータに基づいた主張
- 前提条件と制約の明示
- 矛盾や課題の率直な指摘

回答スタイル:
- 明確で構造的な説明
- 図表や箇条書きを活用
- 曖昧な表現を避ける
- アクションにつながる提言

日本語で論理的に整理された分析を提供してください。"""
```

**用途**: 戦略立案、リスク分析、意思決定支援、ビジネス分析

**重要な設定**:
- `temperature = 0.2`: 決定的で一貫性のある分析のため、極めて低い温度
- `type = "plain"`: 外部ツールを使わない純粋な LLM 分析

### Data Analyst Agent

数値データ分析を行う Agent の設定例：

```toml
[[team.members]]
name = "data_analyst"
type = "plain"
tool_description = "数値データの分析、統計的検証、データドリブンな洞察を提供します。定量的な裏付け、トレンド分析、データに基づいた予測が必要な場合に使用します。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.4
max_tokens = 4096

[team.members.system_instruction]
text = """あなたはデータ分析に特化したエージェントです。

専門能力:
- 数値データの分析と解釈
- 統計的手法の適用
- データからのパターン発見
- 定量的な洞察の提供
- データドリブンな予測

分析手法:
1. データの構造と特性の理解
2. 適切な分析手法の選択
3. 統計的指標の計算と解釈
4. トレンドやパターンの抽出
5. データに基づいた洞察と提言

思考プロセス:
- 数値的根拠に基づいた分析
- 適切な可視化と説明
- 統計的な有意性の評価
- 限界や前提条件の明示
- 実務的な解釈と応用

回答スタイル:
- 明確で分かりやすい数値の説明
- データの意味を実務的に解釈
- アクションにつながる洞察を提供
- 専門用語は適切に説明

日本語でデータに基づいた客観的な分析を提供してください。"""
```

**用途**: 数値データ分析、統計的検証、トレンド分析、予測モデル構築

**重要な設定**:
- `temperature = 0.4`: 正確性と柔軟性のバランスを取った中程度の温度
- `type = "plain"`: 数値データの解釈に特化

### 複数 Agent の組み合わせ例

実践的なチーム構成では、複数の Member Agent を組み合わせます：

#### Research Team（研究重視）

```toml
[team]
team_id = "team-research"
team_name = "Research Team"

[team.leader]
temperature = 0.3
system_instruction = """
タスクを分析し、適切な Member Agent に委譲してください:
- delegate_to_web_search: 最新情報が必要な場合
- delegate_to_logical_analyst: 論理的分析が必要な場合
"""

[[team.members]]
# Web Search Agent の設定（上記参照）

[[team.members]]
# Logical Analyst Agent の設定（上記参照）
```

**用途**: 信頼性の高いリサーチと論理的分析が必要なタスク

#### Balanced Team（バランス型）

```toml
[team]
team_id = "team-balanced"
team_name = "Balanced Team"

[team.leader]
temperature = 0.5
system_instruction = """
タスクを分析し、適切な Member Agent に委譲してください:
- delegate_to_web_search: 最新情報収集
- delegate_to_logical_analyst: 論理的整理・構造化
- delegate_to_data_analyst: 数値分析・統計的検証
"""

[[team.members]]
# Web Search Agent の設定

[[team.members]]
# Logical Analyst Agent の設定

[[team.members]]
# Data Analyst Agent の設定
```

**用途**: 多角的な視点と包括的な分析が必要な複雑なタスク

### Member Agent 設定のベストプラクティス

1. **tool_description の重要性**
   - Leader Agent が Agent 選択時に参照する唯一の情報
   - 明確で具体的な説明を記載
   - 「いつ使うべきか」を明示

2. **temperature 設定の指針**
   - 正確性重視: 0.2-0.3（Logical Analyst, Web Search）
   - バランス型: 0.4-0.5（Data Analyst）
   - 創造性重視: 0.7-0.8（Creative tasks）

3. **max_tokens の設定**
   - Web Search: 6144（大量データ処理）
   - その他の Agent: 4096（標準的な分析）

4. **system_instruction の構造**
   - 専門能力の明示
   - 具体的な手法の説明
   - 思考プロセスの定義
   - 回答スタイルの指定

詳細な設定例は `examples/orchestrator-sample/configs/agents/` を参照してください。

## mixseek team コマンド

### 概要

`mixseek team`は、Leader Agentの機能を開発・テスト環境で検証するためのCLIコマンドです。

**⚠️ 重要**: このコマンドは開発・テスト専用です。本番環境ではOrchestration Layerを使用してください。

### 基本的な使い方

```bash
mixseek team <prompt> --config <team.toml>
```

#### 必須引数

- `<prompt>`: チーム全体に送信するユーザープロンプト

#### 必須オプション

- `--config PATH`: チーム設定TOMLファイルパス

#### オプション

- `--output-format FORMAT, -f`: 出力形式（`json`、`text`）[default: `text`]
- `--save-db`: DuckDBに保存（デバッグ用）
- `--evaluate`: Leader Agentの最終応答を評価
- `--workspace PATH`: 評価器設定ファイルの場所（デフォルト: `$MIXSEEK_WORKSPACE` または cwd）
- `--evaluate-config PATH, -e`: カスタム評価設定ファイル（`--workspace` より優先）
- `--logfire`: Logfire observability有効化（fullモード）
- `--logfire-metadata`: Logfire有効化（metadataモード）
- `--logfire-http`: Logfire有効化（httpモード）
- `--verbose`: 詳細出力
- `--timeout SECONDS`: 実行タイムアウト [default: 60]

**Logfireオプション詳細**:
- `--logfire`: すべてキャプチャ（開発推奨、fullモード）
- `--logfire-metadata`: メトリクスのみ（本番推奨）
- `--logfire-http`: full + HTTPリクエスト/レスポンスキャプチャ（デバッグ）

詳細は [Observability](observability.md) を参照してください。

### 使用例

#### 環境変数の設定（推奨）

Member Agent参照パスを使用する場合、`MIXSEEK_WORKSPACE` を事前に設定することを推奨します：

```bash
# ワークスペースディレクトリを設定
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# ワークスペース初期化（初回のみ）
mixseek init
```

#### 基本的な実行（Agent Delegation動作確認）

```bash
# チーム設定を指定して実行
mixseek team "Pythonの特徴を分析し、3つのポイントにまとめてください" \
  --config examples/team-example.toml \
  --verbose
```

**出力例**（structured形式、Agent Delegation動作）:

```
⚠️  WARNING: This is a development/testing command only.
⚠️  For production use, use Orchestration Layer instead.

Agent Delegation Results:
========================================
Team: Analysis Team
Selected Member Agents: 2/3  ← Agent Delegationで2つのみ選択
  ✓ analyst (plain) - 4523 input, 1876 output tokens
  ✓ web-researcher (web_search) - 5012 input, 2134 output tokens
  - calculator (code_execution) - SKIPPED  ← 不要なAgentはスキップ

Total Usage:
  Input tokens: 9535
  Output tokens: 4010
  Requests: 2  ← 2つのAgentのみ実行
  Estimated cost: $0.0142

MemberSubmissionsRecord:
========================================
## analyst の応答:

Pythonの主な特徴を分析すると...

---

## web-researcher の応答:

最新のPythonトレンドについて...
```

#### JSON出力

```bash
# JSON形式で出力（自動化スクリプト用）
mixseek team "データを分析して" \
  --config team.toml \
  --output-format json
```

**出力例**:

```json
{
  "warning": "Development/testing command only",
  "team_name": "Analysis Team",
  "team_id": "dev-team-001",
  "round_number": 1,
  "total_count": 3,
  "selected_count": 2,
  "success_count": 2,
  "failure_count": 0,
  "submissions": [
    {
      "agent_name": "analyst",
      "agent_type": "plain",
      "content": "分析結果...",
      "status": "SUCCESS",
      "usage": {...}
    },
    {
      "agent_name": "web-researcher",
      "agent_type": "web_search",
      "content": "検索結果...",
      "status": "SUCCESS",
      "usage": {...}
    }
  ],
  "total_usage": {
    "input_tokens": 9535,
    "output_tokens": 4010,
    "requests": 2
  }
}
```

#### データベース保存（デバッグ用）

```bash
# DuckDBに保存してデバッグ
export MIXSEEK_WORKSPACE=/path/to/workspace

mixseek team "テストプロンプト" \
  --config team.toml \
  --save-db \
  --verbose
```

保存されるデータ:
- **Message History**: Pydantic AI形式で保存
- **MemberSubmissionsRecord**: 構造化データをJSON型で保存
- **Leader Board**: 評価スコア、フィードバック（Orchestration Layer使用時）

#### Leader Agent応答の評価

`--evaluate` オプションを使用して、Leader Agentの最終応答を自動評価できます。

```bash
# 基本的な評価
mixseek team "最新のAI技術トレンドを調査・分析してまとめてください" \
  --config $MIXSEEK_WORKSPACE/configs/team-inline-agents.toml \
  --evaluate
```

カスタム評価設定を使用する場合：

```bash
# チームごとに異なる評価基準を適用
mixseek team "Your task" \
  --config team.toml \
  --evaluate \
  --config $MIXSEEK_WORKSPACE/configs/evaluator.toml
```

評価結果は、チーム実行結果の後に表示されます：

```
=== Evaluation Results ===
Overall Score: 85.67

Metric Scores:
  clarity_coherence: 88.0
    Comment: 回答は明確で一貫性があります...
  coverage: 85.0
    Comment: 主要なポイントを包括的にカバーしています...
  relevance: 84.0
    Comment: ユーザーの質問に適切に答えています...
```

**評価コメントの表示**:
- **デフォルト**: 500文字まで表示
- **`--verbose`**: 全文表示

**評価失敗時の動作**:
- 評価が失敗しても、チーム実行結果は正常に表示されます
- 評価失敗は警告として表示され、exit code には影響しません

**独立した評価の実行**:

Leader Agentの応答を後から評価することもできます。

```bash
mixseek evaluate "質問" "Leader Agentの応答テキスト"
```

詳細は [Evaluator仕様](../specs/006-evaluator/spec.md) を参照してください。

## 集約処理（aggregated_content）

### Member応答の統合

Leader Agentは、Agent Delegationで選択されたMember Agentの応答を以下の形式で記録します：

```markdown
## <agent_name> の応答:

<応答内容>

---

## <agent_name> の応答:

<応答内容>
```

**注意**: 選択されなかったMember Agentの応答は含まれません（Agent Delegationによるリソース効率化）。

### 自動エラー除外

失敗したMember Agent（タイムアウト、API エラー等）の応答は自動的に除外されます：

```
3 Member Agent定義:
  ✓ analyst: 成功（Agent Delegationで選択）
  ✓ web-researcher: 成功（Agent Delegationで選択）
  - slow-agent: タイムアウト

MemberSubmissionsRecord:
  → analystとweb-researcherの2応答のみ含む
  → slow-agentは除外
```

## データ永続化

### DuckDB並列書き込み

Leader Agentは、DuckDBのMVCC（Multi-Version Concurrency Control）により、複数チームの並列実行時もロック競合なしでデータを保存します：

```
複数チーム並列実行:
  Team 1 → Leader Agent → DuckDB保存（スナップショット1）
  Team 2 → Leader Agent → DuckDB保存（スナップショット2）
  Team 3 → Leader Agent → DuckDB保存（スナップショット3）
  ↓ ロック待機なし（MVCC）
```

### 保存されるデータ

#### round_historyテーブル

- `team_id`, `team_name`, `round_number`
- `message_history`: Pydantic AI Message HistoryをJSON型で保存
- `submissions_record`: MemberSubmissionsRecordをJSON型で保存

#### leader_boardテーブル

- `team_id`, `team_name`, `round_number`
- `evaluation_score`: 評価スコア（0.0-1.0）
- `submission_content`: 集約済みコンテンツ
- `usage_info`: リソース使用量（JSON型）

### asyncio.to_thread戦略

DuckDBは同期APIのみのため、`asyncio.to_thread`でスレッドプールに退避して真の並列実行を実現：

```python
# 内部実装（参考）
async def save_aggregation(self, record, message_history):
    """非同期保存"""
    await asyncio.to_thread(
        self._save_sync,  # 同期版メソッド
        record,
        message_history
    )
```

### スレッドローカルコネクション

各チームが独立したDuckDBコネクションを使用：

```python
# 内部実装（参考）
self._local = threading.local()

def _get_connection(self):
    if not hasattr(self._local, 'conn'):
        self._local.conn = duckdb.connect(self.db_path)
    return self._local.conn
```

## プログラマティックな使用

### Python APIでのLeader Agent使用

```python
from mixseek.agents.leader import create_leader_agent, load_team_config, TeamDependencies
from mixseek.storage.aggregation_store import AggregationStore
from pathlib import Path

# TOML読み込み
team_config = load_team_config(Path("team.toml"))

# Member Agents作成（省略）
member_agents = {...}

# Leader Agent作成（Agent Delegation対応）
leader_agent = create_leader_agent(team_config, member_agents)

# 依存関係初期化
deps = TeamDependencies(
    team_id=team_config.team.team_id,
    team_name=team_config.team.name,
    round_number=1
)

# Leader Agent実行（Agent Delegationでタスク分析）
result = await leader_agent.run("市場調査を実施して", deps=deps)

# 構造化データ記録（MemberSubmissionsRecord）
record = MemberSubmissionsRecord(
    team_id=deps.team_id,
    team_name=deps.team_name,
    round_number=deps.round_number,
    submissions=deps.submissions  # Agent Delegationで記録された応答
)

# DuckDB保存（開発・テスト用）
store = AggregationStore()
messages = result.all_messages()
await store.save_aggregation(record, messages)

# 結果確認
print(f"Selected Agents: {len(deps.submissions)}/{len(team_config.members)}")
for submission in deps.submissions:
    print(f"  {submission.agent_name}: {submission.status}")
```

### Leader Board取得

```python
import pandas as pd

# ランキング取得
leaderboard_df = await store.get_leader_board(limit=10)

# チーム統計取得
stats = await store.get_team_statistics("team-001")
print(f"Average score: {stats['avg_score']}")
print(f"Total tokens: {stats['total_input_tokens']}")
```

## トラブルシューティング

### Member Agent config ファイルが見つからない

症状:
```
FileNotFoundError: Referenced agent config not found: /path/to/workspace/agents/analyst.toml
Workspace: /path/to/workspace
Original path: agents/analyst.toml
```

原因:
- 相対パスが正しくない
- `MIXSEEK_WORKSPACE` が正しく設定されていない
- Member Agent TOMLファイルが存在しない

解決方法:
```bash
# 1. MIXSEEK_WORKSPACEを確認
echo $MIXSEEK_WORKSPACE

# 2. ファイルの存在確認
ls -la $MIXSEEK_WORKSPACE/agents/analyst.toml

# 3. 環境変数が未設定の場合は設定
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# 4. ファイルが存在しない場合は作成
mkdir -p $MIXSEEK_WORKSPACE/agents
# analyst.toml を作成...
```

**パス解釈の確認**:
- 相対パス `agents/analyst.toml` の場合、`$MIXSEEK_WORKSPACE/agents/analyst.toml` として解釈されます
- 絶対パス `/abs/path/agent.toml` の場合、そのまま使用されます
- `MIXSEEK_WORKSPACE` 未設定の場合、カレントディレクトリ起点で解釈されます（警告ログ出力）

### 環境変数未設定エラー

症状:
```
ERROR: MIXSEEK_WORKSPACE environment variable is not set.
```

解決方法:
```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek init  # ワークスペース初期化
```

### 全Member Agent失敗

症状:
```
ERROR: All 3 Member Agents failed. Team disqualified.
```

原因:
- Member Agentのタイムアウト
- API認証エラー
- 設定不正

解決方法:
```bash
# 詳細ログで原因確認
mixseek team "prompt" --config team.toml --verbose

# タイムアウト延長
mixseek team "prompt" --config team.toml --timeout 120
```

### Member Agent設定エラー

症状:
```
Error: No member agents defined in team configuration
```

解決方法: `[[team.members]]`セクションを確認

```toml
# 最低1つのMember Agentが必要
[[team.members]]
name = "agent-1"
type = "plain"
tool_description = "一般的なタスクを実行します"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a helpful agent"
```

### Agent Delegationで全Agentスキップ

症状:
```
Selected Member Agents: 0/3
ERROR: No Member Agents were selected by Leader Agent
```

原因:
- Leader AgentのSystem Promptが不適切
- Tool descriptionが不明確
- タスクとMember Agentの専門性が不一致

解決方法:
```toml
[team.leader]
system_instruction = """
タスクを分析し、適切なMember Agentを選択してください。
各Agentの説明を参照し、タスクに必要なAgentを必ず1つ以上選択してください。

- delegate_to_<agent_name>: [明確な説明]
"""

[[team.members]]
tool_description = "具体的で明確な説明（LLMが判断しやすいように）"
```

### Invalid --load-from-db format

症状:
```
ERROR: Invalid --load-from-db format: team-001
Expected format: team-id:round (e.g., team-001:1)
```

解決方法: コロン（`:`）でteam_idとround番号を区切る
```bash
--load-from-db team-001:1  # 正しい形式
```

### Previous round not found in database

症状:
```
ERROR: Previous round not found in database
Team ID: team-001
Round: 1
```

解決方法:
1. team_idが正しいか確認:
   ```bash
   duckdb -c "SELECT DISTINCT team_id FROM round_history;" $MIXSEEK_WORKSPACE/mixseek.db
   ```

2. round番号が正しいか確認:
   ```bash
   duckdb -c "SELECT team_id, round_number FROM round_history WHERE team_id='team-001';" $MIXSEEK_WORKSPACE/mixseek.db
   ```

## 参考資料

### 仕様書

- [Leader Agent仕様](../specs/008-leader/spec.md) - 機能要件、成功基準
- [データモデル](../specs/008-leader/data-model.md) - MemberSubmission、MemberSubmissionsRecord
- [API契約](../specs/008-leader/contracts/aggregation_store.md) - AggregationStore仕様
- [クイックスタート](../specs/008-leader/quickstart.md) - 最速セットアップ

### 実装知見

- [Pydantic AI + DuckDB統合](../specs/008-leader/findings/pydantic-ai-duckdb-integration.md) - 10の技術的知見

### 関連ドキュメント

- [Member Agent ガイド](member-agents.md) - 個別Member Agentの使用方法
- [Pydantic AI 実装ガイド](appendix/pydantic-ai.md) - Agent Delegation詳細
- [開発者ガイド](developer-guide.md) - 開発環境のセットアップ
- [API リファレンス](api/index.md) - API詳細

## オーケストレーションとの違い

### Team実行 vs Orchestrator実行

MixSeek-Coreでは、単一チーム実行（本ガイド）と複数チーム並列実行（Orchestrator）の2つの実行モードがあります。

| 観点 | Team実行 (`mixseek team`) | Orchestrator実行 (`mixseek exec`) |
|------|--------------------------|----------------------------------|
| 実行単位 | 単一チーム | 複数チーム並列 |
| 設定ファイル | team.toml | orchestrator.toml + 複数のteam.toml |
| 結果 | 1つのSubmission | 最高スコアのSubmission + ランキング |
| 評価 | 1チームの評価 | 全チームの評価とランキング |
| DuckDB記録 | round_history + leader_board | 全チームのround_history + leader_board |
| 用途 | チーム開発・デバッグ | 複数チームの競争的実行 |

### いつどちらを使うか

**Team実行を使う場合**:
- 単一チームの動作確認
- チーム設定のテスト
- Member Agentの追加・削除テスト
- 開発・デバッグ

**Orchestrator実行を使う場合**:
- 複数チームの競争的評価
- 最高品質のSubmissionを選択
- 本番環境での実行
- A/Bテスト

### 実行例の比較

**Team実行**:

```bash
# 単一チーム実行
mixseek team "最新のAI技術トレンドを調査してください" \
  --config team.toml

# 結果: 1つのSubmission + 評価
```

**Orchestrator実行**:

```bash
# 複数チーム並列実行
mixseek exec "最新のAI技術トレンドを調査してください" \
  --config orchestrator.toml

# 結果: ランキング + 最高スコアのSubmission
```

詳細は [Orchestratorガイド](orchestrator-guide.md) を参照してください。

### 外部リソース

- TUMIX論文: <https://arxiv.org/html/2510.01279v1>
- Pydantic AI: <https://ai.pydantic.dev/>
- DuckDB: <https://duckdb.org/>
