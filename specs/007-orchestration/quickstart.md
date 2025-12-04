# Quickstart: MixSeek-Core Orchestrator

**Date**: 2025-11-05
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

このドキュメントは、MixSeek-Core Orchestratorの使用方法を説明します。

## Prerequisites

- Python 3.13.9以上
- mixseek-coreパッケージがインストール済み
- Google AI APIキー（Gemini使用時）

## Installation

```bash
# uvでインストール（推奨）
uv pip install mixseek-core

# または通常のpipでインストール
pip install mixseek-core
```

## Setup

### 1. 環境変数設定

```bash
# ワークスペース作成
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
mkdir -p $MIXSEEK_WORKSPACE

# API キー設定（Gemini使用時）
export GOOGLE_API_KEY=your-google-api-key

# または OpenAI使用時
export OPENAI_API_KEY=your-openai-api-key
```

### 2. ワークスペース初期化

```bash
# 初期化（設定ファイルのテンプレートを生成）
mixseek init
```

実行後、以下のディレクトリ構造が作成されます:

```
$MIXSEEK_WORKSPACE/
├── configs/
│   ├── orchestrator.toml       # オーケストレータ設定
│   ├── team1.toml               # チーム1設定
│   └── team2.toml               # チーム2設定
├── mixseek.db                   # DuckDBファイル（実行後に自動作成）
└── logs/                        # ログディレクトリ
```

### 3. オーケストレータ設定

`$MIXSEEK_WORKSPACE/configs/orchestrator.toml`を編集:

```toml
[orchestrator]
# チーム単位タイムアウト（秒）
timeout_per_team_seconds = 600

# チーム設定参照
[[orchestrator.teams]]
config = "configs/team1.toml"

[[orchestrator.teams]]
config = "configs/team2.toml"
```

### 4. チーム設定

`$MIXSEEK_WORKSPACE/configs/team1.toml`の例:

```toml
[team]
team_id = "research-team-001"
team_name = "Research Team"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、利用可能なMember Agentから適切なものを選択して実行してください。
"""
temperature = 0.7

# Member Agent設定
[[team.members]]
agent_name = "web-search-agent"
agent_type = "web_search"
tool_description = "Web検索で最新情報を収集します"
model = "google-gla:gemini-2.5-flash-lite"
max_tokens = 6144
timeout = 120

[[team.members]]
agent_name = "analyst"
agent_type = "plain"
tool_description = "論理的な分析・データ解釈を実行します"
model = "google-gla:gemini-2.5-flash-lite"
max_tokens = 2048
```

## Usage

### 基本的な使用方法

```bash
# 最もシンプルな実行
mixseek exec "最新のAI技術トレンドを調査してください"
```

出力例:

```
🚀 MixSeek Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task: 最新のAI技術トレンドを調査してください

🔄 Running 2 teams in parallel...

✅ Team 1: Research Team (completed in 45.2s)
   Score: 0.92
   Feedback: 包括的な調査結果が提供されました。

✅ Team 2: Analysis Team (completed in 38.7s)
   Score: 0.88
   Feedback: 詳細な分析が行われました。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Best Result (Team 1: Research Team, Score: 0.92)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Submissionテキストがここに表示される]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Teams:      2
Completed Teams:  2
Failed Teams:     0
Execution Time:   45.2s

💾 Results saved to DuckDB
```

### カスタム設定ファイルを指定

```bash
mixseek exec "タスク説明" \
  --config workspace/configs/my-orchestrator.toml
```

### タイムアウトを指定

```bash
# 5分（300秒）のタイムアウト
mixseek exec "タスク説明" --timeout 300
```

### JSON出力

```bash
# JSON形式で結果を出力
mixseek exec "タスク説明" --output-format json > result.json

# jqで整形して表示
mixseek exec "タスク説明" --output-format json | jq .
```

### 詳細ログ付き実行

```bash
# 実行中の詳細ログを表示
mixseek exec "タスク説明" --verbose
```

## Programmatic Usage

### Python APIから直接使用

```python
import asyncio
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings

async def main():
    # 設定読み込み
    settings = load_orchestrator_settings(
        Path("workspace/configs/orchestrator.toml")
    )

    # Orchestrator作成
    orchestrator = Orchestrator(settings=settings)

    # 実行
    summary = await orchestrator.execute(
        user_prompt="最新のAI技術トレンドを調査してください",
    )

    # 結果表示
    print(f"完了チーム: {summary.completed_teams}/{summary.total_teams}")
    print(f"最高スコア: {summary.best_score}")

    # 最高スコアチームのSubmission取得
    if summary.best_team_id:
        best_result = next(
            r for r in summary.team_results
            if r.team_id == summary.best_team_id
        )
        print(f"\n{best_result.submission_content}")

if __name__ == "__main__":
    asyncio.run(main())
```

### RoundControllerを直接使用（単一チーム実行）

```python
import asyncio
from pathlib import Path
from mixseek.orchestrator import RoundController

async def main():
    # RoundController作成
    controller = RoundController(
        team_config_path=Path("workspace/configs/team1.toml"),
        workspace=Path("workspace"),
        round_number=1,
    )

    # 1ラウンド実行
    result = await controller.run_round(
        user_prompt="最新のAI技術トレンドを調査してください",
        timeout_seconds=600,
    )

    # 結果表示
    print(f"チーム: {result.team_name}")
    print(f"スコア: {result.evaluation_score}")
    print(f"フィードバック: {result.evaluation_feedback}")
    print(f"\nSubmission:\n{result.submission_content}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### 環境変数未設定エラー

```
Error: MIXSEEK_WORKSPACE environment variable is not set.
```

**解決方法**:

```bash
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace
mkdir -p $MIXSEEK_WORKSPACE
```

### API キーエラー

```
Error: GOOGLE_API_KEY environment variable is not set.
```

**解決方法**:

```bash
export GOOGLE_API_KEY=your-google-api-key
```

### 設定ファイル不在エラー

```
Error: Orchestrator config file not found: workspace/configs/orchestrator.toml
```

**解決方法**:

```bash
# ワークスペース初期化
mixseek init

# または手動で設定ファイルを作成
mkdir -p $MIXSEEK_WORKSPACE/configs
# orchestrator.tomlとチーム設定TOMLを作成
```

### 全チーム失敗

```
Error: All teams failed to complete the task.
```

**解決方法**:

1. `--verbose`オプションで詳細ログを確認
2. チーム設定のモデルとAPIキーを確認
3. タイムアウトを延長（`--timeout 1200`等）

## Next Steps

- [Data Model](./data-model.md): データモデルの詳細
- [API Contracts](./contracts/): APIの詳細仕様
- [Spec](./spec.md): 機能仕様の詳細

## Advanced Configuration

### 複数チームの追加

`orchestrator.toml`に新しいチームを追加:

```toml
[[orchestrator.teams]]
config = "configs/team3.toml"

[[orchestrator.teams]]
config = "configs/team4.toml"
```

### Evaluator設定

オーケストレータは既存のEvaluator実装（src/mixseek/evaluator/）を使用しています。

評価基準やLLMパラメータをカスタマイズするには、ワークスペース内に`configs/evaluator.toml`を配置してください：

```toml
# configs/evaluator.toml
[[metrics]]
name = "ClarityCoherence"
weight = 0.4

[[metrics]]
name = "Coverage"
weight = 0.3

[[metrics]]
name = "Relevance"
weight = 0.3

[llm]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.0
max_tokens = 2000
max_retries = 3
```

詳細は `specs/001-specs/spec.md` の FR-008, FR-009 を参照してください。

### DuckDB結果の確認

```bash
# DuckDBファイルを直接クエリ
duckdb $MIXSEEK_WORKSPACE/mixseek.db

# Leader Boardを確認
SELECT team_name, evaluation_score, created_at
FROM leader_board
ORDER BY evaluation_score DESC
LIMIT 10;

# 実行履歴を確認
SELECT team_name, round_number, created_at
FROM round_history
ORDER BY created_at DESC
LIMIT 10;
```
