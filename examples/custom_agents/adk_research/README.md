# Google ADK リサーチエージェントサンプル

Google ADK（Agent Development Kit）を使用したカスタムメンバーエージェントの実装サンプルです。外部 AI フレームワークを MixSeek-Core の`BaseMemberAgent`インターフェースに統合する手法を実証するために作成されました。

## 主な機能

- **単一検索モード**：`google_search`ツールによる迅速なウェブ検索と要約機能
- **深堀調査モード**：複数の視点を考慮した並列的な調査パイプラインと統合処理
- **出典追跡機能**：メタデータ内に自動的に抽出・記録される情報源 URL の追跡機能
- **構造化エラー処理**：ユーザーフレンドリーな説明付きのエラー分類機能

## 実行モードの詳細

### 単一検索モード（Single Search）

`deep_research=False` を指定した場合、1 つの LlmAgent と`google_search`ツールを使用して迅速な検索・要約を実行します。

**特徴**:

- 低レイテンシ（目標: 10 秒以内）
- シンプルなクエリに最適
- 単一の視点からの情報収集

**使用例**:

```python
result = await agent.execute("Pythonとは何ですか？", deep_research=False)
```

### 深堀調査モード（Deep Research）

`deep_research=True`（デフォルト）を指定した場合、複数の並列リサーチャーと統合エージェントによるパイプライン処理を実行します。

**5 つの並列リサーチャーの視点**:

1. **技術的側面と実装詳細** - 技術仕様、アーキテクチャ、実装方法
2. **市場トレンドと業界分析** - 市場動向、競合状況、業界への影響
3. **課題・制限・将来方向** - 現在の制限、課題、将来の展望
4. **ユースケースと実例** - 実際の適用例、成功事例、ベストプラクティス
5. **競合状況と代替アプローチ** - 代替技術、比較分析

**パイプライン構造**:

```
ParallelAgent (parallel_research)
├── researcher_1 (技術的側面)
├── researcher_2 (市場トレンド)
├── researcher_3 (課題・将来方向)
├── researcher_4 (ユースケース)
└── researcher_5 (競合状況)
         ↓
SequentialAgent → Summarizer (統合・要約)
```

**使用例**:

```python
result = await agent.execute(
    "AIエージェントフレームワークの最新動向を調査してください",
    deep_research=True  # デフォルト
)
print(f"情報源数: {result.metadata['source_count']}")
```

## 出力形式の詳細

### MemberAgentResult の構造

実行結果は`MemberAgentResult`オブジェクトとして返されます。

| フィールド          | 型                  | 説明                           |
| ------------------- | ------------------- | ------------------------------ |
| `status`            | `ResultStatus`      | SUCCESS / ERROR                |
| `content`           | `str`               | Markdown 形式のレポート本文    |
| `agent_name`        | `str`               | エージェント名                 |
| `agent_type`        | `str`               | "custom"                       |
| `execution_time_ms` | `int`               | 実行時間（ミリ秒）             |
| `metadata`          | `dict[str, Any]`    | 詳細メタデータ（下記参照）     |
| `error_code`        | `str \| None`       | エラー時のコード               |

### metadata の構造

```python
{
    "mode": "deep_research",           # "single_search" | "deep_research"
    "model": "gemini-2.5-flash",       # 使用したGeminiモデル
    "sources": [                       # SearchResult配列
        {
            "url": "https://example.com/article",
            "title": "記事タイトル",
            "snippet": "",
            "timestamp": "2025-01-01T12:00:00Z"
        }
    ],
    "source_count": 10,                # ソース数
    "structured_report": { ... }       # structured_output=true時のみ
}
```

### ResearchReport の構造（構造化出力）

`structured_output=true`（デフォルト）の場合、`metadata["structured_report"]`に以下の構造が含まれます：

```python
{
    "executive_summary": "調査結果の概要...",
    "key_findings": [
        "発見1: LLMはマルチモーダル化が進んでいる",
        "発見2: エージェントフレームワークが進化している"
    ],
    "patterns": [
        "パターン1: AI機能の統合が進んでいる"
    ],
    "recommendations": [
        "推奨1: マルチエージェントアーキテクチャの採用を検討"
    ],
    "sources": [ ... ]
}
```

**Gemini JSON モードによる構造化出力**:

構造化出力は Gemini の JSON モード（`response_mime_type="application/json"`）を使用して生成されます。これにより、LLM が直接 JSON 形式で出力するため、以下のメリットがあります：

- **高い信頼性**: スキーマに準拠した出力が保証される
- **パース失敗なし**: 正規表現パースに依存しないため、出力形式の変動に影響されない
- **型安全性**: Pydantic モデルによる自動検証

## チーム/オーケストレーション連携

### メタデータ永続化

`persist_metadata=true`を設定すると、実行結果のメタデータが JSON ファイルに保存されます。

**保存先**: `$MIXSEEK_WORKSPACE/logs/adk_research/`

**ファイル命名規則**:

- チーム実行時: `{execution_id}_{team_id}_{round}.json`
- 単独実行時: `adk_research_{timestamp}.json`

**TOML 設定例**:

```toml
[agent.metadata.tool_settings.adk_research]
persist_metadata = true
```

### load_metadata() ユーティリティ

team/orchestration 実行後にメタデータを取得するためのスタティックメソッドです。

```python
from pathlib import Path
from examples.custom_agents.adk_research import ADKResearchAgent

# team実行後のメタデータ取得
metadata = ADKResearchAgent.load_metadata(
    workspace=Path("/path/to/workspace"),
    execution_id="exec-123",
    team_id="team-1",
    round_number=1,
)

if metadata:
    sources = metadata.get("sources", [])
    structured_report = metadata.get("structured_report", {})
    print(f"取得した情報源: {len(sources)}件")
```

## デバッグモード

`debug_mode=true`を設定すると、ADK イベントと grounding データの詳細ログが標準ロギングシステムに出力されます。

### 設定

```toml
[agent.metadata.tool_settings.adk_research]
debug_mode = true
```

### ログレベルの制御

デバッグ情報を確認するには、`--log-level debug`オプションを使用します：

```bash
# コンソールとファイルにデバッグログを出力
mixseek member --config adk_research.toml --log-level debug "検索クエリ"

# ログファイルの確認
cat $MIXSEEK_WORKSPACE/logs/mixseek.log | grep "ADK debug"
```

### Logfire 統合

Logfire が有効な場合、デバッグ情報は自動的にスパンとして記録されます：

```bash
# Logfire 統合でリアルタイム観測
mixseek member --config adk_research.toml --log-level debug --logfire "検索クエリ"
```

### 出力内容

デバッグログには以下の情報が含まれます：

- ADK イベント数とイベントダンプ
- セッション状態のキー一覧
- grounding_metadata の内容（情報源 URL など）

**用途**:

- google_search ツールの動作確認
- grounding_metadata の抽出状況の検証
- ADK イベントフローのトラブルシューティング

## 前提条件

### 1. API Key

Set the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### 2. 依存関係

The `google-adk` package is required. Install with:

```bash
uv sync --extra adk
```

### 3. 対応モデル

`google_search`ツールでは以下の Gemini 2.0 以降のモデルを使用できます：

- `gemini-2.5-flash`（デフォルト推奨）
- `gemini-2.5-flash-lite`
- `gemini-2.5-pro`
- `gemini-2.0-flash`
- `gemini-3-pro-preview`

## クイックスタート

### カスタムメンバーエージェントとしての使用方法

1. TOML 設定ファイルを作業スペースにコピーします：

```bash
cp examples/custom_agents/adk_research/adk_research_agent.toml \
   $MIXSEEK_WORKSPACE/configs/
```

2. TOML ファイル内のプラグインパスを、ご自身の環境に合わせて更新してください。

3. CLI から実行します：

```bash
mixseek member --config $MIXSEEK_WORKSPACE/configs/adk_research_agent.toml \
  "AIエージェントの最新トレンドは何ですか？"
```

### Python を直接使用する場合

```python
import asyncio
from examples.custom_agents.adk_research import ADKResearchAgent
from mixseek.models.member_agent import (
    MemberAgentConfig,
    PluginMetadata,
)

# Create configuration
config = MemberAgentConfig(
    name="my-research-agent",
    type="custom",
    model="google-gla:gemini-2.5-flash",
    system_instruction="You are a research assistant.",
    plugin=PluginMetadata(
        path="examples/custom_agents/adk_research/agent.py",
        agent_class="ADKResearchAgent",
    ),
    metadata={
        "tool_settings": {
            "adk_research": {
                "gemini_model": "gemini-2.5-flash",
                "temperature": 0.7,
                "max_output_tokens": 4096,
                "search_result_limit": 10,
                "researcher_count": 3,
                "timeout_seconds": 30,
            }
        }
    },
)

# Create and use agent
async def main():
    agent = ADKResearchAgent(config)

    # Single search mode (default)
    result = await agent.execute("What is Python programming language?")
    print(result.content)

    # Deep Research mode
    result = await agent.execute(
        "Compare Python vs JavaScript for web development",
        deep_research=True
    )
    print(result.content)
    print(f"Sources: {result.metadata['source_count']}")

    await agent.cleanup()

asyncio.run(main())
```

## 設定リファレンス

### TOML 設定ファイル

```toml
[agent]
type = "custom"
name = "adk-research-agent"
model = "google-gla:gemini-2.5-flash"
temperature = 0.7
max_tokens = 4096
description = "Google ADK Deep Research Agent"

[agent.system_instruction]
text = "You are a research assistant..."

[agent.plugin]
path = "/app/examples/custom_agents/adk_research/agent.py"
agent_class = "ADKResearchAgent"

[agent.metadata.tool_settings.adk_research]
gemini_model = "gemini-2.5-flash"
temperature = 0.7
max_output_tokens = 4096
search_result_limit = 10
researcher_count = 3
timeout_seconds = 30
```

### Configuration Options

| Option                      | Type   | Default            | Description                                             |
| --------------------------- | ------ | ------------------ | ------------------------------------------------------- |
| `gemini_model`              | string | `gemini-2.5-flash` | Gemini model for ADK agents                             |
| `temperature`               | float  | `0.5`              | Generation temperature (0.0-2.0)                        |
| `max_output_tokens`         | int    | `8192`             | Maximum tokens per response                             |
| `search_result_limit`       | int    | `15`               | Max search results to process                           |
| `researcher_count`          | int    | `5`                | Parallel researchers for Deep Research (1-5)            |
| `timeout_seconds`           | int    | `120`              | Request timeout                                         |
| `deep_research_default`     | bool   | `true`             | Enable Deep Research mode by default                    |
| `structured_output`         | bool   | `true`             | Enable structured output (ResearchReport) in metadata   |
| `debug_mode`                | bool   | `false`            | Enable debug logging via standard logging (use --log-level debug) |
| `persist_metadata`          | bool   | `false`            | Persist metadata to JSON for team/orchestration access  |
| `append_sources_to_content` | bool   | `true`             | Append sources section to markdown content for UI       |

## Error Code Reference

| Code                | Description             | Troubleshooting                             |
| ------------------- | ----------------------- | ------------------------------------------- |
| `AUTH_ERROR`        | Invalid/missing API key | Check `GOOGLE_API_KEY` environment variable |
| `RATE_LIMIT`        | Gemini API rate limit   | Wait and retry, check quota                 |
| `TIMEOUT`           | Request timeout         | Increase `timeout_seconds` in config        |
| `NETWORK_ERROR`     | Network connectivity    | Check internet connection                   |
| `SEARCH_NO_RESULTS` | No search results       | Refine the query                            |
| `PIPELINE_ERROR`    | ADK pipeline failure    | Check agent configuration                   |
| `CONFIG_ERROR`      | Configuration error     | Verify TOML settings                        |

## Architecture

```
ADKResearchAgent
├── Single Search Mode
│   └── LlmAgent (researcher)
│       └── google_search tool
│
└── Deep Research Mode
    └── SequentialAgent (pipeline)
        ├── ParallelAgent (parallel_research)
        │   ├── LlmAgent (researcher_1) - Technical focus
        │   ├── LlmAgent (researcher_2) - Market focus
        │   └── LlmAgent (researcher_3) - Future focus
        │
        └── LlmAgent (summarizer)
```

## テスト

テストはプロジェクトルートの `tests/examples/custom_agents/` に配置されています。

### 単体テストの実行

```bash
pytest tests/examples/custom_agents/test_adk_models.py -v
pytest tests/examples/custom_agents/test_adk_agent.py -v
```

### E2E テストの実行（API キーが必要）

```bash
export GOOGLE_API_KEY="your-api-key"
pytest -m e2e tests/examples/custom_agents/test_adk_e2e.py -v
```

### カバレッジ測定付きで全テストを実行

```bash
pytest tests/examples/custom_agents/test_adk_*.py --cov=examples.custom_agents.adk_research -v
```

## 成功基準

| 基準項目 | 目標値                            | 検証方法                     |
| -------- | --------------------------------- | ---------------------------- |
| SC-001   | 単一検索処理時間 < 10 秒          | E2E テストの実行時間測定     |
| SC-002   | 深層調査処理時間 < 30 秒          | E2E テストの実行時間測定     |
| SC-003   | エラー情報の 100%取得             | 単体テストによる検証         |
| SC-004   | ソースコード追跡の 100%実現       | 単体テストによる検証         |
| SC-005   | コードカバレッジ 80%              | カバレッジレポートによる測定 |
| SC-007   | MemberAgentResult との 100%互換性 | 統合テストによる検証         |

## 参考資料

- [Google ADK を使用した深層調査エージェントの構築](https://cloud.google.com/blog/products/ai-machine-learning/build-a-deep-research-agent-with-google-adk)
- [Google ADK Python リポジトリ](https://github.com/google/adk-python)
- [Google 検索の Grounding 機能](https://ai.google.dev/gemini-api/docs/google-search)
- [Gemini モデル一覧](https://ai.google.dev/gemini-api/docs/models)

## ライセンス

Apache-2.0
