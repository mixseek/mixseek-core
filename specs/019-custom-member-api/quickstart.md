# Quickstart Guide: bitbank Public API連携サンプルエージェント

**Feature**: 133-custom-member-api
**Date**: 2025-11-20
**Target Audience**: Python中級レベルの開発者

## Overview

このガイドでは、bitbank Public API連携サンプルエージェント（`BitbankAPIAgent`）を10分でセットアップし、基本的なデータ取得と金融指標分析を実行する方法を説明します。

## Prerequisites

- Python 3.13以上
- uv（パッケージマネージャ）
- Google API Key（環境変数`GOOGLE_API_KEY`に設定）
- インターネット接続（bitbank APIアクセス用）

## Step 1: 環境セットアップ (2分)

### 1.1 リポジトリのクローン

```bash
cd /path/to/your/workspace
git clone https://github.com/your-org/mixseek-core.git
cd mixseek-core
```

### 1.2 依存関係のインストール

```bash
uv sync
```

### 1.3 環境変数の設定

```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

**Note**: Google API Keyは[Google AI Studio](https://aistudio.google.com/apikey)で取得できます。

## Step 2: TOML設定ファイルの確認 (1分)

サンプルエージェントの設定ファイルを確認します。

```bash
cat examples/custom_agents/bitbank/bitbank_agent.toml
```

**設定例**:

```toml
[agent]
type = "custom"
name = "bitbank-api-agent"
description = "Sample agent for bitbank Public API integration"
capabilities = ["data_retrieval", "statistical_analysis"]

[agent.metadata.plugin]
agent_module = "examples.custom_agents.bitbank.agent"
agent_class = "BitbankAPIAgent"

[agent.tool_settings.bitbank_api]
base_url = "https://public.bitbank.cc"
timeout_seconds = 30
max_retries = 3
retry_delay_seconds = 1
min_request_interval_seconds = 1
supported_pairs = ["btc_jpy", "xrp_jpy", "eth_jpy"]
supported_candle_types = ["1hour", "1day", "1week"]

[agent.llm_settings]
model = "gemini-2.0-flash-exp"
temperature = 0.7
```

## Step 3: サンプルエージェントの実行 (3分)

### 3.1 リアルタイム価格取得

```bash
mixseek member \
  --config examples/custom_agents/bitbank/bitbank_agent.toml \
  --task "Get the current ticker data for btc_jpy"
```

**期待される出力**:

```
# BTC/JPY Ticker Data

## Current Prices
- **Buy Price**: 10,500,000 JPY
- **Sell Price**: 10,510,000 JPY
- **Last Traded Price**: 10,505,000 JPY

## 24-Hour Statistics
- **High**: 10,600,000 JPY
- **Low**: 10,400,000 JPY
- **Volume**: 1,234.5678 BTC

**Timestamp**: 2025-11-20 10:30:00
```

### 3.2 時系列データ分析

```bash
mixseek member \
  --config examples/custom_agents/bitbank/bitbank_agent.toml \
  --task "Analyze btc_jpy candlestick data for the last 24 hours using 1hour intervals"
```

**期待される出力**:

```
# BTC/JPY Candlestick Analysis (1hour, Last 24 Hours)

## Statistical Summary
- **Mean Price**: 10,505,000 JPY
- **Standard Deviation**: 15,000 JPY
- **Maximum Price**: 10,600,000 JPY
- **Minimum Price**: 10,400,000 JPY
- **Median Price**: 10,500,000 JPY
- **Total Volume**: 1,234.5678 BTC
- **Price Change Rate**: +1.92%

## Observations
- Price trend is **upward** with moderate volatility.
- Trading volume is consistent across the 24-hour period.
```

## Step 4: カスタムツールの動作確認 (2分)

### 4.1 単体テスト実行

```bash
pytest tests/examples/custom_agents/test_bitbank_agent.py -v
```

### 4.2 統合テスト実行

```bash
pytest tests/examples/custom_agents/test_bitbank_agent.py::test_integration -v
```

### 4.3 E2Eテスト実行（実際のAPI使用）

```bash
pytest tests/examples/custom_agents/test_bitbank_agent.py -m e2e -v
```

**Note**: E2Eテストは実際のbitbank APIを呼び出します。レート制限に注意してください。

## Step 5: コードの確認 (2分)

### 5.1 エージェント実装

```bash
cat examples/custom_agents/bitbank/agent.py
```

**主要なクラス**:

- `BitbankAPIAgent`: `BaseMemberAgent`を継承したカスタムエージェント
- `execute(task: str, context: dict) -> MemberAgentResult`: 非同期実行メソッド

### 5.2 ツール実装

```bash
cat examples/custom_agents/bitbank/tools.py
```

**主要なツール関数**:

- `get_ticker_data(pair: str) -> BitbankTickerData`: ticker API呼び出し
- `get_candlestick_data(pair: str, candle_type: str, year: int) -> BitbankCandlestickData`: candlestick API呼び出し
- `calculate_financial_metrics(candlestick_data: BitbankCandlestickData, config: BitbankAPIConfig) -> FinancialSummary`: 金融指標分析

## Troubleshooting

### Issue 1: `GOOGLE_API_KEY` not set

**Error**:
```
ValueError: GOOGLE_API_KEY environment variable is not set.
```

**Solution**:
```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

### Issue 2: bitbank APIタイムアウト

**Error**:
```
RuntimeError: Request timeout after 30s. Check network connectivity.
```

**Solution**:
- インターネット接続を確認
- TOML設定で`timeout_seconds`を増やす（例: 60秒）

### Issue 3: レート制限エラー

**Error**:
```
RuntimeError: Rate limit exceeded. Retry with exponential backoff.
```

**Solution**:
- リクエスト間隔を空ける（最低1秒）
- TOML設定で`min_request_interval_seconds`を増やす

### Issue 4: 無効な通貨ペア

**Error**:
```
ValueError: Invalid currency pair: btc_usd. Supported pairs: btc_jpy, xrp_jpy, eth_jpy
```

**Solution**:
- サポートされている通貨ペアを使用（`btc_jpy`、`xrp_jpy`、`eth_jpy`など）
- TOML設定の`supported_pairs`を確認

## Next Steps

### カスタムエージェント開発

1. **新しいエージェントを作成**: `examples/custom_agents/your_agent/`ディレクトリを作成
2. **`BaseMemberAgent`を継承**: `agent.py`で独自のエージェントクラスを実装
3. **TOML設定を作成**: `your_agent.toml`で設定を定義
4. **テストを作成**: `tests/examples/custom_agents/test_your_agent.py`

### ドキュメント参照

- **カスタムエージェント開発ガイド**: `docs/custom-agent-guide.md`
- **親仕様（009-member）**: `specs/009-member/spec.md`
- **親仕様（018-custom-member）**: `specs/018-custom-member/spec.md`
- **データモデル詳細**: `specs/019-custom-member-api/data-model.md`

### 実装計画

- **Implementation Plan**: `specs/019-custom-member-api/plan.md`
- **Research**: `specs/019-custom-member-api/research.md`
- **Tasks**: `specs/019-custom-member-api/tasks.md`（`/speckit.tasks`で生成）

## Summary

このクイックスタートガイドでは、以下を実行しました：

1. 環境セットアップ（uv sync、環境変数設定）
2. TOML設定ファイルの確認
3. サンプルエージェントの実行（ticker、candlestick、金融指標分析）
4. テストの実行（単体、統合、E2E）
5. コードの確認（agent.py、tools.py）

次は、`docs/custom-agent-guide.md`を参照して、独自のカスタムエージェントを開発してください。
