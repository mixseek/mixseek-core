# Research: bitbank Public API連携サンプルエージェント

**Feature Branch**: `018-custom-member`
**Research Date**: 2025-11-20
**Status**: Completed

## 概要

本リサーチは、Feature 114（Custom Member Agent Development）における外部API連携サンプルエージェントの実装計画策定のために実施しました。具体的には、bitbank Public API（暗号資産取引所の公開API）を利用した時系列データ取得と統計分析機能を持つカスタムMember Agentの技術選定と設計方針を決定します。

### サンプルエージェントの目的

- **外部API統合パターンの実証**: REST APIクライアント実装、エラーハンドリング、レート制限対応の実装例を提供
- **認証不要で即座に試行可能**: bitbank Public APIは認証不要のため、開発者がすぐに実行できる
- **統計分析機能の実装例**: 取得したOHLCVデータの基本統計計算（平均、標準偏差、最大/最小値）を示す
- **親仕様インターフェース準拠の実証**: `BaseMemberAgent`継承、TOML設定（`type = "custom"`）、動的ロード機構の使用例を提供

## 1. bitbank Public API エンドポイント

### Decision

以下の2つのエンドポイントを使用します：

1. **`GET /{pair}/ticker`**: リアルタイム価格情報の取得
2. **`GET /{pair}/candlestick/{candle-type}/{YYYY}`**: 時系列OHLCV（ローソク足）データの取得

### Rationale

#### エンドポイント選定理由

- **ticker**: シンプルなREST APIリクエストの実装例として最適（単一リクエスト、即座にレスポンス）
- **candlestick**: より複雑なパラメータ処理と大量データハンドリングの実装例として有用（複数パラメータ、日付フォーマット、配列レスポンス）
- **認証不要**: Public APIのため環境変数によるAPI Key管理が不要で、開発者が即座に試行可能
- **信頼性**: bitbankは日本の主要暗号資産取引所であり、APIの安定性が高い

#### レスポンス構造

**ticker エンドポイント**:
```json
{
  "success": 1,
  "data": {
    "sell": "最低売値",
    "buy": "最高買値",
    "high": "24時間最高値",
    "low": "24時間最低値",
    "open": "24時間前の始値",
    "last": "最新約定価格",
    "vol": "24時間取引量",
    "timestamp": "UNIXタイムスタンプ（ミリ秒）"
  }
}
```

**candlestick エンドポイント**:
```json
{
  "success": 1,
  "data": {
    "candlestick": [
      {
        "type": "1hour",
        "ohlcv": [
          ["open", "high", "low", "close", "volume", "UNIXタイムスタンプ(ミリ秒)"],
          ...
        ]
      }
    ]
  }
}
```

#### パラメータ仕様

- **pair**: 通貨ペア（例: `btc_jpy`, `eth_jpy`, `xrp_jpy`）
- **candle-type**: ローソク足の時間単位
  - 短期: `1min`, `5min`, `15min`, `30min`
  - 中期: `1hour`, `4hour`, `8hour`, `12hour`
  - 長期: `1day`, `1week`, `1month`
- **YYYY**: 日付指定
  - 短期足（1min～30min）: `YYYYMMDD`形式（例: `20250120`）
  - 長期足（1hour～1month）: `YYYY`形式（例: `2025`）

#### レート制限と推奨リクエスト頻度

- **公式ドキュメントに明示的な記載なし**: bitbank Public APIドキュメントにはレート制限の具体的な数値が記載されていません
- **推奨実装方針**:
  - リクエスト間隔: 最低1秒のインターバルを設定（保守的なアプローチ）
  - リトライロジック: 429 Too Many Requestsレスポンス検出時のエクスポネンシャルバックオフ実装
  - タイムアウト設定: 30秒（TOML設定で変更可能）
  - 同時接続数: 1（シンプルな逐次実行）

#### エラーレスポンス形式

```json
{
  "success": 0,
  "data": {
    "code": "エラーコード（数値）"
  }
}
```

- **HTTP 4XX**: クライアントエラー（無効なパラメータ、存在しない通貨ペア等）
- **HTTP 5XX**: サーバーエラー（bitbank側の一時的障害）
- **タイムアウト**: ネットワークエラー、接続タイムアウト

#### ベースURL

```
https://public.bitbank.cc
```

### Alternatives Considered

#### coincheck API
- **長所**: 同様に日本の取引所、認証不要の公開API提供
- **短所**: APIドキュメントがbitbankより詳細でない、OHLCVデータ形式がやや複雑
- **不採用理由**: bitbankの方がドキュメントが整備されており、開発者の学習曲線が低い

#### CoinGecko API
- **長所**: グローバルな暗号資産価格データ、豊富なエンドポイント、API Key不要
- **短所**: レート制限が厳しい（無料プランで30リクエスト/分）、OHLCVデータがプレミアムプラン限定
- **不採用理由**: 無料で試せる機能が制限され、サンプルとしての有用性が低い

#### 公式Pythonライブラリ使用
- **長所**: bitbank公式の`python-bitbankcc`ライブラリが存在
- **短所**: Article 9（Data Accuracy Mandate）準拠のためには環境変数管理が必要、依存関係追加
- **不採用理由**: HTTPクライアント（httpx）を直接使用する方が、外部API統合パターンの教育価値が高い

## 2. HTTPクライアントライブラリ

### Decision

**httpx**（バージョン: >=0.27.0、Python 3.13互換）を採用します。

### Rationale

#### 非同期対応の必要性

- **親仕様の要件**: `BaseMemberAgent.execute()`は非同期メソッド（`async def execute(...)`）であり、すべてのカスタムエージェントは非同期処理に対応する必要がある
- **httpxの優位性**: ネイティブな非同期サポート（`httpx.AsyncClient`）により、`async with`構文とコンテキストマネージャーを使用した明示的なリソース管理が可能
- **requestsの制約**: 同期専用ライブラリであり、非同期対応の計画なし。`asyncio`と併用する場合はスレッドプール経由の実行が必要で、オーバーヘッドが大きい

#### タイムアウト設定の柔軟性

**httpx**:
```python
timeout = httpx.Timeout(
    connect=5.0,  # 接続タイムアウト
    read=30.0,    # 読み取りタイムアウト
    write=5.0,    # 書き込みタイムアウト
    pool=5.0      # プールタイムアウト
)
async with httpx.AsyncClient(timeout=timeout) as client:
    response = await client.get(url)
```

**requests**:
```python
# 単一のタイムアウト値のみ、または(connect, read)のタプル
response = requests.get(url, timeout=30)  # シンプルだが柔軟性に欠ける
```

#### リトライロジックの実装

**httpx**:
- **ネイティブサポート**: `AsyncHTTPTransport(retries=3)`で接続失敗時のリトライが可能（ただし、レスポンス受信後のリトライは対象外）
- **サードパーティ統合**: `httpx-retries`パッケージで高度なリトライポリシー（エクスポネンシャルバックオフ、HTTP 429対応）を実装可能
- **カスタム実装**: `BaseMemberAgent._execute_with_retry()`を活用したカスタムリトライロジックとの統合が容易

**requests**:
- **HTTPAdapter + urllib3.util.retry.Retry**: リトライ機能は存在するが、非同期環境での使用には制約がある
- **同期処理の制限**: `asyncio`イベントループとの統合に追加の複雑性が発生

#### HTTP/2サポート

- **httpx**: HTTP/2プロトコルをネイティブサポート（`http2=True`オプション）
- **requests**: HTTP/1.1のみサポート

#### Python 3.13互換性

- **httpx**: Python 3.13で完全にテスト済み、公式ドキュメントで3.13サポートを明記
- **requests**: Python 3.13で動作するが、新機能（ジェネリクス型注釈等）の活用は限定的

#### パフォーマンス

- 2025年のベンチマーク結果: `asyncio`と`httpx`の組み合わせにより、同期的な`requests`と比較して**5倍の高速化**が達成可能（複数の同時リクエスト処理時）
- 本サンプルエージェントでは逐次実行のため、パフォーマンス差は限定的だが、将来的な拡張（複数通貨ペアの並列取得等）を考慮

### Alternatives Considered

#### requests
- **長所**: 最も普及したHTTPクライアント、シンプルなAPI、豊富なドキュメント
- **短所**: 非同期未対応、`BaseMemberAgent`の非同期メソッドとの統合に制約
- **不採用理由**: 親仕様の非同期要件に適合しない

#### aiohttp
- **長所**: 非同期HTTPクライアント・サーバーの統合フレームワーク
- **短所**: httpxより複雑、サーバー機能は本サンプルで不要、依存関係が多い
- **不採用理由**: シンプルさを重視するサンプルコードとしては過剰な機能

### Implementation Notes

#### TOML設定統合

```toml
[agent.tool_settings.bitbank_api]
base_url = "https://public.bitbank.cc"
timeout_seconds = 30
max_retries = 3
retry_delay_seconds = 1.0
# Article 9準拠: ハードコード禁止、すべて環境変数またはTOML設定から読み込み
```

#### エクスポネンシャルバックオフ実装

```python
async def _fetch_with_retry(
    self,
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> dict[str, Any]:
    """Fetch data with exponential backoff retry logic.

    Implements Article 9 compliant error handling:
    - NO implicit fallbacks
    - Explicit error propagation
    - Clear error messages with resolution guidance
    """
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit - retry with backoff
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
            # Non-retryable HTTP error - propagate immediately
            raise
        except httpx.TimeoutException:
            # Timeout - retry if attempts remain
            if attempt < max_retries:
                delay = initial_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            raise
    # Max retries exceeded - explicit error
    raise MaxRetriesExceededError(
        f"Failed to fetch {url} after {max_retries} retries. "
        f"Check network connection or bitbank API status."
    )
```

#### HTTP 429ハンドリング

```python
if response.status_code == 429:
    retry_after = response.headers.get("Retry-After", "60")
    raise RateLimitError(
        f"Rate limit exceeded. Retry after {retry_after} seconds. "
        f"Consider reducing request frequency in TOML config."
    )
```

## 3. 統計分析ライブラリ

### Decision

**numpy**（バージョン: >=1.26.0、Python 3.13互換）を採用します。

### Rationale

#### 基本統計計算の要件

本サンプルエージェントで実装する統計機能：

- **平均（mean）**: 終値（close）の平均値
- **標準偏差（std）**: 価格のボラティリティ指標
- **最大値/最小値（max/min）**: 期間内の高値・安値
- **中央値（median）**: 外れ値の影響を受けにくい中心傾向指標

#### numpyの優位性

**パフォーマンス**:
- C言語実装による高速な配列演算（pandasのバックエンドとしても使用）
- 1000件のOHLCVデータ処理で、純粋Pythonループと比較して**10～100倍高速**

**メモリ効率**:
- NumPy配列は連続メモリ配列を使用し、Pythonリストより**5～10倍省メモリ**
- 大量のローソク足データ（1日分の1分足 = 1440件）でも効率的に処理

**統計関数の豊富さ**:
```python
import numpy as np

# OHLCV配列から終値を抽出
closes = np.array([candle[3] for candle in ohlcv_data])

# 統計計算（単一行で実行可能）
stats = {
    "mean": np.mean(closes),
    "std": np.std(closes),
    "max": np.max(closes),
    "min": np.min(closes),
    "median": np.median(closes),
}
```

**Python 3.13互換性**:
- NumPy 1.26.0以降でPython 3.13をサポート
- 2025年時点で安定バージョン（1.26.x）が利用可能

#### pandasとの比較

**pandas**:
- **長所**: DataFrame APIの直感的な操作、時系列データ処理に特化した機能（resample, rolling等）
- **短所**:
  - 本サンプルでは過剰な機能（DataFrameの構造化データは不要）
  - 依存関係が多い（numpy, python-dateutil, pytz等）
  - インポート時間が長い（約0.5秒 vs numpyの約0.1秒）
- **ユースケース**: 複雑な時系列分析や複数データソースの統合が必要な場合は有用

**numpy**:
- **長所**:
  - 軽量で高速（シンプルな統計計算に最適）
  - 依存関係なし（標準的な数値計算ライブラリ）
  - 学習曲線が低い（配列演算の基本概念のみ）
- **短所**: DataFrame的な構造化データ管理機能なし
- **ユースケース**: 基本的な数値計算と統計分析（本サンプルに該当）

#### Python 3.13での性能

- Python 3.13のベンチマーク結果では、データサイエンス系のワークロード（numpy/pandas）の性能向上は控えめ（Web系フレームワークと比較して）
- しかし、numpy自体のC実装による高速性は変わらず、本サンプルの要件には十分

### Alternatives Considered

#### pandas
- **不採用理由**: 基本統計計算のみのサンプルには過剰な機能、依存関係の追加、インポート時間の増加
- **採用を検討すべきケース**: 時系列リサンプリング、移動平均、複数通貨ペアの相関分析等を実装する場合

#### statistics（標準ライブラリ）
- **長所**: 外部依存なし、Pythonに同梱
- **短所**: 配列演算に最適化されておらず、1000件以上のデータで**10～100倍遅い**
- **不採用理由**: パフォーマンス要件を満たさない

#### scipy.stats
- **長所**: 高度な統計分析機能（分布、検定、回帰等）
- **短所**: 本サンプルでは不要な機能、依存関係追加
- **不採用理由**: 基本統計のみの要件には過剰

### Implementation Notes

#### OHLCV配列の処理パターン

```python
import numpy as np
from typing import Any

def calculate_statistics(ohlcv_data: list[list[float]]) -> dict[str, float]:
    """Calculate basic statistics from OHLCV candlestick data.

    Args:
        ohlcv_data: List of [open, high, low, close, volume, timestamp]

    Returns:
        Dictionary with statistical metrics

    Raises:
        ValueError: If ohlcv_data is empty or malformed
    """
    if not ohlcv_data:
        raise ValueError(
            "Error: Empty OHLCV data. "
            "Check API response or date parameter in TOML config."
        )

    # Extract close prices (index 3 in OHLCV)
    closes = np.array([candle[3] for candle in ohlcv_data], dtype=np.float64)

    # Extract volumes (index 4 in OHLCV)
    volumes = np.array([candle[4] for candle in ohlcv_data], dtype=np.float64)

    return {
        "price_mean": float(np.mean(closes)),
        "price_std": float(np.std(closes)),
        "price_max": float(np.max(closes)),
        "price_min": float(np.min(closes)),
        "price_median": float(np.median(closes)),
        "volume_total": float(np.sum(volumes)),
        "volume_mean": float(np.mean(volumes)),
        "data_points": len(ohlcv_data),
    }
```

#### 大量データの効率的処理

```python
# 1日分の1分足データ（1440件）のメモリ使用量
# numpy配列: 約11KB (1440 * 6 fields * 8 bytes)
# Pythonリスト: 約57KB (オブジェクトオーバーヘッド含む)
```

## 4. エラーハンドリングパターン

### Decision

以下の4層のエラーハンドリング戦略を採用します：

1. **入力バリデーション層**: TOML設定とユーザー入力の検証
2. **ネットワーク層**: HTTP通信エラー（タイムアウト、接続エラー、レート制限）
3. **レスポンス検証層**: JSON構造とbitbank APIレスポンスのスキーマ検証
4. **データ処理層**: 統計計算時のエラー（空配列、無効な数値）

### Rationale

#### Article 9（Data Accuracy Mandate）準拠の徹底

**NO 暗黙的フォールバック**:
- エラー発生時にデフォルト値を返さない
- 部分的な結果でエラーを隠蔽しない
- すべてのエラーで明示的な`MemberAgentResult.error()`を返す

**NO ハードコーディング**:
- エラーメッセージのフォーマット文字列も定数化（`ERROR_MESSAGES`辞書）
- すべての設定値をTOMLまたは環境変数から読み込み

**明示的なエラー伝播**:
- 各層で適切な例外型を定義（`BitbankAPIError`, `ValidationError`, `StatisticsError`）
- エラーメッセージに解決策を含める（例: "Check network connection"）

#### 4層エラーハンドリング詳細

##### 1. 入力バリデーション層

```python
from pydantic import BaseModel, Field, field_validator

class BitbankToolConfig(BaseModel):
    """bitbank API tool configuration with strict validation."""

    pair: str = Field(
        default="btc_jpy",
        description="Trading pair (e.g., btc_jpy, eth_jpy)"
    )
    candle_type: str = Field(
        default="1hour",
        description="Candlestick type (1min, 5min, 15min, 30min, 1hour, 4hour, 8hour, 12hour, 1day, 1week, 1month)"
    )
    date: str = Field(
        default="2025",
        description="Date in YYYYMMDD (short-term) or YYYY (long-term) format"
    )

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        """Validate trading pair format."""
        valid_pairs = ["btc_jpy", "eth_jpy", "xrp_jpy", "ltc_jpy", "bcc_jpy"]
        if v not in valid_pairs:
            raise ValueError(
                f"Error: Invalid pair '{v}'. "
                f"Valid pairs: {', '.join(valid_pairs)}. "
                f"Update 'pair' in TOML config [agent.tool_settings.bitbank_api]."
            )
        return v

    @field_validator("candle_type")
    @classmethod
    def validate_candle_type(cls, v: str) -> str:
        """Validate candlestick type."""
        valid_types = [
            "1min", "5min", "15min", "30min",
            "1hour", "4hour", "8hour", "12hour",
            "1day", "1week", "1month"
        ]
        if v not in valid_types:
            raise ValueError(
                f"Error: Invalid candle_type '{v}'. "
                f"Valid types: {', '.join(valid_types)}. "
                f"Update 'candle_type' in TOML config."
            )
        return v
```

##### 2. ネットワーク層

```python
import httpx

async def _fetch_ticker(self, pair: str) -> dict[str, Any]:
    """Fetch ticker data with comprehensive error handling.

    Raises:
        BitbankAPIError: On HTTP errors, timeouts, or rate limits
    """
    url = f"{self.base_url}/{pair}/ticker"

    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BitbankAPIError(
                f"Error: Pair '{pair}' not found. "
                f"Valid pairs: btc_jpy, eth_jpy, xrp_jpy. "
                f"Update TOML config."
            )
        elif e.response.status_code == 429:
            raise BitbankAPIError(
                f"Error: Rate limit exceeded. "
                f"Retry after 60 seconds or reduce request frequency."
            )
        elif 500 <= e.response.status_code < 600:
            raise BitbankAPIError(
                f"Error: bitbank server error ({e.response.status_code}). "
                f"Retry later or check https://status.bitbank.cc"
            )
        else:
            raise BitbankAPIError(
                f"Error: HTTP {e.response.status_code}. "
                f"Details: {e.response.text}"
            )

    except httpx.TimeoutException:
        raise BitbankAPIError(
            f"Error: Request timeout after {self.timeout.read}s. "
            f"Check network connection or increase timeout_seconds in TOML."
        )

    except httpx.NetworkError as e:
        raise BitbankAPIError(
            f"Error: Network error - {str(e)}. "
            f"Check internet connection."
        )
```

##### 3. レスポンス検証層（Pydantic Model使用）

```python
from pydantic import BaseModel, Field

class TickerResponse(BaseModel):
    """bitbank ticker API response schema."""

    sell: str = Field(..., description="Lowest sell price")
    buy: str = Field(..., description="Highest buy price")
    high: str = Field(..., description="24h highest price")
    low: str = Field(..., description="24h lowest price")
    last: str = Field(..., description="Latest price")
    vol: str = Field(..., description="24h volume")
    timestamp: int = Field(..., description="Unix timestamp (ms)")

class TickerAPIResponse(BaseModel):
    """bitbank API wrapper response."""

    success: int = Field(..., description="Success flag (1=success, 0=error)")
    data: TickerResponse

def _validate_ticker_response(self, json_data: dict[str, Any]) -> TickerResponse:
    """Validate ticker response with Pydantic.

    Raises:
        ValidationError: On schema mismatch or missing fields
    """
    try:
        response = TickerAPIResponse.model_validate(json_data)
        if response.success != 1:
            raise BitbankAPIError(
                f"Error: bitbank API returned error. "
                f"Response: {json_data}"
            )
        return response.data

    except ValidationError as e:
        raise BitbankAPIError(
            f"Error: Invalid API response format. "
            f"Expected fields: sell, buy, high, low, last, vol, timestamp. "
            f"Validation errors: {e.errors()}"
        )
```

##### 4. データ処理層

```python
def _calculate_statistics(self, ohlcv_data: list[list[float]]) -> dict[str, float]:
    """Calculate statistics with error handling.

    Raises:
        StatisticsError: On empty data or calculation failures
    """
    if not ohlcv_data:
        raise StatisticsError(
            "Error: Empty OHLCV data. "
            "Check API response or date parameter in TOML config."
        )

    try:
        closes = np.array([candle[3] for candle in ohlcv_data], dtype=np.float64)

        # Check for invalid values
        if np.any(np.isnan(closes)) or np.any(np.isinf(closes)):
            raise StatisticsError(
                "Error: Invalid numeric values in OHLCV data (NaN or Inf). "
                "Check bitbank API response quality."
            )

        return {
            "price_mean": float(np.mean(closes)),
            "price_std": float(np.std(closes)),
            "price_max": float(np.max(closes)),
            "price_min": float(np.min(closes)),
        }

    except (IndexError, TypeError) as e:
        raise StatisticsError(
            f"Error: Malformed OHLCV data structure. "
            f"Expected format: [[open, high, low, close, volume, timestamp], ...]. "
            f"Details: {str(e)}"
        )
```

### Alternatives Considered

#### try-except-pass（サイレントエラー）
- **不採用理由**: Article 9で明示的に禁止（NO サイレントエラー）

#### デフォルト値へのフォールバック
```python
# 禁止パターン
def get_ticker(pair: str) -> dict:
    try:
        return fetch_ticker(pair)
    except Exception:
        return {"last": "0.0"}  # 暗黙的フォールバック（Article 9違反）
```
- **不採用理由**: Article 9で禁止（NO 暗黙的フォールバック）

#### ロギングのみでエラー継続
```python
# 禁止パターン
try:
    data = fetch_data()
except Exception as e:
    logger.error(f"Error: {e}")
    data = []  # エラーを隠蔽（Article 9違反）
```
- **不採用理由**: エラーの隠蔽は禁止、明示的なエラー結果を返す

### Implementation Notes

#### エラーメッセージのベストプラクティス

**推奨フォーマット**（親仕様FR-019準拠）:
```
Error: <エラー概要>. <詳細説明または対処方法>
```

**実装例**:
```python
ERROR_MESSAGES = {
    "INVALID_PAIR": (
        "Error: Invalid pair '{pair}'. "
        "Valid pairs: {valid_pairs}. "
        "Update 'pair' in TOML config [agent.tool_settings.bitbank_api]."
    ),
    "NETWORK_TIMEOUT": (
        "Error: Request timeout after {timeout}s. "
        "Check network connection or increase timeout_seconds in TOML."
    ),
    "EMPTY_DATA": (
        "Error: Empty OHLCV data. "
        "Check API response or date parameter in TOML config."
    ),
}

# 使用例
raise BitbankAPIError(
    ERROR_MESSAGES["INVALID_PAIR"].format(
        pair=pair,
        valid_pairs="btc_jpy, eth_jpy, xrp_jpy"
    )
)
```

#### カスタム例外クラス

```python
class BitbankAgentError(Exception):
    """Base exception for bitbank agent errors."""
    pass

class BitbankAPIError(BitbankAgentError):
    """HTTP/API related errors."""
    pass

class ValidationError(BitbankAgentError):
    """Input validation errors."""
    pass

class StatisticsError(BitbankAgentError):
    """Data processing/calculation errors."""
    pass
```

## 5. TOML設定構造

### Decision

以下のTOML設定構造を採用します：

```toml
# bitbank_agent.toml
[agent]
name = "bitbank-api-agent"
type = "custom"  # 018-custom-member仕様で固定
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 2048

system_instruction = """
あなたはbitbank Public APIを使用して暗号資産の価格データを取得・分析する専門エージェントです。
ユーザーの質問に対して、ticker（リアルタイム価格）またはcandlestick（時系列OHLCV）データを取得し、
基本的な統計分析結果を日本語で分かりやすく説明してください。
"""

description = "bitbank Public API integration sample agent for cryptocurrency price analysis"

# カスタムエージェント動的ロード設定（FR-020）
[agent.metadata.plugin]
agent_module = "examples.custom_agents.bitbank.agent"  # 推奨: モジュールパス方式
# path = "/path/to/bitbank_agent.py"  # 代替: ファイルパス方式
agent_class = "BitbankAPIAgent"

# リトライ設定
[agent.retry_config]
max_retries = 3
initial_delay = 1.0
backoff_factor = 2.0

# bitbank API固有設定
[agent.tool_settings.bitbank_api]
base_url = "https://public.bitbank.cc"
timeout_seconds = 30
max_retries = 3
retry_delay_seconds = 1.0

# デフォルトパラメータ
pair = "btc_jpy"
candle_type = "1hour"
date = "2025"
```

### Rationale

#### Article 9準拠の保証

**NO ハードコーディング**:
- API base URLは`base_url`で明示的に設定
- タイムアウト値は`timeout_seconds`で設定
- リトライ設定は`retry_config`セクションで集中管理

**明示的データソース**:
- すべての設定項目に`description`を付与（TOML標準ではコメントだが、Pydantic Modelで検証）
- 環境変数（`GOOGLE_API_KEY`）とTOML設定の明確な分離

**適切なエラー伝播**:
- TOML構文エラー時はCLI起動時に即座にエラー表示
- Pydanticバリデーションエラーでフィールド別詳細表示

#### 親仕様インターフェース準拠

**`type = "custom"`固定**:
- 018-custom-member仕様の要件（2025-11-20明確化）
- 独自識別子（"bitbank_api"等）は使用せず、`name`で識別

**`agent.metadata.plugin`セクション**:
- `agent_module`（推奨）: 本番環境・SDK配布用
- `path`（代替）: 開発プロトタイピング用
- `agent_class`: クラス名を明示

#### 設定の階層化

**エージェント基本設定** (`[agent]`):
- AIモデル設定（model, temperature, max_tokens）
- system_instruction（エージェントの動作指示）

**リトライ設定** (`[agent.retry_config]`):
- 親仕様の`RetryConfig`モデルに準拠

**ツール固有設定** (`[agent.tool_settings.bitbank_api]`):
- bitbank API専用パラメータ
- 他のカスタムツール設定と分離

### Alternatives Considered

#### 環境変数でAPI設定を管理
```bash
export BITBANK_BASE_URL="https://public.bitbank.cc"
export BITBANK_TIMEOUT=30
```
- **不採用理由**:
  - TOML設定の方が一覧性が高い
  - 環境変数はプロバイダー認証（`GOOGLE_API_KEY`等）に限定すべき
  - Article 9では環境変数とTOML設定の両方を認めているが、本サンプルではTOML統合を優先

#### JSON設定ファイル
- **不採用理由**: MixSeek-Coreの標準フォーマットはTOML（親仕様で明記）

#### YAML設定ファイル
- **不採用理由**: Pythonの標準ライブラリに含まれない（`tomllib`は3.11+で標準）

### Implementation Notes

#### TOML読み込みパターン

```python
import tomllib
from pathlib import Path
from pydantic import ValidationError

from mixseek.models.member_agent import MemberAgentConfig

def load_agent_config(config_path: str) -> MemberAgentConfig:
    """Load and validate agent configuration from TOML file.

    Args:
        config_path: Path to TOML configuration file

    Returns:
        Validated MemberAgentConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        TOMLDecodeError: If TOML syntax is invalid
        ValidationError: If config schema is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(
            f"Error: Config file not found: {config_path}. "
            f"Check file path in --config option."
        )

    try:
        with open(config_file, "rb") as f:
            toml_data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(
            f"Error: Invalid TOML syntax in {config_path}. "
            f"Line {e.lineno}: {e.msg}. "
            f"Fix TOML syntax and retry."
        )

    try:
        return MemberAgentConfig.model_validate(toml_data.get("agent", {}))
    except ValidationError as e:
        error_details = "\n".join([
            f"  - {err['loc'][0]}: {err['msg']}"
            for err in e.errors()
        ])
        raise ValueError(
            f"Error: Invalid configuration in {config_path}.\n"
            f"Validation errors:\n{error_details}\n"
            f"Fix configuration and retry."
        )
```

#### デフォルト値の管理

```python
from pydantic import BaseModel, Field

class BitbankToolConfig(BaseModel):
    """bitbank API tool configuration with explicit defaults."""

    base_url: str = Field(
        default="https://public.bitbank.cc",
        description="bitbank API base URL (change for testing/mocking)"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries for failed requests"
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Initial delay between retries (exponential backoff applied)"
    )
    pair: str = Field(
        default="btc_jpy",
        description="Default trading pair"
    )
    candle_type: str = Field(
        default="1hour",
        description="Default candlestick type"
    )
    date: str = Field(
        default="2025",
        description="Default date for candlestick data (YYYY or YYYYMMDD)"
    )
```

## 実装チェックリスト

### Article 9（Data Accuracy Mandate）準拠確認

- [ ] **NO ハードコーディング**: すべての設定値をTOMLまたは環境変数から読み込み
- [ ] **NO 暗黙的フォールバック**: エラー時のデフォルト値自動適用なし
- [ ] **NO 推測・補完**: 無効な入力を自動修正しない
- [ ] **明示的データソース**: TOML設定で`base_url`, `timeout_seconds`等を明示
- [ ] **適切なエラー伝播**: すべてのエラーで明確なメッセージと解決策提示

### 親仕様インターフェース準拠確認

- [ ] **BaseMemberAgent継承**: `BaseMemberAgent`を継承し`execute()`メソッドを実装
- [ ] **TOML設定**: `type = "custom"`固定、`agent.metadata.plugin`セクション設定
- [ ] **動的ロード機構**: `agent_module`（推奨）または`path`（代替）による動的ロード
- [ ] **非同期処理**: `async def execute()`の実装
- [ ] **MemberAgentResult返却**: 成功時は`MemberAgentResult.success()`、エラー時は`MemberAgentResult.error()`

### 技術選定確認

- [ ] **httpx**: 非同期HTTPクライアント、タイムアウト・リトライ設定
- [ ] **numpy**: 統計計算ライブラリ（平均、標準偏差、最大/最小値）
- [ ] **Pydantic Model**: APIレスポンスのスキーマ検証
- [ ] **4層エラーハンドリング**: 入力検証、ネットワーク、レスポンス検証、データ処理

## 次のステップ

1. **plan.md作成**: 本research.mdの決定事項に基づき、実装計画を策定
2. **tasks.md生成**: `/speckit.tasks`コマンドで実装タスクを自動生成
3. **プロトタイプ実装**: `examples/custom_agents/bitbank/`ディレクトリにサンプルコード作成
4. **テスト作成**: Article 3（Test-First Imperative）に従い、実装前にテストを作成
5. **ドキュメント作成**: `docs/custom-agent-guide.md`にステップバイステップガイドを追加

## 参考資料

### 公式ドキュメント

- [bitbank Public API Documentation](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-api.md)
- [httpx Documentation](https://www.python-httpx.org/)
- [NumPy Documentation](https://numpy.org/doc/stable/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### 親仕様

- [specs/009-member/spec.md](../009-member/spec.md) - 標準Member Agentバンドルとカスタムエージェント作成の基本要件
- [specs/018-custom-member/spec.md](./spec.md) - Custom Member Agent Development仕様
- [.specify/memory/constitution.md](../../.specify/memory/constitution.md) - Article 9（Data Accuracy Mandate）

### 実装例

- [examples/custom_agents/simple/simple_agent.py](../../examples/custom_agents/simple/simple_agent.py) - シンプルなカスタムエージェント実装例
- [src/mixseek/agents/member/base.py](../../src/mixseek/agents/member/base.py) - BaseMemberAgent抽象基底クラス
