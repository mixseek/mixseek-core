"""Tool functions for bitbank API integration (TASK-010, TASK-012, TASK-014).

All tools comply with Article 9 (Data Accuracy Mandate) and Article 16 (Type Safety).
"""

import numpy as np

from examples.custom_agents.bitbank.client import BitbankAPIClient
from examples.custom_agents.bitbank.models import (
    BitbankAPIConfig,
    BitbankCandlestickData,
    BitbankCandlestickOHLCV,
    BitbankTickerData,
    FinancialSummary,
)


async def get_ticker_data(pair: str, config: BitbankAPIConfig) -> BitbankTickerData:
    """Get ticker data for a currency pair (TASK-010: FR-001).

    Args:
        pair: Currency pair (e.g., "btc_jpy").
        config: bitbank API configuration.

    Returns:
        BitbankTickerData model.

    Raises:
        ValueError: If pair is invalid.
        RuntimeError: On API errors.
    """
    # Validate currency pair
    if pair not in config.supported_pairs:
        raise ValueError(f"Invalid currency pair: {pair}. Supported pairs: {', '.join(config.supported_pairs)}")

    # Call API
    client = BitbankAPIClient(config)
    response = await client.get_ticker(pair)

    # Parse response
    if response.get("success") != 1:
        raise RuntimeError(f"API returned error: {response}")

    data = response.get("data", {})
    return BitbankTickerData(
        pair=pair,
        buy=data["buy"],
        sell=data["sell"],
        high=data["high"],
        low=data["low"],
        last=data["last"],
        vol=data["vol"],
        timestamp=data["timestamp"],
    )


async def get_candlestick_data(
    pair: str, candle_type: str, year: int, config: BitbankAPIConfig
) -> BitbankCandlestickData:
    """Get candlestick data for a currency pair (TASK-012: FR-002).

    Args:
        pair: Currency pair (e.g., "btc_jpy").
        candle_type: Candlestick interval (e.g., "1hour", "1day").
        year: Year for data retrieval (e.g., 2024).
        config: bitbank API configuration.

    Returns:
        BitbankCandlestickData model.

    Raises:
        ValueError: If pair or candle_type is invalid.
        RuntimeError: On API errors.
    """
    # Validate currency pair
    if pair not in config.supported_pairs:
        raise ValueError(f"Invalid currency pair: {pair}. Supported pairs: {', '.join(config.supported_pairs)}")

    # Validate candle type
    if candle_type not in config.supported_candle_types:
        raise ValueError(
            f"Invalid candle type: {candle_type}. Supported types: {', '.join(config.supported_candle_types)}"
        )

    # Call API
    client = BitbankAPIClient(config)
    response = await client.get_candlestick(pair, candle_type, year)

    # Parse response
    if response.get("success") != 1:
        raise RuntimeError(f"API returned error: {response}")

    data = response.get("data", {})
    candlestick_list = data.get("candlestick", [])

    if not candlestick_list:
        raise ValueError(f"No candlestick data available for {pair} ({candle_type}, {year})")

    # Parse OHLCV data
    ohlcv_data = candlestick_list[0].get("ohlcv", [])
    ohlcv_entries = [
        BitbankCandlestickOHLCV(
            open=float(entry[0]),
            high=float(entry[1]),
            low=float(entry[2]),
            close=float(entry[3]),
            volume=float(entry[4]),
            timestamp=int(entry[5]),
        )
        for entry in ohlcv_data
    ]

    return BitbankCandlestickData(
        pair=pair,
        candle_type=candlestick_list[0]["type"],
        ohlcv=ohlcv_entries,
    )


def calculate_financial_metrics(
    candlestick_data: BitbankCandlestickData, config: BitbankAPIConfig
) -> FinancialSummary:
    """Calculate financial metrics from candlestick data (TASK-014: FR-003).

    Args:
        candlestick_data: Candlestick data.
        config: bitbank API configuration (contains risk_free_rate, etc.).

    Returns:
        FinancialSummary model.

    Raises:
        ValueError: If data is empty or invalid.
    """
    if len(candlestick_data.ohlcv) == 0:
        raise ValueError("Candlestick data is empty")

    # Extract closing prices
    closes = np.array([entry.close for entry in candlestick_data.ohlcv])

    # Validate finite values
    if not np.all(np.isfinite(closes)):
        raise ValueError("Price data contains NaN or Inf values")

    # Validate no zero prices (to prevent division by zero)
    if np.any(closes == 0):
        raise ValueError("Price data contains zero values")

    # Calculate daily returns (safe from division by zero after validation)
    daily_returns = np.diff(closes) / closes[:-1]

    # Additional safety check for finite returns
    if not np.all(np.isfinite(daily_returns)):
        raise ValueError("Calculated daily returns contain NaN or Inf values")

    # Annualized return (compound)
    daily_mean_return = np.mean(daily_returns)
    annualized_return = (1 + daily_mean_return) ** config.financial_metrics.trading_days_per_year - 1

    # Annualized volatility
    daily_std = np.std(daily_returns)
    annualized_volatility = daily_std * np.sqrt(config.financial_metrics.trading_days_per_year)

    # Sharpe ratio
    sharpe_ratio = (
        (annualized_return - config.financial_metrics.risk_free_rate) / annualized_volatility
        if annualized_volatility > 0
        else 0.0
    )

    # Sortino ratio (downside risk only)
    downside_returns = daily_returns[daily_returns < config.financial_metrics.minimum_acceptable_return]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0
    sortino_ratio = (
        (annualized_return - config.financial_metrics.minimum_acceptable_return)
        / (downside_std * np.sqrt(config.financial_metrics.trading_days_per_year))
        if downside_std > 0
        else 0.0
    )

    # Maximum drawdown (Running maximum method)
    running_max = np.maximum.accumulate(closes)
    drawdowns = (closes - running_max) / running_max
    max_drawdown = float(np.min(drawdowns))

    # Return distribution (calculated without scipy)
    mean_return = np.mean(daily_returns)
    std_return = np.std(daily_returns)

    if std_return > 0:
        # Skewness = E[(X - μ)³] / σ³
        return_skewness = float(np.mean(((daily_returns - mean_return) / std_return) ** 3))
        # Kurtosis (excess) = E[(X - μ)⁴] / σ⁴ - 3
        return_kurtosis = float(np.mean(((daily_returns - mean_return) / std_return) ** 4) - 3)
    else:
        return_skewness = 0.0
        return_kurtosis = 0.0

    # Total return
    total_return = (closes[-1] - closes[0]) / closes[0]

    # Total volume
    total_volume = float(np.sum([entry.volume for entry in candlestick_data.ohlcv]))

    return FinancialSummary(
        annualized_return=float(annualized_return),
        annualized_volatility=float(annualized_volatility),
        max_drawdown=max_drawdown,
        sharpe_ratio=float(sharpe_ratio),
        sortino_ratio=float(sortino_ratio),
        return_skewness=return_skewness,
        return_kurtosis=return_kurtosis,
        total_return=float(total_return),
        start_price=float(closes[0]),
        end_price=float(closes[-1]),
        mean_price=float(np.mean(closes)),
        total_volume=total_volume,
        trading_days=len(closes),
    )
