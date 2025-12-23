# Orchestratorガイド - 複数チームの並列実行

MixSeek-Core Orchestratorは、複数のチームを並列実行し、より品質の高いSubmissionを選択する機能を提供します。

## 概要

### オーケストレーションとは

オーケストレーションは、同一タスクに対して複数のチーム（Leader Agent + Member Agents）を並列実行し、評価結果に基づいて最高スコアのSubmissionを選択する機能です。

**主な特徴**:
- 複数チームの並列実行（`asyncio.gather()`使用）
- チーム単位のタイムアウト管理
- 評価スコアに基づくランキング
- 失敗チームの自動隔離
- DuckDBへの全結果記録
- **実行追跡**: 各オーケストレーション実行にUUID（`execution_id`）を自動割り当て

### ユースケース

Orchestratorは以下のような状況で有効です：

- **複数アプローチの競争的評価**: 異なる戦略を持つ複数チームを実行し、最良の結果を選択
- **品質保証**: 複数の実装を並列実行し、最高評価のSubmissionを採用
- **A/Bテスト**: 異なる構成のチームを並列実行し、性能を比較
- **冗長性確保**: 一部のチームが失敗してもシステムが継続動作

### Team実行との違い

| 観点 | Team実行 (`mixseek team`) | Orchestrator実行 (`mixseek exec`) |
|------|--------------------------|----------------------------------|
| 実行単位 | 単一チーム | 複数チーム並列 |
| 設定ファイル | team.toml | orchestrator.toml + 複数のteam.toml |
| 結果 | 1つのSubmission | 最高スコアのSubmission + ランキング |
| 評価 | 1チームの評価 | 全チームの評価とランキング |
| 用途 | チーム開発・デバッグ | 複数チームの競争的実行 |

詳細は [Team Guide](team-guide.md) を参照してください。

## セットアップ

### 環境変数設定

Orchestrator実行には以下の環境変数が必要です：

```bash
# ワークスペースパス（必須）
export MIXSEEK_WORKSPACE=/path/to/workspace

# API認証情報（使用するモデルに応じて設定）
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
export GOOGLE_API_KEY=your_key
```

### ワークスペース初期化

ワークスペースディレクトリ構造：

```text
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── orchestrator.toml          # オーケストレータ設定
│   ├── research-team.toml         # チーム設定1
│   ├── analysis-team.toml         # チーム設定2
│   └── evaluator.toml             # 評価設定（オプション）
├── agents/
│   ├── search_agent.py            # Member Agent実装
│   └── code_exec_agent.py
└── mixseek.db                     # 結果データベース（実行時に自動作成）
```

### オーケストレータ設定ファイル作成

テンプレートから設定ファイルを生成できます：

```bash
# orchestrator.toml テンプレート生成（workspace/configs/orchestrator.toml に出力）
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config init --component orchestrator

# または --workspace オプションで指定
mixseek config init --component orchestrator --workspace /path/to/workspace
```

または、手動で`orchestrator.toml`を作成：

```toml
[orchestrator]
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/research-team.toml"

[[orchestrator.teams]]
config = "configs/analysis-team.toml"
```

**設定項目**:
- `timeout_per_team_seconds`: チーム単位のタイムアウト（秒）
- `teams`: チーム設定ファイルのパスリスト（相対パスまたは絶対パス）

### チーム設定ファイル準備

各チームの設定ファイル（`team.toml`）を準備します。詳細は [Team Guide](team-guide.md) を参照してください。

#### テンプレートから設定ファイルを生成

テンプレートからチーム設定ファイルを生成できます：

```bash
# team.toml テンプレート生成（workspace/configs/team.toml に出力）
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config init --component team

# 生成されたファイルを編集
vim $MIXSEEK_WORKSPACE/configs/team.toml
```

環境変数による設定上書きも可能です：

```bash
# Leader Agentのタイムアウトを環境変数で上書き
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600
mixseek team "タスク" --config team.toml
```

#### 手動でチーム設定ファイルを作成

または、手動で`research-team.toml`を作成：

```toml
[team]
team_id = "research-team-001"
team_name = "Research Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
timeout_seconds = 300
system_instruction = """
タスクを分析し、適切な Member Agent に委譲してください:
- delegate_to_web_search: 最新情報が必要な場合
- delegate_to_code_executor: 計算やデータ処理が必要な場合
"""

[[team.members]]
name = "web_search"
type = "web_search"
tool_description = "Web検索でリアルタイム情報を取得します"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 6144

[team.members.system_instruction]
text = "あなたはWeb検索に特化した研究エージェントです。信頼できる情報源を優先し、最新情報を正確に提供してください。"

[team.members.tool_settings.web_search]
max_results = 15
timeout = 60
include_raw_content = true

[[team.members]]
name = "code_executor"
type = "code_execution"
tool_description = "Pythonコードを実行してデータ処理を行います"
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.0
max_tokens = 4096

[team.members.system_instruction]
text = "あなたは計算とデータ処理に特化したエージェントです。Pythonコードで正確な計算を実行してください。"
```

## 基本的な使い方

### 最もシンプルな実行

```bash
mixseek exec "最新のAI技術トレンドを調査してください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

これにより、以下の処理が実行されます：

1. **タスク配信**: Orchestratorが全チームに同一タスクを配信
2. **実行追跡**: UUID（`execution_id`）を自動生成し、全チームの実行を関連付け
3. **並列実行**: 各チームが独立してLeader Agent → Member Agent → Evaluationを実行
4. **結果集約**: 全チーム完了後、最高スコアチームを特定
5. **リーダーボード表示**: スコア順にランキング表示
6. **DuckDB記録**: 全結果を`execution_id`と共にデータベースに記録

:::{note}
`execution_id`により、複数のオーケストレーション実行を識別し、同一実行に属するチーム結果をグループ化できます。
:::

### 実行フロー

```{mermaid}
graph TD
    A[User: mixseek exec] --> B[Orchestrator]
    B --> C[RoundController 1]
    B --> D[RoundController 2]
    B --> E[RoundController N]
    C --> F[Leader Agent 1]
    D --> G[Leader Agent 2]
    E --> H[Leader Agent N]
    F --> I[Member Agents]
    G --> J[Member Agents]
    H --> K[Member Agents]
    I --> L[Evaluator 1]
    J --> M[Evaluator 2]
    K --> N[Evaluator N]
    L --> O[DuckDB]
    M --> O
    N --> O
    O --> P[ExecutionSummary]
    P --> Q[リーダーボード表示]
```

## 実行オプション

### カスタム設定ファイル指定

```bash
mixseek exec "タスク" --config /path/to/orchestrator.toml
```

相対パスも使用可能：

```bash
mixseek exec "タスク" --config configs/orchestrator.toml
```

### タイムアウト指定

デフォルトのタイムアウトを上書き：

```bash
mixseek exec "タスク" \
  --config orchestrator.toml \
  --timeout 300  # 5分に短縮
```

### JSON出力

JSON形式で結果を出力：

```bash
mixseek exec "タスク" \
  --config orchestrator.toml \
  --output-format json > result.json
```

JSON出力は`ExecutionSummary`モデルのJSON表現です。詳細は [Data Models](api/orchestrator/data-models.md) を参照してください。

### 詳細ログ

詳細なログを表示：

```bash
mixseek exec "タスク" \
  --config orchestrator.toml \
  --verbose
```

## 設定の確認

orchestrator設定ファイルの内容を確認するには、`--config`オプションを使用します。

### 階層的な設定表示

orchestrator → team → member の階層構造を表示：

```bash
# orchestrator.tomlの階層表示（MIXSEEK_WORKSPACE環境変数を使用）
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config show --config orchestrator.toml

# または --workspace オプションで指定
mixseek config show --config orchestrator.toml --workspace /path/to/workspace

# ワークスペース相対パスで指定
mixseek config show --config configs/orchestrator.toml --workspace $MIXSEEK_WORKSPACE
```

**出力例**:
```
[orchestrator] (/path/to/orchestrator.toml)
  environment: dev
  workspace_path: /path/to/workspace
  timeout_per_team_seconds: 600
  max_concurrent_teams: 4
  teams: [...]

  [team 1] (configs/agents/analyst-team-a.toml)
    team_id: team-a
    team_name: チームA: 論理的分析
    max_concurrent_members: 15
    ...

    [member 1]
      name: logical_analyst
      type: plain
      model: google-gla:gemini-2.5-flash-lite
      ...
```

**注意**: `config show` コマンドは `--config` オプションが必須です。`--workspace` オプションは省略可能で、省略時は `MIXSEEK_WORKSPACE` 環境変数を使用します。

### 安全機能

`--config`オプションは以下の安全機能を備えています：

- **循環参照検出**: 設定ファイルの循環参照を検出し、エラーメッセージで参照パスを表示
- **最大深度制限**: 最大10レベルの深さまで読み込み（stack overflow防止）
- **バリデーション**: orchestrator TOMLファイルの構文と構造を検証

詳細は [Configuration Guide](configuration-guide.md) を参照してください。

## 実践例: Web Search を使ったマルチチーム構成

`examples/orchestrator-sample` では、Web Search Agent を含む複数チーム構成の実践的なサンプルを提供しています。

### サンプル構成

このサンプルには5つのチームが含まれています：

| チーム | Temperature | Member Agents | 用途 |
|--------|-------------|---------------|------|
| Team A | 0.3 | なし | 論理的・構造的な分析 |
| Team B | 0.8 | なし | 創造的・革新的な視点 |
| Research Team | 0.3 | Web Search + Logical Analyst | 最新情報の正確な収集と論理的分析 |
| Creative Team | 0.7 | Web Search + Data Analyst | 革新的アイデアとデータ裏付け |
| Balanced Team | 0.5 | Web Search + Logical + Data | 包括的な多角的アプローチ |

### セットアップ

```bash
# サンプルをワークスペースにコピー
cp -rp examples/orchestrator-sample workspaces/
export MIXSEEK_WORKSPACE=workspaces/orchestrator-sample

# API キーを設定
export GOOGLE_API_KEY="your-api-key"
```

### 実行例

```bash
# 5チーム並列実行
mixseek exec "2025年のAI規制動向と企業への影響を分析してください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### 期待される結果

異なるアプローチを持つ5つのチームが並列実行され、それぞれ独自の視点で分析を提供します：

- **Team A & B**: Member Agent なしで、Leader Agent のみが分析
- **Research Team**: Web 検索で最新規制情報を収集し、論理的に分析
- **Creative Team**: Web 検索でトレンドを発見し、データ分析で裏付け
- **Balanced Team**: 3つの Agent を組み合わせ、最も包括的な分析を提供

通常、**Balanced Team** が最高スコアを獲得します（Web 検索、論理分析、データ分析を統合した多角的アプローチのため）。

### Web Search Agent の設定

Web Search Agent を使用する場合の重要な設定項目：

```toml
[[team.members]]
name = "web_search"
type = "web_search"
tool_description = "Web検索で最新情報を収集します"
model = "google-gla:gemini-2.5-flash-lite"  # または anthropic:claude-sonnet-4-5-20250929, openai:gpt-4o
temperature = 0.3
max_tokens = 6144  # Web検索は大量データを処理するため高めに設定

[team.members.system_instruction]
text = "信頼できる情報源を優先し、最新情報を正確に提供してください"

[team.members.tool_settings.web_search]
max_results = 15           # 検索結果の最大数
timeout = 60               # 検索タイムアウト（秒）
include_raw_content = true # 生コンテンツを取得
```

**サポートされるモデル**:
- Google Gemini: `google-gla:gemini-2.5-flash-lite`
- Anthropic Claude: `anthropic:claude-sonnet-4-5-20250929`
- OpenAI: `openai:gpt-4o`

すべてのモデルプロバイダーで Web Search 機能が利用可能です。

### Agent Delegation の動作

Leader Agent は、タスクを分析して必要な Member Agent のみを実行します：

```
User: "2025年のAI規制動向を分析してください"
    ↓
Leader Agent (LLMが分析)
    ↓
必要なToolを選択:
    ├─ delegate_to_web_search    ✅ 実行（最新情報が必要）
    └─ delegate_to_logical_analyst ✅ 実行（分析が必要）
    ↓
各Member Agentが結果を返す
    ↓
Leader Agentが統合して最終結果を生成
```

詳細は `examples/orchestrator-sample/README.md` を参照してください。

## 実行結果の理解

### テキスト出力の構造

```text
🚀 MixSeek Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task: 最新のAI技術トレンドを調査してください

🔄 Running 2 teams in parallel...

✅ Team research-team-001: Research Team (completed in 45.2s)
   Score: 92.00
   Feedback: 包括的な調査結果が提供されました。構造化され、詳細な分析が含まれています。

✅ Team analysis-team-001: Analysis Team (completed in 38.7s)
   Score: 88.00
   Feedback: 詳細な分析が行われました。追加のコンテキストがあればより良くなります。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Best Result (Team research-team-001, Score: 92.00)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[最高スコアチームのSubmission内容]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Leaderboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank  Team                  Score    Status        Tokens
1     Research Team         92.00    ✅ Completed  15,234
2     Analysis Team         88.00    ✅ Completed  12,456

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Teams:      2
Completed Teams:  2
Failed Teams:     0
Execution Time:   45.2s

💾 Results saved to DuckDB
```

### リーダーボードテーブル

リーダーボードには以下の情報が表示されます：

- **Rank**: スコア順の順位
- **Team**: チーム名
- **Score**: 評価スコア（0-100スケール、内部は0.0-1.0で記録）
- **Status**: 実行ステータス（✅ Completed / ❌ Failed）
- **Tokens**: 合計トークン使用量（input + output）

### 最高スコアチーム

最高スコアを獲得したチームのSubmission全文が表示されます。これが最終的な出力として採用される内容です。

### 失敗チームの扱い

失敗したチームは「❌ Failed」として表示され、エラーメッセージが記録されます：

```text
❌ Failed Teams:
   • analysis-team-002: Advanced Analysis Team
     Error: Timeout after 600 seconds
```

失敗チームは最終評価に含まれませんが、DuckDBには記録されます。

## プログラマティックな使用

### Python APIからの使用

```python
import asyncio
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings

async def main():
    # 設定読み込み
    settings = load_orchestrator_settings(
        Path("orchestrator.toml"),
        workspace=Path("/path/to/workspace"),
    )

    # Orchestrator初期化
    orchestrator = Orchestrator(settings=settings)

    # 並列実行
    summary = await orchestrator.execute(
        user_prompt="最新のAI技術トレンドを調査してください",
        timeout_seconds=600,
    )

    # 結果の利用
    print(f"Execution ID: {summary.execution_id}")
    print(f"Total Teams: {summary.total_teams}")
    print(f"Completed: {summary.completed_teams}")
    print(f"Best Team: {summary.best_team_id}")
    print(f"Best Score: {summary.best_score}")

    # 最高スコアチームのSubmission
    best_result = next(
        r for r in summary.team_results
        if r.team_id == summary.best_team_id
    )
    print(f"Submission: {best_result.submission_content}")

    # execution_idによるデータベースクエリ
    # （全チームの結果を同一execution_idでグループ化可能）
    print(f"Results saved with execution_id: {summary.execution_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### ラウンド完了時のコールバック

Orchestratorは`on_round_complete`パラメータを受け付け、各チームの各ラウンド完了時にカスタム処理を実行できます。このコールバックは全チームの全RoundControllerに渡され、ラウンド完了時に呼び出されます。

```python
import asyncio
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings
from mixseek.round_controller import RoundState
from mixseek.agents.leader.models import MemberSubmission

async def on_round_complete(
    round_state: RoundState,
    member_submissions: list[MemberSubmission],
) -> None:
    """各ラウンド完了時に呼び出されるコールバック"""
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

    # Member Agentの結果を処理
    for sub in member_submissions:
        print(f"  - {sub.agent_name}: {sub.status}")

    # カスタム処理（例: 外部サービスへの通知、追加データ保存など）
    # await external_service.notify(round_state)

async def main():
    settings = load_orchestrator_settings(
        Path("orchestrator.toml"),
        workspace=Path("/path/to/workspace"),
    )

    # on_round_completeコールバックを設定
    orchestrator = Orchestrator(
        settings=settings,
        on_round_complete=on_round_complete,
    )

    summary = await orchestrator.execute(
        user_prompt="最新のAI技術トレンドを調査してください",
        timeout_seconds=600,
    )

    print(f"Best Team: {summary.best_team_id} (Score: {summary.best_score})")

if __name__ == "__main__":
    asyncio.run(main())
```

**ユースケース**:
- リアルタイム進捗追跡（UIへの更新通知など）
- カスタムデータ保存（拡張プロジェクト固有のストレージへの保存）
- 外部サービス連携（Slack通知、メトリクス送信など）
- 研究用途（citation情報の収集、search結果の保存など）

**注意事項**:
- コールバック内で例外が発生しても、RoundControllerの実行は継続されます
- 例外は警告ログとして記録されます

### RoundControllerの直接使用

**Note**: RoundControllerは通常Orchestrator経由で使用します。直接使用する場合は、必要なパラメータ（task、evaluator_settings）を自分で準備する必要があります。

```python
import asyncio
from pathlib import Path
from uuid import uuid4
from mixseek.config.manager import ConfigurationManager
from mixseek.orchestrator.models import OrchestratorTask
from mixseek.round_controller import RoundController

async def main():
    workspace = Path("/path/to/workspace")

    # Evaluator設定を取得
    config_manager = ConfigurationManager(workspace=workspace)
    evaluator_settings = config_manager.get_evaluator_settings()

    # OrchestratorTask作成（execution_id含む）
    task = OrchestratorTask(
        user_prompt="最新のAI技術トレンドを調査してください",
        team_configs=[Path("team.toml")],
        timeout_seconds=600,
        max_rounds=3,
        min_rounds=1,
    )

    # RoundController初期化
    controller = RoundController(
        team_config_path=Path("team.toml"),
        workspace=workspace,
        task=task,
        evaluator_settings=evaluator_settings,
        save_db=True,
    )

    # マルチラウンド実行
    result = await controller.run_round(
        user_prompt=task.user_prompt,
        timeout_seconds=600,
    )

    # 結果の利用（LeaderBoardEntry）
    print(f"Execution ID: {result.execution_id}")
    print(f"Team: {result.team_name}")
    print(f"Best Round: {result.round_number}")
    print(f"Score: {result.score}")
    print(f"Submission: {result.submission_content}")
    print(f"Exit Reason: {result.exit_reason}")

if __name__ == "__main__":
    asyncio.run(main())
```

### ラウンド完了時のフック機構（RoundController直接使用時）

RoundControllerを直接使用する場合も、`on_round_complete`パラメータでコールバックを設定できます。Orchestrator経由で使用する場合は、[ラウンド完了時のコールバック](#ラウンド完了時のコールバック)を参照してください。

```python
from mixseek.round_controller import RoundController, RoundState
from mixseek.agents.leader.models import MemberSubmission

async def on_round_complete(round_state: RoundState, member_submissions: list[MemberSubmission]) -> None:
    """ラウンド完了時に呼び出されるフック"""
    print(f"Round {round_state.round_number} completed with score {round_state.evaluation_score}")

controller = RoundController(
    team_config_path=Path("team.toml"),
    workspace=workspace,
    task=task,
    evaluator_settings=evaluator_settings,
    on_round_complete=on_round_complete,
)

result = await controller.run_round(user_prompt, timeout_seconds=600)
```

**コールバック引数**:

| 引数 | 型 | 説明 |
|------|-----|------|
| `round_state` | `RoundState` | ラウンドの状態（スコア、submission内容、タイムスタンプ等） |
| `member_submissions` | `list[MemberSubmission]` | Member Agentの応答リスト（Leaderの最終submissionとは別） |

### 非同期実行の扱い

Orchestratorは完全に非同期設計されています：

```python
import asyncio
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings

async def run_multiple_tasks():
    settings = load_orchestrator_settings(Path("orchestrator.toml"))
    orchestrator = Orchestrator(settings=settings)

    # 複数タスクを並列実行
    tasks = [
        orchestrator.execute("タスク1", timeout_seconds=300),
        orchestrator.execute("タスク2", timeout_seconds=300),
        orchestrator.execute("タスク3", timeout_seconds=300),
    ]

    summaries = await asyncio.gather(*tasks)

    for i, summary in enumerate(summaries, 1):
        print(f"Task {i}: Best Score = {summary.best_score}")
```

## トラブルシューティング

### 環境変数未設定エラー

**エラー**:
```
Error: MIXSEEK_WORKSPACE environment variable is not set.
Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace
```

**解決策**:
```bash
export MIXSEEK_WORKSPACE=/path/to/workspace
```

### 設定ファイルエラー

**エラー**:
```
Error: FileNotFoundError: [Errno 2] No such file or directory: 'orchestrator.toml'
```

**解決策**:
- 設定ファイルパスが正しいか確認
- 相対パスの場合、カレントディレクトリから正しく参照できるか確認
- 絶対パスの使用を推奨

### 全チーム失敗

**症状**: 全チームが「❌ Failed」と表示される

**原因と解決策**:

1. **API認証エラー**:
   - 環境変数が正しく設定されているか確認
   - APIキーが有効か確認

2. **タイムアウト**:
   - `--timeout`オプションで時間を延長
   - タスクの複雑度を考慮してタイムアウトを調整

3. **チーム設定エラー**:
   - 各チームの`team.toml`が正しいか確認
   - Member Agentの参照が正しいか確認

### タイムアウト問題

**症状**: 特定のチームが常にタイムアウトする

**解決策**:

1. **タイムアウト延長**:
   ```bash
   mixseek exec "タスク" --config orchestrator.toml --timeout 1200
   ```

2. **チーム設定の見直し**:
   - Member Agentの数を減らす
   - より高速なモデルを使用

3. **タスクの簡素化**:
   - 複雑なタスクを分割して実行

### DuckDB記録エラー

**症状**: 実行は成功するが「DuckDB記録エラー」が表示される

**解決策**:

1. **ワークスペースの書き込み権限確認**:
   ```bash
   ls -la $MIXSEEK_WORKSPACE/
   ```

2. **DuckDBファイルの整合性確認**:
   ```bash
   duckdb $MIXSEEK_WORKSPACE/mixseek.db "SELECT COUNT(*) FROM leader_board;"
   ```

3. **データベースの再作成**:
   ```bash
   rm $MIXSEEK_WORKSPACE/mixseek.db
   # 次回実行時に自動作成されます
   ```

## 次のステップ

- **[API Reference](api/orchestrator/index.md)** - Orchestrator/RoundController APIの詳細
- **[Data Models](api/orchestrator/data-models.md)** - データモデルの詳細
- **[Team Guide](team-guide.md)** - 単一チーム実行の詳細
- **[Database Schema](database-schema.md)** - DuckDBスキーマとクエリ例
- **[Observability](observability.md)** - Logfireによるリアルタイム観測
