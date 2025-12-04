# ADK Research Orchestrator Sample

ADK Research Agent（深層調査エージェント）をオーケストレーションで使用するサンプル。

## 前提条件

- [ADK Research Agent](../custom_agents/adk_research/)のセットアップ完了
- `GOOGLE_API_KEY` 環境変数

## クイックスタート

1. ワークスペースにコピー:
   ```bash
   mkdir -p workspaces && cp -r examples/adk-research-orchestrator-sample workspaces/
   ```

2. 環境変数設定:
   ```bash
   export MIXSEEK_WORKSPACE=$PWD/workspaces/adk-research-orchestrator-sample
   export GOOGLE_API_KEY="your-key"
   ```

3. 実行:
   ```bash
   mixseek exec "AIエージェントフレームワークの最新動向を調査" --config configs/orchestrator.toml
   ```

## チーム構成

| Agent | Type | 役割 |
|-------|------|------|
| adk_researcher | custom | 深層調査（並列検索・統合分析・構造化レポート） |
| web_search | web_search | 補助的なニュース・トレンド検索 |

## 特徴

### メタデータ永続化

`persist_metadata=true` により、各ラウンドの調査結果（ソースURL、構造化レポート）が JSON ファイルに保存されます。

**保存先**: `$MIXSEEK_WORKSPACE/logs/adk_research/`

### 複数ラウンド調査

デフォルトで2ラウンド構成:
1. **Round 1**: 初期調査（概要把握）
2. **Round 2**: 深掘り調査（詳細分析）

### 構造化出力

ADK Research Agent は以下の構造化データを提供:
- エグゼクティブサマリー
- 主要な発見
- パターンとトレンド
- 推奨事項
- 情報源URL一覧

## カスタマイズ

### plugin path の調整（ローカル環境の場合）

デフォルトはDocker環境向けです。ローカル環境で実行する場合は `configs/agents/team-deep-research.toml` を編集:

```toml
# 変更前（Docker環境）
plugin = { path = "/app/examples/custom_agents/adk_research/agent.py", ... }

# 変更後（ローカル環境）
plugin = { path = "examples/custom_agents/adk_research/agent.py", ... }
```

### ラウンド数の調整

`configs/orchestrator.toml` で調整:

```toml
[orchestrator]
max_rounds = 3  # 最大ラウンド数を増やす
```

### 調査視点のカスタマイズ

`configs/agents/team-deep-research.toml` の `researcher_count` で並列リサーチャー数を調整（1-5）:

```toml
tool_settings = { adk_research = { researcher_count = 3, ... } }
```

## メタデータの活用

### ラウンド間でのソース参照

永続化されたメタデータは以下のAPIで取得可能:

```python
from pathlib import Path
from examples.custom_agents.adk_research import ADKResearchAgent

metadata = ADKResearchAgent.load_metadata(
    workspace=Path(os.environ["MIXSEEK_WORKSPACE"]),
    execution_id="exec-123",
    team_id="team-deep-research",
    round_number=1,
)

if metadata:
    sources = metadata.get("sources", [])
    report = metadata.get("structured_report", {})
```

## 関連ドキュメント

- [ADK Research Agent実装詳細](../custom_agents/adk_research/)
- [Orchestrator使用法](../orchestrator-sample/)
