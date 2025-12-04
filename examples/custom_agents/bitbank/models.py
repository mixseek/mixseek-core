"""Pydantic models for bitbank Public API integration (TASK-004).

All models comply with Article 16 (Type Safety Mandate).
"""

from datetime import datetime
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

CandleType = Literal[
    "1min",
    "5min",
    "15min",
    "30min",
    "1hour",
    "4hour",
    "8hour",
    "12hour",
    "1day",
    "1week",
    "1month",
]


class BitbankTickerData(BaseModel):
    """bitbank ticker API response data model."""

    pair: str = Field(..., description="Currency pair")
    buy: str = Field(..., description="Best buy price")
    sell: str = Field(..., description="Best sell price")
    high: str = Field(..., description="24-hour high price")
    low: str = Field(..., description="24-hour low price")
    last: str = Field(..., description="Last traded price")
    vol: str = Field(..., description="24-hour volume")
    timestamp: int = Field(..., description="UNIX timestamp in milliseconds")

    @property
    def timestamp_dt(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp / 1000.0)

    @property
    def buy_float(self) -> float:
        """Convert buy price to float."""
        return float(self.buy)

    @property
    def sell_float(self) -> float:
        """Convert sell price to float."""
        return float(self.sell)

    @property
    def last_float(self) -> float:
        """Convert last traded price to float."""
        return float(self.last)

    @property
    def vol_float(self) -> float:
        """Convert volume to float."""
        return float(self.vol)

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class BitbankCandlestickOHLCV(BaseModel):
    """Single OHLCV data entry."""

    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Trading volume")
    timestamp: int = Field(..., description="UNIX timestamp in milliseconds")

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, info: ValidationInfo) -> float:
        """Validate that high price is >= open price."""
        if "open" in info.data and v < info.data["open"]:
            raise ValueError("High price must be >= open price")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, info: ValidationInfo) -> float:
        """Validate that low price is <= open price."""
        if "open" in info.data and v > info.data["open"]:
            raise ValueError("Low price must be <= open price")
        return v

    @property
    def timestamp_dt(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp / 1000.0)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "open": 10500000.0,
                    "high": 10600000.0,
                    "low": 10400000.0,
                    "close": 10550000.0,
                    "volume": 123.456,
                    "timestamp": 1700000000000,
                }
            ]
        }
    )


class BitbankCandlestickData(BaseModel):
    """bitbank candlestick API response data model."""

    pair: str = Field(..., description="Currency pair")
    candle_type: CandleType = Field(..., description="Candlestick interval")
    ohlcv: list[BitbankCandlestickOHLCV] = Field(..., description="List of OHLCV data entries")

    @property
    def count(self) -> int:
        """Number of data entries."""
        return len(self.ohlcv)

    @property
    def closes(self) -> np.ndarray:
        """Array of closing prices (numpy)."""
        return np.array([entry.close for entry in self.ohlcv])

    @property
    def volumes(self) -> np.ndarray:
        """Array of volumes (numpy)."""
        return np.array([entry.volume for entry in self.ohlcv])

    @property
    def timestamps(self) -> np.ndarray:
        """Array of timestamps (numpy)."""
        return np.array([entry.timestamp for entry in self.ohlcv])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "pair": "btc_jpy",
                    "candle_type": "1hour",
                    "ohlcv": [
                        {
                            "open": 10500000.0,
                            "high": 10600000.0,
                            "low": 10400000.0,
                            "close": 10550000.0,
                            "volume": 123.456,
                            "timestamp": 1700000000000,
                        },
                        {
                            "open": 10550000.0,
                            "high": 10650000.0,
                            "low": 10500000.0,
                            "close": 10600000.0,
                            "volume": 234.567,
                            "timestamp": 1700003600000,
                        },
                    ],
                }
            ]
        }
    )


class FinancialSummary(BaseModel):
    """Financial metrics analysis result for investors."""

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
        """Validate that financial metrics are finite numbers."""
        if not np.isfinite(v):
            raise ValueError(f"Financial metric must be a finite number, got {v}")
        return v

    @field_validator("end_price")
    @classmethod
    def validate_end_price(cls, v: float, info: ValidationInfo) -> float:
        """Validate that end price is positive."""
        if "start_price" in info.data and info.data["start_price"] <= 0:
            raise ValueError("Start price must be positive")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "annualized_return": 0.152,
                    "annualized_volatility": 0.342,
                    "max_drawdown": -0.189,
                    "sharpe_ratio": 0.441,
                    "sortino_ratio": 0.623,
                    "return_skewness": -0.123,
                    "return_kurtosis": 2.456,
                    "total_return": 0.0192,
                    "start_price": 10400000.0,
                    "end_price": 10600000.0,
                    "mean_price": 10505000.0,
                    "total_volume": 1234.5678,
                    "trading_days": 24,
                }
            ]
        }
    )


class FinancialMetricsConfig(BaseModel):
    """Financial metrics calculation settings."""

    risk_free_rate: float = Field(0.001, ge=0, description="Risk-free rate for Sharpe ratio (default: 0.1%)")
    trading_days_per_year: int = Field(365, gt=0, description="Trading days per year for annualization")
    minimum_acceptable_return: float = Field(0.0, description="Minimum acceptable return for Sortino ratio (MAR)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"risk_free_rate": 0.001, "trading_days_per_year": 365, "minimum_acceptable_return": 0.0}]
        }
    )


class BitbankAPIConfig(BaseModel):
    """bitbank API configuration (Article 9 compliant)."""

    base_url: str = Field(..., description="API base URL")
    timeout_seconds: int = Field(30, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(1, gt=0, description="Initial retry delay in seconds")
    min_request_interval_seconds: int = Field(1, gt=0, description="Minimum interval between requests in seconds")
    supported_pairs: list[str] = Field(default_factory=list, description="List of supported currency pairs")
    supported_candle_types: list[str] = Field(default_factory=list, description="List of supported candlestick types")
    financial_metrics: FinancialMetricsConfig = Field(
        default_factory=FinancialMetricsConfig, description="Financial metrics calculation settings"
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base URL starts with https and does not end with /."""
        if not v.startswith("https://"):
            raise ValueError("base_url must start with https://")
        if v.endswith("/"):
            raise ValueError("base_url must not end with /")
        return v

    @field_validator("supported_pairs")
    @classmethod
    def validate_supported_pairs(cls, v: list[str]) -> list[str]:
        """Validate currency pair format (lowercase, underscore-separated)."""
        for pair in v:
            if not pair.islower() or "_" not in pair:
                raise ValueError(f"Invalid pair format: {pair}. Must be lowercase with underscore (e.g., btc_jpy)")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "base_url": "https://public.bitbank.cc",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1,
                    "min_request_interval_seconds": 1,
                    "supported_pairs": ["btc_jpy", "xrp_jpy", "eth_jpy"],
                    "supported_candle_types": ["1hour", "4hour", "8hour", "12hour", "1day", "1week", "1month"],
                    "financial_metrics": {
                        "risk_free_rate": 0.001,
                        "trading_days_per_year": 365,
                        "minimum_acceptable_return": 0.0,
                    },
                }
            ]
        }
    )


__all__ = [
    "BitbankTickerData",
    "BitbankCandlestickOHLCV",
    "BitbankCandlestickData",
    "FinancialSummary",
    "FinancialMetricsConfig",
    "BitbankAPIConfig",
    "CandleType",
]
