# Data Model: bitbank Public API連携サンプルエージェント

**Feature**: 133-custom-member-api
**Date**: 2025-11-20
**Parent Spec**: specs/018-custom-member/spec.md

## Overview

本ドキュメントは、bitbank Public API連携サンプルエージェントで使用するPydantic Modelの詳細設計を定義します。すべてのモデルはArticle 16（Python Type Safety Mandate）に準拠し、包括的な型注釈と静的型チェックを必須とします。

## Entity Models

### 1. BitbankTickerData

通貨ペアの最新価格情報を表すモデル（bitbank APIの`/{pair}/ticker`レスポンスから取得）。

```python
from pydantic import BaseModel, Field
from datetime import datetime

class BitbankTickerData(BaseModel):
    """bitbank ticker APIレスポンスのデータモデル

    Attributes:
        pair: 通貨ペア識別子（例: "btc_jpy", "xrp_jpy"）
        buy: 買値（最良買い注文価格）
        sell: 売値（最良売り注文価格）
        high: 24時間高値
        low: 24時間低値
        last: 最終取引価格
        vol: 24時間取引量（基軸通貨）
        timestamp: データ取得時刻（UNIXタイムスタンプ、ミリ秒）
        timestamp_dt: データ取得時刻（datetime、自動変換）
    """

    pair: str = Field(..., description="Currency pair (e.g., btc_jpy)")
    buy: str = Field(..., description="Best buy price")
    sell: str = Field(..., description="Best sell price")
    high: str = Field(..., description="24-hour high price")
    low: str = Field(..., description="24-hour low price")
    last: str = Field(..., description="Last traded price")
    vol: str = Field(..., description="24-hour volume")
    timestamp: int = Field(..., description="UNIX timestamp in milliseconds")

    @property
    def timestamp_dt(self) -> datetime:
        """タイムスタンプをdatetimeオブジェクトに変換"""
        return datetime.fromtimestamp(self.timestamp / 1000.0)

    @property
    def buy_float(self) -> float:
        """買値をfloatに変換"""
        return float(self.buy)

    @property
    def sell_float(self) -> float:
        """売値をfloatに変換"""
        return float(self.sell)

    @property
    def last_float(self) -> float:
        """最終取引価格をfloatに変換"""
        return float(self.last)

    @property
    def vol_float(self) -> float:
        """取引量をfloatに変換"""
        return float(self.vol)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pair": "btc_jpy",
                    "buy": "10500000",
                    "sell": "10510000",
                    "high": "10600000",
                    "low": "10400000",
                    "last": "10505000",
                    "vol": "1234.5678",
                    "timestamp": 1700000000000,
                }
            ]
        }
    }
```

### 2. BitbankCandlestickOHLCV

ロウソク足データの単一エントリを表すモデル。

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import numpy as np

class BitbankCandlestickOHLCV(BaseModel):
    """単一のOHLCVデータエントリ

    Attributes:
        open: 始値
        high: 高値
        low: 安値
        close: 終値
        volume: 出来高
        timestamp: UNIXタイムスタンプ（ミリ秒）
    """

    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Trading volume")
    timestamp: int = Field(..., description="UNIX timestamp in milliseconds")

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, values: dict) -> float:
        """高値が始値・終値以上であることを検証"""
        if "open" in values and v < values["open"]:
            raise ValueError("High price must be >= open price")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, values: dict) -> float:
        """安値が始値・終値以下であることを検証"""
        if "open" in values and v > values["open"]:
            raise ValueError("Low price must be <= open price")
        return v

    @property
    def timestamp_dt(self) -> datetime:
        """タイムスタンプをdatetimeオブジェクトに変換"""
        return datetime.fromtimestamp(self.timestamp / 1000.0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "open": 10500000.0,
                    "high": 10520000.0,
                    "low": 10490000.0,
                    "close": 10510000.0,
                    "volume": 123.456,
                    "timestamp": 1700000000000,
                }
            ]
        }
    }
```

### 3. BitbankCandlestickData

時系列OHLCV（Open/High/Low/Close/Volume）データのコレクションを表すモデル。

```python
from typing import Literal
from pydantic import BaseModel, Field

CandleType = Literal[
    "1min", "5min", "15min", "30min", "1hour",
    "4hour", "8hour", "12hour", "1day", "1week", "1month"
]

class BitbankCandlestickData(BaseModel):
    """bitbank candlestick APIレスポンスのデータモデル

    Attributes:
        pair: 通貨ペア識別子
        candle_type: ロウソク足の時間間隔
        ohlcv: OHLCVデータのリスト（時系列順）
        count: データ件数
    """

    pair: str = Field(..., description="Currency pair")
    candle_type: CandleType = Field(..., description="Candlestick interval")
    ohlcv: list[BitbankCandlestickOHLCV] = Field(
        ..., description="List of OHLCV data entries"
    )

    @property
    def count(self) -> int:
        """データ件数"""
        return len(self.ohlcv)

    @property
    def closes(self) -> np.ndarray:
        """終値の配列（numpy）"""
        return np.array([entry.close for entry in self.ohlcv])

    @property
    def volumes(self) -> np.ndarray:
        """出来高の配列（numpy）"""
        return np.array([entry.volume for entry in self.ohlcv])

    @property
    def timestamps(self) -> np.ndarray:
        """タイムスタンプの配列（numpy）"""
        return np.array([entry.timestamp for entry in self.ohlcv])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pair": "btc_jpy",
                    "candle_type": "1hour",
                    "ohlcv": [
                        {
                            "open": 10500000.0,
                            "high": 10520000.0,
                            "low": 10490000.0,
                            "close": 10510000.0,
                            "volume": 123.456,
                            "timestamp": 1700000000000,
                        }
                    ],
                }
            ]
        }
    }
```

### 4. FinancialSummary

金融指標分析結果を表すモデル。

```python
from pydantic import BaseModel, Field, field_validator
import numpy as np

class FinancialSummary(BaseModel):
    """投資家向け金融指標分析結果

    Attributes:
        annualized_return: 年率リターン（複利計算）
        annualized_volatility: 年率ボラティリティ
        max_drawdown: 最大ドローダウン（Running maximum method）
        sharpe_ratio: シャープレシオ（リスクフリーレート考慮）
        sortino_ratio: ソルティーノレシオ（下方リスクのみ）
        return_skewness: リターン分布の歪度
        return_kurtosis: リターン分布の尖度
        total_return: 期間全体のリターン
        start_price: 期初価格
        end_price: 期末価格
        mean_price: 平均価格
        total_volume: 総取引量
        trading_days: 取引日数
    """

    annualized_return: float = Field(..., description="Annualized return (compound)")
    annualized_volatility: float = Field(..., ge=0, description="Annualized volatility")
    max_drawdown: float = Field(..., le=0, description="Maximum drawdown (negative value)")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    return_skewness: float = Field(..., description="Return distribution skewness")
    return_kurtosis: float = Field(..., description="Return distribution kurtosis")
    total_return: float = Field(..., description="Total return for the period")
    start_price: float = Field(..., gt=0, description="Starting price")
    end_price: float = Field(..., gt=0, description="Ending price")
    mean_price: float = Field(..., gt=0, description="Mean price")
    total_volume: float = Field(..., ge=0, description="Total trading volume")
    trading_days: int = Field(..., gt=0, description="Number of trading days")

    @field_validator("annualized_return", "annualized_volatility", "sharpe_ratio", "sortino_ratio")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        """金融指標が有限であることを検証"""
        if not np.isfinite(v):
            raise ValueError(f"Financial metric must be a finite number, got {v}")
        return v

    @field_validator("end_price")
    @classmethod
    def validate_end_price(cls, v: float, values: dict) -> float:
        """期末価格が正の値であることを検証"""
        if "start_price" in values and values["start_price"] <= 0:
            raise ValueError("Start price must be positive")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "annualized_return": 0.152,  # 15.2%
                    "annualized_volatility": 0.342,  # 34.2%
                    "max_drawdown": -0.189,  # -18.9%
                    "sharpe_ratio": 0.441,
                    "sortino_ratio": 0.623,
                    "return_skewness": -0.123,
                    "return_kurtosis": 2.456,
                    "total_return": 0.0192,  # 1.92%
                    "start_price": 10400000.0,
                    "end_price": 10600000.0,
                    "mean_price": 10505000.0,
                    "total_volume": 1234.5678,
                    "trading_days": 24,
                }
            ]
        }
    }
```

## Configuration Models

### 5. BitbankAPIConfig

bitbank API設定を表すモデル（TOML設定からロード、Article 9準拠）。

```python
from pydantic import BaseModel, Field, field_validator

class BitbankAPIConfig(BaseModel):
    """bitbank API設定（Article 9準拠）

    Attributes:
        base_url: API base URL（TOML必須）
        timeout_seconds: タイムアウト（秒）
        max_retries: 最大リトライ回数
        retry_delay_seconds: リトライ待機時間（秒、エクスポネンシャルバックオフの初期値）
        min_request_interval_seconds: 最低リクエスト間隔（秒、レート制限対応）
        supported_pairs: サポート通貨ペアリスト
        supported_candle_types: サポートするcandlestickタイプリスト
        risk_free_rate: リスクフリーレート（シャープレシオ計算用）
        trading_days_per_year: 年間取引日数（年率換算用）
        minimum_acceptable_return: 最低許容リターン（ソルティーノレシオMAR）
    """

    base_url: str = Field(..., description="API base URL (TOML required)")
    timeout_seconds: int = Field(30, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(1, gt=0, description="Initial retry delay in seconds")
    min_request_interval_seconds: int = Field(
        1, gt=0, description="Minimum interval between requests in seconds"
    )
    supported_pairs: list[str] = Field(
        default_factory=list, description="List of supported currency pairs"
    )
    supported_candle_types: list[str] = Field(
        default_factory=list, description="List of supported candlestick types"
    )
    risk_free_rate: float = Field(0.001, ge=0, description="Risk-free rate for Sharpe ratio (default: 0.1%)")
    trading_days_per_year: int = Field(365, gt=0, description="Trading days per year for annualization")
    minimum_acceptable_return: float = Field(0.0, description="Minimum acceptable return for Sortino ratio (MAR)")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """base URLがhttpsで始まることを検証"""
        if not v.startswith("https://"):
            raise ValueError("base_url must start with https://")
        if v.endswith("/"):
            raise ValueError("base_url must not end with /")
        return v

    @field_validator("supported_pairs")
    @classmethod
    def validate_supported_pairs(cls, v: list[str]) -> list[str]:
        """通貨ペア形式の検証（小文字、アンダースコア区切り）"""
        for pair in v:
            if not pair.islower() or "_" not in pair:
                raise ValueError(
                    f"Invalid pair format: {pair}. Must be lowercase with underscore (e.g., btc_jpy)"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "base_url": "https://public.bitbank.cc",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1,
                    "min_request_interval_seconds": 1,
                    "supported_pairs": ["btc_jpy", "xrp_jpy", "eth_jpy"],
                    "supported_candle_types": ["1hour", "1day", "1week"],
                    "risk_free_rate": 0.001,
                    "trading_days_per_year": 365,
                    "minimum_acceptable_return": 0.0,
                }
            ]
        }
    }
```

## Response Models

### 6. MemberAgentResult

親仕様で定義された標準応答フォーマット（`BaseMemberAgent.execute()`の戻り値）。

```python
from pydantic import BaseModel, Field

class MemberAgentResult(BaseModel):
    """Member Agentの標準応答フォーマット（親仕様準拠）

    Attributes:
        success: 実行成功フラグ
        content: 応答コンテンツ（Markdown形式推奨）
        metadata: 追加メタデータ（統計データ、エラー詳細など）
    """

    success: bool = Field(..., description="Execution success flag")
    content: str = Field(..., description="Response content (Markdown recommended)")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "content": "# BTC/JPY Ticker Data\n\n- Buy: 10,500,000 JPY\n- Sell: 10,510,000 JPY",
                    "metadata": {"pair": "btc_jpy", "timestamp": 1700000000000},
                }
            ]
        }
    }
```

## Entity Relationships

```
BitbankAPIAgent
├── BitbankAPIConfig (TOML設定)
│   ├── base_url
│   ├── timeout_seconds
│   ├── max_retries
│   ├── supported_pairs
│   ├── risk_free_rate
│   ├── trading_days_per_year
│   └── minimum_acceptable_return
│
├── BitbankTickerData (リアルタイム価格)
│   ├── pair
│   ├── buy, sell, last
│   └── timestamp
│
├── BitbankCandlestickData (時系列データ)
│   ├── pair
│   ├── candle_type
│   └── ohlcv: list[BitbankCandlestickOHLCV]
│
├── FinancialSummary (金融指標分析結果)
│   ├── annualized_return, annualized_volatility
│   ├── max_drawdown, sharpe_ratio, sortino_ratio
│   ├── return_skewness, return_kurtosis
│   ├── total_return, start_price, end_price
│   └── mean_price, total_volume, trading_days
│
└── MemberAgentResult (標準応答)
    ├── success
    ├── content (Markdown)
    └── metadata
```

## Type Safety Validation

すべてのモデルは以下の型安全性要件を満たします（Article 16準拠）：

1. **包括的な型注釈**: すべてのフィールドに型ヒント
2. **Pydanticバリデーション**: 実行時の型チェックと値検証
3. **mypy準拠**: strict modeでの静的型チェック合格
4. **field_validator**: カスタムバリデーションロジック
5. **json_schema_extra**: ドキュメント生成とサンプルデータ

## Article 9 Compliance

すべての設定値はTOMLファイルまたは環境変数から明示的に取得し、ハードコードを禁止します：

- `BitbankAPIConfig`: TOMLから読み込み（`base_url`、`timeout_seconds`、`risk_free_rate`、`trading_days_per_year`、`minimum_acceptable_return`など）
- `GOOGLE_API_KEY`: 環境変数から読み込み（`os.getenv()`で明示的エラー）
- エラー時のデフォルト値適用なし（明示的例外を発生）
- 金融指標パラメータのハードコード禁止（すべてTOML設定で管理）

## Next Steps

1. **quickstart.md作成**: 開発者向けクイックスタートガイド
2. **plan.md完成**: Technical Contextとアーキテクチャ設計の統合
3. **tasks.md生成**: `/speckit.tasks`で実装タスクを自動生成
