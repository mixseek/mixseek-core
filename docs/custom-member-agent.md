# カスタムエージェント開発ガイド

MixSeek-Coreでは、標準バンドル以外にカスタムMember Agentを開発して動的にロードできます。この機能により、独自のドメイン知識やツールを統合したエージェントを作成できます（FR-020-FR-022）。

## 動的ロード方式

カスタムエージェントは2つの方法でロードできます

1. **agent_module（推奨）**: pip インストール可能なPythonパッケージからロード（本番環境向け）
2. **path（代替）**: スタンドアロンPythonファイルからロード（開発・プロトタイピング向け）

優先順位処理（FR-021）
- `agent_module`が指定されている場合、優先的に試行
- `agent_module`が失敗または未指定の場合、`path`にフォールバック

## カスタムエージェントクラスの実装

すべてのカスタムエージェントは`BaseMemberAgent`を継承する必要があります

```python
from typing import Any

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult

class DataAnalystAgent(BaseMemberAgent):
    """データ分析専門カスタムエージェント"""

    def __init__(self, config: MemberAgentConfig):
        super().__init__(config)
        # カスタム初期化処理

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """
        エージェント実行のメインエントリポイント

        Args:
            task: タスク説明
            context: 実行コンテキスト
            **kwargs: 追加パラメータ

        Returns:
            MemberAgentResult: 実行結果
        """
        # カスタムロジックの実装
        # self._agent（Pydantic AI Agent）を使用して推論実行
        result = await self._agent.run(task)

        return MemberAgentResult.success(
            content=result.data,
            agent_name=self.config.name,
            agent_type=self.config.type,
        )
```

## TOML設定

### agent_module方式（推奨）

pipインストール可能なパッケージからロードする方式

```toml
[agent]
name = "data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a data analyst with expertise in pandas and numpy. Analyze data and provide insights based on statistical methods."
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.plugin]
agent_module = "my_analytics_package.agents.data_analyst"
agent_class = "DataAnalystAgent"
```

パッケージのインストール

```bash
pip install my_analytics_package
```

### path方式（代替）

開発環境でスタンドアロンファイルからロードする方式

```{warning}
**セキュリティ警告**: `path`方式は指定されたファイルからPythonコードを実行します。
**信頼できるソースからのファイルのみを使用してください**。
本番環境では`agent_module`方式の使用を強く推奨します。
```

```toml
[agent]
name = "data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a data analyst with expertise in pandas and numpy. Analyze data and provide insights based on statistical methods."
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.plugin]
path = "/path/to/custom_agent.py"
agent_class = "DataAnalystAgent"
```

### 両方指定（フォールバック）

本番環境では`agent_module`を使い、開発環境では`path`にフォールバックする構成

```toml
[agent]
name = "data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
system_instruction = "You are a data analyst with expertise in pandas and numpy. Analyze data and provide insights based on statistical methods."
description = "Pandas/NumPyを使ったデータ分析専門エージェント"

[agent.plugin]
agent_module = "my_analytics_package.agents.data_analyst"  # 優先
path = "/path/to/custom_agent.py"                          # フォールバック
agent_class = "DataAnalystAgent"
```

## エラーハンドリング

カスタムエージェントのロードに失敗した場合、詳細なエラーメッセージが表示されます（FR-022）

**agent_module方式のエラー例**
```
Error: Failed to load custom agent from module 'my_package.agents.custom'.
ModuleNotFoundError: No module named 'my_package'.
Install package: pip install <package-name>
```

**path方式のエラー例**
```
Error: Failed to load custom agent from path '/path/to/custom_agent.py'.
FileNotFoundError: File not found.
Check file path in TOML config.
```

**クラス名エラー例**
```
Error: Custom agent class 'WrongClassName' not found in module 'my_package.agents'.
Check agent_class in TOML config.
```

## 使用方法

カスタムエージェントは標準エージェントと同じ方法で使用できます

```bash
# CLIで実行
mixseek member "Analyze this dataset" --config custom_agent.toml

# 出力形式指定
mixseek member "Analyze sales trends" \
  --config custom_agent.toml \
  --output-format json
```

## 実装例: bitbank API統合

実際の外部API統合を通じて、カスタムエージェントの実装方法を学びます。

### 概要

bitbank Public APIと統合し、暗号通貨の財務指標分析を行うカスタムエージェントです。

**機能:**
- リアルタイム価格取得（ティッカーデータ）
- ローソク足データ分析（OHLCV）
- 財務指標計算（シャープレシオ、ソルティノレシオ、最大ドローダウン、歪度、尖度）

**学べること:**
- 外部API統合（httpx、リトライロジック、レート制限）
- Pydantic AIツール登録（複数ツールの管理）
- 非同期処理（async/await）
- エラーハンドリング（明示的なエラー伝播）
- TOML設定管理（すべての定数値を外部化）

### ファイル構成

```
examples/custom_agents/bitbank/
├── agent.py                   # エージェントクラス（BitbankAPIAgent）
├── models.py                  # Pydanticモデル（FinancialSummary, BitbankAPIConfig等）
├── client.py                  # 非同期HTTPクライアント（BitbankAPIClient）
├── tools.py                   # ツール関数（ticker取得、財務指標計算）
├── bitbank_agent.toml         # TOML設定ファイル
└── README.md                  # 詳細な使用方法
```

### 実装手順

#### ステップ1: Pydanticモデル定義

財務指標とAPI設定のモデルを定義します。すべてのデータ構造はPydanticでバリデーションします

```{literalinclude} ../examples/custom_agents/bitbank/models.py
:language: python
:lines: 146-160
:caption: examples/custom_agents/bitbank/models.py - FinancialSummaryモデル（抜粋）
```

**ポイント:**
- `Field`でバリデーションルールを定義（`ge=0`, `le=0`等）
- docstringで各フィールドの意味を明記
- 財務指標の計算に必要なすべてのパラメータをモデル化

#### ステップ2: APIクライアント実装

非同期HTTPクライアントとリトライロジックを実装します

```{literalinclude} ../examples/custom_agents/bitbank/client.py
:language: python
:lines: 39-71
:caption: examples/custom_agents/bitbank/client.py - リトライロジック（抜粋）
```

**ポイント:**
- 指数バックオフでリトライ（`2**attempt`）
- 429 Rate Limitエラーの自動処理
- レート制限遵守（`_enforce_rate_limit`）

#### ステップ3: ツール関数実装

API統合と財務指標計算の関数を実装します

```{literalinclude} ../examples/custom_agents/bitbank/tools.py
:language: python
:lines: 125-160
:caption: examples/custom_agents/bitbank/tools.py - 財務指標計算（抜粋）
```

**ポイント:**
- NumPyで効率的な統計計算
- すべての定数（`risk_free_rate`等）は設定から取得
- NaN/Inf値の明示的なチェック

#### ステップ4: エージェントクラス実装

`BaseMemberAgent`を継承し、Pydantic AIツールを登録します

```{literalinclude} ../examples/custom_agents/bitbank/agent.py
:language: python
:lines: 28-60
:caption: examples/custom_agents/bitbank/agent.py - エージェント初期化（抜粋）
```

**重要なポイント:**
- `config.metadata.get("tool_settings", {}).get("bitbank_api", {})`で設定取得
- 設定が存在しない場合は明示的なエラー
- Pydantic AIの`Agent`を初期化し、`deps_type`で依存関係を指定

ツール登録の例

```{literalinclude} ../examples/custom_agents/bitbank/agent.py
:language: python
:lines: 61-76
:caption: examples/custom_agents/bitbank/agent.py - ツール登録（抜粋）
```

**ツール実装のポイント:**
- `@self.agent.tool`デコレータでツールとして登録
- `ctx: RunContext[BitbankAPIConfig]`型アノテーション必須
- `async def`で定義（イベントループの入れ子を回避）
- Markdown形式で結果を返す（LLMが解釈しやすい）

#### ステップ5: TOML設定

エージェント設定とAPI設定を定義します

```{literalinclude} ../examples/custom_agents/bitbank/bitbank_agent.toml
:language: toml
:lines: 1-20
:caption: examples/custom_agents/bitbank/bitbank_agent.toml - 基本設定（抜粋）
```

**注意:**
- `[agent.metadata.tool_settings.bitbank_api]`にAPI設定を配置
- すべての定数値（risk_free_rate等）は設定ファイルで管理
- `[agent.plugin]`で`path`または`agent_module`を指定

財務指標設定

```{literalinclude} ../examples/custom_agents/bitbank/bitbank_agent.toml
:language: toml
:lines: 54-57
:caption: examples/custom_agents/bitbank/bitbank_agent.toml - 財務指標設定
```

````{warning}
本サンプルは`path`方式を使用しています。
本番環境では`agent_module`方式に変更してください

```toml
[agent.plugin]
agent_module = "your_package.agents.bitbank"
agent_class = "BitbankAPIAgent"
```

`path`方式は開発・プロトタイピング用です。信頼できるソースからのファイルのみを使用してください。
````

### 実行方法

```bash
# 環境変数設定
export GOOGLE_API_KEY="your-api-key"
export MIXSEEK_WORKSPACE=/tmp

# 実行
mixseek member "btc_jpyの2024年のパフォーマンスを日足で分析してください" \
  --config examples/custom_agents/bitbank/bitbank_agent.toml
```

**出力例:**

```
Status: SUCCESS
Agent: bitbank-api-agent (custom)

### BTC_JPY 2024年 日次パフォーマンス分析

#### リターン
*   **年率リターン**: 170.06%
*   **トータルリターン**: 136.15%

#### リスク指標
*   **年率ボラティリティ**: 52.19%
*   **最大ドローダウン**: -30.66%

#### リスク調整後リターン
*   **シャープ・レシオ**: 3.256
*   **ソルティノ・レシオ**: 5.333
```

```{tip}
**ベストプラクティス**:
- すべての定数値はTOMLファイルで管理
- エラーは明示的に伝播
- ツール関数は`async def`で定義
- 型アノテーションを徹底（mypy strict mode推奨）
```

### 詳細情報

完全な実装とドキュメントは以下を参照
- **サンプルコード**: `examples/custom_agents/bitbank/`
- **日本語README**: `examples/custom_agents/bitbank/README.md`
- **仕様書**: `specs/019-custom-member-api/spec.md`
- **実装計画**: `specs/019-custom-member-api/plan.md`
- **データモデル**: `specs/019-custom-member-api/data-model.md`
