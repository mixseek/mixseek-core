# Research: bitbank Public API連携サンプルエージェント

**Feature**: 133-custom-member-api
**Date**: 2025-11-20
**Parent Spec**: specs/018-custom-member/spec.md

## 1. bitbank Public API エンドポイント

### Decision

以下の2つのPublic APIエンドポイントを実装に採用：

1. **`GET /{pair}/ticker`**: リアルタイム価格情報取得
   - Base URL: `https://public.bitbank.cc`
   - パラメータ: `{pair}` = btc_jpy, xrp_jpy, eth_jpy, ltc_jpy, mona_jpy, bcc_jpy, xlm_jpy, qtum_jpy, bat_jpy, omg_jpy, xym_jpy, link_jpy, mkr_jpy, boba_jpy, enj_jpy, matic_jpy, doge_jpy, astr_jpy, ada_jpy, avax_jpy, axs_jpy, flr_jpy, sand_jpy, gala_jpy, chz_jpy, apt_jpy, hbar_jpy, oat_jpy, eth_btc, doge_btc
   - レスポンス構造:
     ```json
     {
       "success": 1,
       "data": {
         "sell": "string (売値)",
         "buy": "string (買値)",
         "high": "string (24時間高値)",
         "low": "string (24時間安値)",
         "last": "string (最終取引価格)",
         "vol": "string (24時間取引量)",
         "timestamp": number (UNIXタイムスタンプ、ミリ秒)
       }
     }
     ```

2. **`GET /{pair}/candlestick/{candle-type}/{YYYY}`**: 時系列OHLCVデータ取得
   - パラメータ:
     - `{pair}`: tickerと同様の通貨ペア
     - `{candle-type}`: 1min, 5min, 15min, 30min, 1hour, 4hour, 8hour, 12hour, 1day, 1week, 1month (11種類)
     - `{YYYY}`: 年（例: 2025）
   - レスポンス構造:
     ```json
     {
       "success": 1,
       "data": {
         "candlestick": [
           {
             "type": "string (candle-type)",
             "ohlcv": [
               [open, high, low, close, volume, timestamp]
             ]
           }
         ],
         "timestamp": number
       }
     }
     ```

### Rationale

- **認証不要**: Public APIのため開発者がAPIキー登録なしで即座に試行可能（学習目的に最適）
- **シンプルな構造**: RESTful APIで理解しやすく、教育的価値が高い
- **包括的なデータ**: ticker（リアルタイム）とcandlestick（時系列）の両方をカバー
- **信頼性**: bitbankは日本の主要暗号資産取引所で、APIの安定性が高い
- **Article 9準拠**: API base URLをTOML設定で管理（ハードコード禁止）

### Alternatives Considered

- **他の暗号資産取引所API（CoinGecko、Binance）**:
  - CoinGecko: 無料枠だがレート制限が厳しい（10-50 req/min）
  - Binance: APIキー登録が必要で初心者向けではない
- **Private API（認証付き）**:
  - 売買注文機能を含むが、学習目的のサンプルエージェントには不適切（セキュリティリスク）

### Rate Limiting Strategy

**公式ドキュメントにレート制限の明示的記載なし**のため、保守的アプローチを採用：

1. **最低リクエスト間隔**: 1秒（推奨）
2. **HTTP 429検出時**: エクスポネンシャルバックオフ（1秒 → 2秒 → 4秒）
3. **最大リトライ回数**: 3回（TOML設定`max_retries`）
4. **タイムアウト**: 30秒（TOML設定`timeout_seconds`）

## 2. HTTPクライアントライブラリ

### Decision

**httpx（非同期HTTPクライアント）**を採用

- Version: 0.27.0以上（Python 3.13互換）
- 用途: bitbank Public APIへの非同期HTTPリクエスト

### Rationale

1. **非同期ネイティブサポート**:
   - `async`/`await`構文をネイティブサポート
   - `BaseMemberAgent.execute()`が非同期メソッドのため必須
   - 複数通貨ペアの並行データ取得に最適

2. **柔軟なタイムアウト設定**:
   - connect、read、write、poolの個別タイムアウト設定が可能
   - `httpx.Timeout(connect=5.0, read=30.0)`のような細かい制御

3. **リトライ機構の柔軟性**:
   - `httpx.AsyncHTTPTransport(retries=3)`による組み込みリトライ
   - カスタムエクスポネンシャルバックオフの実装が容易

4. **HTTP/2サポート**:
   - 将来的なパフォーマンス最適化の可能性

5. **Python 3.13完全対応**:
   - 最新のPython型ヒント機能を活用可能

### Alternatives Considered

- **requests（同期HTTPクライアント）**:
  - 欠点: 同期専用で非同期処理に対応していない
  - `asyncio`との統合にスレッドプール経由が必要でオーバーヘッドが大きい
  - 複数通貨ペアの並行取得が非効率

- **aiohttp**:
  - 欠点: httpxより低レベルでコード量が増える
  - タイムアウト設定が複雑

### Implementation Notes

**エクスポネンシャルバックオフの実装例**:

```python
import asyncio
import httpx

async def fetch_with_retry(url: str, max_retries: int = 3) -> dict:
    """HTTP 429検出時のエクスポネンシャルバックオフ実装"""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # 1秒 → 2秒 → 4秒
                    await asyncio.sleep(wait_time)
                    continue
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise httpx.HTTPStatusError("Max retries exceeded", ...)
```

**Article 9準拠**:
- タイムアウト、リトライ回数はTOML設定で管理（`timeout_seconds`、`max_retries`）

## 3. 金融指標分析ライブラリ

### Decision

**numpy（数値計算ライブラリ）**を採用

- Version: 1.26.0以上（Python 3.13互換）
- 用途: 金融指標計算（年率リターン、年率ボラティリティ、シャープレシオ、最大ドローダウン、分布統計）

### Rationale

1. **高速性**:
   - C実装による配列演算で純粋Pythonの10～100倍高速
   - 1000件のロウソク足データ処理が数ミリ秒で完了
   - 金融指標計算（日次リターン、ローリング最大値、分布統計）に最適

2. **メモリ効率**:
   - 連続メモリ配列でPythonリストの5～10倍メモリ効率が高い
   - 大量データ（数千件）処理時のメモリ負荷削減

3. **軽量性**:
   - 依存関係なし（純粋Cライブラリ）
   - インポート時間が短い（約0.1秒）

4. **Python 3.13対応**:
   - NumPy 1.26.0以降でPython 3.13を完全サポート

5. **金融計算に必要な統計関数**:
   - `np.mean()`, `np.std()`: 年率リターン・ボラティリティ計算
   - `np.maximum.accumulate()`: ローリング最大値（最大ドローダウン計算）
   - 手動実装による分布統計（歪度・尖度）: scipyへの依存を避け軽量化

### Alternatives Considered

- **pandas（データ分析ライブラリ）**:
  - 欠点: 基本統計計算のみのサンプルには過剰な機能（DataFrame、Series、時系列処理など）
  - 依存関係が多い（pytz、python-dateutil等）
  - インポート時間が長い（約0.5秒）
  - メモリ使用量が大きい

- **statistics（Python標準ライブラリ）**:
  - 欠点: 純粋Python実装で大量データ処理が遅い
  - 配列操作機能が貧弱

### Implementation Notes

**実装する金融指標機能**:

```python
import numpy as np
from scipy import stats

def calculate_financial_metrics(
    candlestick_data: BitbankCandlestickData,
    config: BitbankAPIConfig
) -> FinancialSummary:
    """金融指標の計算

    Args:
        candlestick_data: ロウソク足データ
        config: API設定（risk_free_rate、trading_days_per_year、minimum_acceptable_returnを含む）

    Returns:
        FinancialSummary: 金融指標サマリー
    """
    closes = np.array([entry.close for entry in candlestick_data.ohlcv])

    # 日次リターン計算
    daily_returns = np.diff(closes) / closes[:-1]

    # 年率リターン（複利計算）
    daily_mean_return = np.mean(daily_returns)
    annualized_return = (1 + daily_mean_return) ** config.trading_days_per_year - 1

    # 年率ボラティリティ
    daily_std = np.std(daily_returns)
    annualized_volatility = daily_std * np.sqrt(config.trading_days_per_year)

    # シャープレシオ
    sharpe_ratio = (annualized_return - config.risk_free_rate) / annualized_volatility

    # ソルティーノレシオ（下方リスクのみ考慮）
    downside_returns = daily_returns[daily_returns < config.minimum_acceptable_return]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0
    sortino_ratio = (annualized_return - config.minimum_acceptable_return) / (downside_std * np.sqrt(config.trading_days_per_year)) if downside_std > 0 else 0.0

    # 最大ドローダウン（Running maximum method）
    running_max = np.maximum.accumulate(closes)
    drawdowns = (closes - running_max) / running_max
    max_drawdown = np.min(drawdowns)

    # リターン分布
    return_skewness = stats.skew(daily_returns)
    return_kurtosis = stats.kurtosis(daily_returns)

    return FinancialSummary(
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        return_skewness=return_skewness,
        return_kurtosis=return_kurtosis,
        total_return=(closes[-1] - closes[0]) / closes[0],
        start_price=closes[0],
        end_price=closes[-1],
        mean_price=np.mean(closes),
        total_volume=np.sum([entry.volume for entry in candlestick_data.ohlcv]),
        trading_days=len(closes),
    )
```

**エラーハンドリング**:
- 空配列: `ValueError("Candlestick data is empty")`
- NaN/Inf: `numpy.isfinite()`によるバリデーション
- 金融指標計算エラー: ゼロ除算、無効な金融パラメータの明示的エラー

## 4. エラーハンドリング戦略

### Decision

**4層のエラーハンドリング戦略**を採用:

1. **入力バリデーション層**: Pydantic Modelによる厳密な検証
2. **ネットワーク層**: httpx例外の包括的処理
3. **レスポンス検証層**: Pydantic Modelによるスキーマ検証
4. **データ処理層**: numpy計算エラーのハンドリング

### Rationale

**Article 9（Data Accuracy Mandate）準拠**:
- **NO 暗黙的フォールバック**: エラー時にデフォルト値を自動適用しない
- **NO ハードコーディング**: エラーメッセージも定数として定義
- **明示的エラー伝播**: すべてのエラーで明確なメッセージを返す

**親仕様FR-019準拠**:
- Toolset経由の関数呼び出しで例外を適切に伝播
- Leader Agentが例外をキャッチし、チーム失格判定を行う

### Implementation Notes

#### 1. 入力バリデーション層

```python
from pydantic import BaseModel, Field, field_validator

class BitbankAPIRequest(BaseModel):
    """APIリクエストのバリデーション"""
    pair: str = Field(..., pattern=r"^[a-z]+_[a-z]+$")
    candle_type: str | None = Field(None, pattern=r"^(1min|5min|15min|30min|1hour|4hour|8hour|12hour|1day|1week|1month)$")

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        valid_pairs = ["btc_jpy", "xrp_jpy", "eth_jpy", ...]
        if v not in valid_pairs:
            raise ValueError(f"Invalid currency pair: {v}. Supported pairs: {', '.join(valid_pairs)}")
        return v
```

#### 2. ネットワーク層

```python
import httpx

try:
    response = await client.get(url, timeout=30.0)
    response.raise_for_status()
except httpx.TimeoutException:
    raise RuntimeError(f"Request timeout after {timeout}s. Check network connectivity.")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        raise ValueError(f"Currency pair not found: {pair}")
    elif e.response.status_code == 429:
        raise RuntimeError("Rate limit exceeded. Retry with exponential backoff.")
    elif e.response.status_code >= 500:
        raise RuntimeError(f"bitbank API server error: {e.response.status_code}")
    else:
        raise
except httpx.NetworkError:
    raise RuntimeError("Network connection error. Check internet connectivity.")
```

#### 3. レスポンス検証層

```python
from pydantic import BaseModel, ValidationError

class BitbankTickerResponse(BaseModel):
    """APIレスポンスのスキーマ検証"""
    success: int
    data: dict

try:
    validated = BitbankTickerResponse.model_validate(response.json())
except ValidationError as e:
    raise ValueError(f"Invalid API response schema: {e}")
```

#### 4. データ処理層

```python
import numpy as np

try:
    prices = np.array([float(d["close"]) for d in candlestick_data])
    if len(prices) == 0:
        raise ValueError("No candlestick data available")
    if not np.all(np.isfinite(prices)):
        raise ValueError("Price data contains NaN or Inf values")
    mean_price = np.mean(prices)
except ValueError as e:
    raise ValueError(f"Data processing error: {e}")
```

### Error Message Format

**親仕様FR-019準拠のフォーマット**:

```
Error: <エラー概要>. <詳細説明または対処方法>
```

**例**:
- `Error: Invalid currency pair: btc_usd. Supported pairs: btc_jpy, xrp_jpy, eth_jpy`
- `Error: Request timeout after 30s. Check network connectivity or increase timeout_seconds in TOML config.`
- `Error: Rate limit exceeded. Retry with exponential backoff (wait time: 2s).`

## 5. TOML設定構造

### Decision

以下のTOML設定構造を採用（親仕様インターフェースに準拠）:

```toml
[agent]
type = "custom"  # 018-custom-member仕様で固定
name = "bitbank-api-agent"
description = "Sample agent for bitbank Public API integration - time series analysis and financial metrics"
capabilities = ["data_retrieval", "financial_metrics_analysis"]

[agent.metadata]
version = "1.0.0"
author = "mixseek-core team"
license = "Apache-2.0"

[agent.metadata.plugin]
agent_module = "examples.custom_agents.bitbank.agent"  # 推奨: agent_module
agent_class = "BitbankAPIAgent"

# または path による指定（agent_module と排他）
# path = "examples/custom_agents/bitbank/agent.py"

[agent.tool_settings]
# bitbank API設定（Article 9準拠: ハードコード禁止）
[agent.tool_settings.bitbank_api]
base_url = "https://public.bitbank.cc"
timeout_seconds = 30
max_retries = 3
retry_delay_seconds = 1  # エクスポネンシャルバックオフの初期待機時間
min_request_interval_seconds = 1  # レート制限対応

# サポート通貨ペア（明示的定義）
supported_pairs = [
    "btc_jpy", "xrp_jpy", "eth_jpy", "ltc_jpy", "mona_jpy",
    "bcc_jpy", "xlm_jpy", "qtum_jpy", "bat_jpy", "omg_jpy"
]

# サポートするcandlestickタイプ
supported_candle_types = [
    "1min", "5min", "15min", "30min", "1hour",
    "4hour", "8hour", "12hour", "1day", "1week", "1month"
]

# Financial metrics settings (Article 9: Data Accuracy Mandate)
[agent.tool_settings.bitbank_api.financial_metrics]
risk_free_rate = 0.001  # 年率0.1%（日本10年国債利回り）
trading_days_per_year = 365  # 暗号通貨は365日取引
minimum_acceptable_return = 0.0  # ソルティーノレシオMAR（ゼロリターン）

[agent.llm_settings]
# LLM設定（環境変数参照）
model = "gemini-2.0-flash-exp"  # Pydantic AI/Google ADK
# Note: GOOGLE_API_KEY は環境変数で設定（Article 9準拠）

temperature = 0.7
top_p = 0.9
max_tokens = 8192
```

### Rationale

**Article 9（Data Accuracy Mandate）準拠**:
- すべての設定値をTOMLで明示（ハードコード禁止）
- API base URL、タイムアウト、リトライ設定を集中管理
- 環境変数（`GOOGLE_API_KEY`）とTOML設定の明確な分離

**親仕様インターフェース準拠**:
- `type = "custom"`固定（018-custom-member仕様）
- `agent_module`または`path`による動的ロード機構
- `tool_settings`セクションでツール固有設定を階層化

**拡張性**:
- `supported_pairs`、`supported_candle_types`の明示的定義
- 将来的なAPI設定追加が容易

### Configuration Loading Pattern

```python
import os
import tomllib
from pathlib import Path
from pydantic import BaseModel, Field

class BitbankAPIConfig(BaseModel):
    """bitbank API設定（Article 9準拠）"""
    base_url: str = Field(..., description="API base URL（TOML必須）")
    timeout_seconds: int = Field(30, gt=0)
    max_retries: int = Field(3, ge=0, le=10)
    retry_delay_seconds: int = Field(1, gt=0)
    min_request_interval_seconds: int = Field(1, gt=0)
    supported_pairs: list[str] = Field(default_factory=list)
    supported_candle_types: list[str] = Field(default_factory=list)
    risk_free_rate: float = Field(0.001, ge=0, description="Risk-free rate for Sharpe ratio")
    trading_days_per_year: int = Field(365, gt=0, description="Trading days per year for annualization")
    minimum_acceptable_return: float = Field(0.0, description="Minimum acceptable return for Sortino ratio")

def load_config(config_path: Path) -> BitbankAPIConfig:
    """TOML設定の読み込みとバリデーション"""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    # Article 9準拠: 必須フィールドが欠けている場合は例外
    try:
        return BitbankAPIConfig.model_validate(
            config_data["agent"]["tool_settings"]["bitbank_api"]
        )
    except KeyError as e:
        raise ValueError(f"Missing required config section: {e}")

# 環境変数の読み込み（Article 9準拠: 明示的エラー）
def get_google_api_key() -> str:
    """環境変数からGoogle API Keyを取得"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Please set it using: export GOOGLE_API_KEY='your-key'"
        )
    return api_key
```

### Alternatives Considered

- **環境変数のみで設定管理**:
  - 欠点: 設定項目が多い場合に管理が煩雑
  - 欠点: 設定のバージョン管理が困難

- **JSONまたはYAML設定ファイル**:
  - 欠点: TOMLより可読性が低い（特にYAML）
  - 欠点: Python 3.13標準ライブラリで`tomllib`が利用可能でJSON/YAMLライブラリが不要

## Implementation Checklist

### Article 9準拠確認

- [ ] NO ハードコーディング（マジックナンバー、固定文字列、API URL）
- [ ] NO 暗黙的フォールバック（デフォルト値の自動適用）
- [ ] NO 推測・補完（エラー時の値生成）
- [ ] 明示的データソース（TOML設定、環境変数）
- [ ] 適切なエラー伝播（明確なエラーメッセージ）

### 親仕様インターフェース準拠確認

- [ ] `BaseMemberAgent`継承
- [ ] `type = "custom"`固定（TOML設定）
- [ ] 動的ロード機構（`agent_module`または`path`）
- [ ] 非同期`execute(task: str, context: dict) -> MemberAgentResult`実装
- [ ] `MemberAgentResult`返却（success: bool, content: str, metadata: dict）

### MixSeek-Core Framework整合性確認

- [ ] Pydantic AI Toolsetを通じた関数呼び出し（FR-019）
- [ ] Leader Agentと同一プロセス内で実行（高速、低オーバーヘッド）
- [ ] エラー時のチーム失格判定（FR-017）
- [ ] TOML設定の階層的妥当性チェック（FR-014）

## Next Steps

1. **plan.md作成**: 本research.mdの決定事項に基づき実装計画を策定
2. **data-model.md作成**: Pydantic Modelの詳細設計（BitbankTickerData、BitbankCandlestickData、FinancialSummary等）
3. **quickstart.md作成**: 開発者向けクイックスタートガイド（10分でセットアップ）
4. **tasks.md生成**: `/speckit.tasks`で実装タスクを自動生成
5. **テスト設計**: Article 3（Test-First Imperative）に従い実装前のテスト作成
