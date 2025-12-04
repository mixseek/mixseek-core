"""Unit tests for bitbank Pydantic models (TASK-003)."""

import pytest
from pydantic import ValidationError


def test_bitbank_ticker_data_valid():
    """Test BitbankTickerData with valid data."""
    from examples.custom_agents.bitbank.models import BitbankTickerData

    data = BitbankTickerData(
        pair="btc_jpy",
        buy="10500000",
        sell="10510000",
        high="10600000",
        low="10400000",
        last="10505000",
        vol="1234.5678",
        timestamp=1700000000000,
    )

    assert data.pair == "btc_jpy"
    assert data.buy_float == 10500000.0
    assert data.sell_float == 10510000.0
    assert data.last_float == 10505000.0
    assert data.vol_float == 1234.5678


def test_bitbank_candlestick_ohlcv_valid():
    """Test BitbankCandlestickOHLCV with valid data."""
    from examples.custom_agents.bitbank.models import BitbankCandlestickOHLCV

    ohlcv = BitbankCandlestickOHLCV(
        open=10500000.0,
        high=10520000.0,
        low=10490000.0,
        close=10510000.0,
        volume=123.456,
        timestamp=1700000000000,
    )

    assert ohlcv.open == 10500000.0
    assert ohlcv.high == 10520000.0
    assert ohlcv.low == 10490000.0
    assert ohlcv.close == 10510000.0


def test_bitbank_candlestick_data_valid():
    """Test BitbankCandlestickData with valid data."""
    from examples.custom_agents.bitbank.models import (
        BitbankCandlestickData,
        BitbankCandlestickOHLCV,
    )

    data = BitbankCandlestickData(
        pair="btc_jpy",
        candle_type="1hour",
        ohlcv=[
            BitbankCandlestickOHLCV(
                open=10500000.0,
                high=10520000.0,
                low=10490000.0,
                close=10510000.0,
                volume=123.456,
                timestamp=1700000000000,
            )
        ],
    )

    assert data.pair == "btc_jpy"
    assert data.candle_type == "1hour"
    assert data.count == 1
    assert len(data.closes) == 1
    assert data.closes[0] == 10510000.0


def test_financial_summary_valid():
    """Test FinancialSummary with valid data."""
    from examples.custom_agents.bitbank.models import FinancialSummary

    summary = FinancialSummary(
        annualized_return=0.152,
        annualized_volatility=0.342,
        max_drawdown=-0.189,
        sharpe_ratio=0.441,
        sortino_ratio=0.623,
        return_skewness=-0.123,
        return_kurtosis=2.456,
        total_return=0.0192,
        start_price=10400000.0,
        end_price=10600000.0,
        mean_price=10505000.0,
        total_volume=1234.5678,
        trading_days=24,
    )

    assert summary.annualized_return == 0.152
    assert summary.sharpe_ratio == 0.441
    assert summary.max_drawdown == -0.189


def test_financial_summary_invalid_nan():
    """Test FinancialSummary rejects NaN values."""
    from examples.custom_agents.bitbank.models import FinancialSummary

    with pytest.raises(ValidationError):
        FinancialSummary(
            annualized_return=float("nan"),
            annualized_volatility=0.342,
            max_drawdown=-0.189,
            sharpe_ratio=0.441,
            sortino_ratio=0.623,
            return_skewness=-0.123,
            return_kurtosis=2.456,
            total_return=0.0192,
            start_price=10400000.0,
            end_price=10600000.0,
            mean_price=10505000.0,
            total_volume=1234.5678,
            trading_days=24,
        )


def test_bitbank_api_config_valid():
    """Test BitbankAPIConfig with valid data."""
    from examples.custom_agents.bitbank.models import BitbankAPIConfig

    config = BitbankAPIConfig(
        base_url="https://public.bitbank.cc",
        timeout_seconds=30,
        max_retries=3,
        retry_delay_seconds=1,
        min_request_interval_seconds=1,
        supported_pairs=["btc_jpy", "xrp_jpy"],
        supported_candle_types=["1hour", "1day"],
    )

    assert config.base_url == "https://public.bitbank.cc"
    assert config.financial_metrics.risk_free_rate == 0.001
    assert config.financial_metrics.trading_days_per_year == 365
    assert config.financial_metrics.minimum_acceptable_return == 0.0


def test_bitbank_api_config_invalid_url():
    """Test BitbankAPIConfig rejects invalid URLs."""
    from examples.custom_agents.bitbank.models import BitbankAPIConfig

    with pytest.raises(ValidationError):
        BitbankAPIConfig(
            base_url="http://insecure.com",  # Should start with https://
            timeout_seconds=30,
            max_retries=3,
            retry_delay_seconds=1,
            min_request_interval_seconds=1,
            supported_pairs=["btc_jpy"],
            supported_candle_types=["1hour"],
        )


def test_member_agent_result_valid():
    """Test MemberAgentResult with valid data."""
    from mixseek.models.member_agent import MemberAgentResult, ResultStatus

    result = MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content="# BTC/JPY Ticker Data\n\n- Buy: 10,500,000 JPY",
        agent_name="bitbank-api-agent",
        agent_type="custom",
    )

    assert result.status == ResultStatus.SUCCESS
    assert "BTC/JPY" in result.content
    assert result.agent_name == "bitbank-api-agent"
