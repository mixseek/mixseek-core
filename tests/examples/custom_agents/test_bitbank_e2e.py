"""E2E tests for bitbank API integration (TASK-021).

These tests call the actual bitbank Public API without mocking.
Run with: pytest tests/examples/custom_agents/test_bitbank_e2e.py -m e2e -v
"""

import asyncio
from datetime import datetime

import pytest

from examples.custom_agents.bitbank.client import BitbankAPIClient
from examples.custom_agents.bitbank.models import (
    BitbankAPIConfig,
    BitbankCandlestickData,
    BitbankTickerData,
)
from examples.custom_agents.bitbank.tools import (
    calculate_financial_metrics,
    get_candlestick_data,
    get_ticker_data,
)


@pytest.fixture
def real_bitbank_config() -> BitbankAPIConfig:
    """Real bitbank API configuration for E2E tests."""
    return BitbankAPIConfig(
        base_url="https://public.bitbank.cc",
        timeout_seconds=30,
        max_retries=3,
        retry_delay_seconds=1,
        min_request_interval_seconds=1,
        supported_pairs=["btc_jpy", "xrp_jpy", "eth_jpy"],
        supported_candle_types=["4hour", "8hour", "12hour", "1day", "1week", "1month"],
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_real_ticker_api_call(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Call actual bitbank ticker API (SC-001: < 3 seconds)."""
    start_time = datetime.now()

    ticker_data = await get_ticker_data("btc_jpy", real_bitbank_config)

    elapsed_time = (datetime.now() - start_time).total_seconds()

    # Verify response structure
    assert isinstance(ticker_data, BitbankTickerData)
    assert ticker_data.pair == "btc_jpy"
    assert ticker_data.buy_float > 0
    assert ticker_data.sell_float > 0
    assert ticker_data.last_float > 0
    assert ticker_data.vol_float > 0
    assert ticker_data.timestamp > 0

    # SC-001: Response time < 3 seconds (network normal)
    assert elapsed_time < 3.0, f"Ticker API took {elapsed_time:.2f}s (expected < 3s)"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_real_candlestick_api_call(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Call actual bitbank candlestick API (SC-002: < 10 seconds)."""
    start_time = datetime.now()
    # Use 2024 data with 4hour intervals (verified working)
    test_year = 2024

    candlestick_data = await get_candlestick_data("btc_jpy", "4hour", test_year, real_bitbank_config)

    elapsed_time = (datetime.now() - start_time).total_seconds()

    # Verify response structure
    assert isinstance(candlestick_data, BitbankCandlestickData)
    assert candlestick_data.pair == "btc_jpy"
    assert candlestick_data.candle_type == "4hour"
    assert len(candlestick_data.ohlcv) > 0
    assert candlestick_data.count > 0

    # Verify OHLCV data
    for ohlcv in candlestick_data.ohlcv[:5]:  # Check first 5 entries
        assert ohlcv.open > 0
        assert ohlcv.high > 0
        assert ohlcv.low > 0
        assert ohlcv.close > 0
        assert ohlcv.volume >= 0
        assert ohlcv.timestamp > 0

    # SC-002: Response time < 10 seconds (max 1000 data points)
    assert elapsed_time < 10.0, f"Candlestick API took {elapsed_time:.2f}s (expected < 10s)"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_real_statistical_analysis(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Perform statistical analysis on real-time data (SC-002: < 10 seconds)."""
    start_time = datetime.now()
    # Use 2024 data with 4hour intervals (verified working)
    test_year = 2024

    # Get candlestick data
    candlestick_data = await get_candlestick_data("btc_jpy", "4hour", test_year, real_bitbank_config)

    # Calculate financial metrics
    metrics = calculate_financial_metrics(candlestick_data, real_bitbank_config)

    elapsed_time = (datetime.now() - start_time).total_seconds()

    # Verify financial metrics
    assert metrics.mean_price > 0
    assert metrics.annualized_volatility >= 0
    assert metrics.end_price > 0
    assert metrics.start_price > 0
    assert metrics.trading_days > 0
    assert metrics.total_volume >= 0
    assert metrics.trading_days == len(candlestick_data.ohlcv)

    # Total return can be positive or negative
    assert -1.0 <= metrics.total_return <= 10.0  # -100% to +1000%

    # SC-002: Total time < 10 seconds
    assert elapsed_time < 10.0, f"Statistical analysis took {elapsed_time:.2f}s (expected < 10s)"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rate_limit_handling_with_retry(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Verify retry logic on consecutive requests (SC-004)."""
    client = BitbankAPIClient(real_bitbank_config)

    # Make consecutive requests (should trigger rate limiting mechanism)
    successful_requests = 0
    for i in range(5):
        try:
            response = await client.get_ticker("btc_jpy")
            assert response["success"] == 1
            successful_requests += 1
        except RuntimeError as e:
            # If rate limited, retry logic should be triggered
            assert "HTTP" in str(e) or "429" in str(e)

    # At least some requests should succeed
    assert successful_requests >= 3, f"Only {successful_requests}/5 requests succeeded"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_requests(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Verify concurrent requests for multiple currency pairs."""
    # Get ticker data for 3 pairs concurrently
    results = await asyncio.gather(
        get_ticker_data("btc_jpy", real_bitbank_config),
        get_ticker_data("xrp_jpy", real_bitbank_config),
        get_ticker_data("eth_jpy", real_bitbank_config),
    )

    # Verify all requests succeeded
    assert len(results) == 3
    assert results[0].pair == "btc_jpy"
    assert results[1].pair == "xrp_jpy"
    assert results[2].pair == "eth_jpy"

    # All prices should be positive
    for ticker in results:
        assert ticker.last_float > 0
        assert ticker.buy_float > 0
        assert ticker.sell_float > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_pair_error_handling(real_bitbank_config: BitbankAPIConfig) -> None:
    """E2E Test: Verify clear error message for invalid currency pair."""
    with pytest.raises(ValueError) as exc_info:
        await get_ticker_data("invalid_pair", real_bitbank_config)

    # Error message should list supported pairs
    assert "Invalid currency pair" in str(exc_info.value)
    assert "btc_jpy" in str(exc_info.value)
    assert "supported pairs" in str(exc_info.value).lower()
