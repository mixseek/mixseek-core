"""Tests for bitbank agent tools (TASK-009+).

This module contains tests for tool functions used by BitbankAPIAgent.
All tests follow TDD Red phase - tests are written before implementation.
"""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from examples.custom_agents.bitbank.models import (
    BitbankAPIConfig,
    BitbankCandlestickData,
    BitbankCandlestickOHLCV,
    BitbankTickerData,
    FinancialSummary,
)
from examples.custom_agents.bitbank.tools import calculate_financial_metrics, get_candlestick_data, get_ticker_data
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult, ResultStatus


@pytest.fixture(autouse=True)
def setup_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup MIXSEEK_WORKSPACE and GOOGLE_API_KEY for all tests."""
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key-for-unit-tests")


@pytest.fixture
def test_config() -> BitbankAPIConfig:
    """Create test configuration for tools."""
    return BitbankAPIConfig(
        base_url="https://public.bitbank.cc",
        timeout_seconds=30,
        max_retries=3,
        retry_delay_seconds=1,
        min_request_interval_seconds=1,
        supported_pairs=["btc_jpy", "xrp_jpy"],
        supported_candle_types=["1hour", "1day"],
    )


@pytest.fixture
def test_member_config() -> MemberAgentConfig:
    """Create test MemberAgentConfig for agent."""
    from mixseek.models.member_agent import PluginMetadata

    # Bitbank API configuration (from TOML [agent.tool_settings.bitbank_api])
    bitbank_api_config = {
        "base_url": "https://public.bitbank.cc",
        "timeout_seconds": 30,
        "max_retries": 3,
        "retry_delay_seconds": 1,
        "min_request_interval_seconds": 1,
        "supported_pairs": ["btc_jpy", "xrp_jpy", "eth_jpy"],
        "supported_candle_types": ["1hour", "1day", "1week"],
        "financial_metrics": {
            "risk_free_rate": 0.001,
            "trading_days_per_year": 365,
            "minimum_acceptable_return": 0.0,
        },
    }

    return MemberAgentConfig(
        name="bitbank-api-agent",
        type="custom",
        model="google-gla:gemini-2.0-flash-exp",
        system_instruction="Test instruction",
        plugin=PluginMetadata(
            agent_module="examples.custom_agents.bitbank.agent",
            agent_class="BitbankAPIAgent",
        ),
        metadata={"tool_settings": {"bitbank_api": bitbank_api_config}},
    )


class TestGetTickerData:
    """Tests for get_ticker_data tool function (TASK-009)."""

    @pytest.mark.asyncio
    async def test_get_ticker_data_success(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test successful ticker data retrieval and parsing"""
        mock_api_response = {
            "success": 1,
            "data": {
                "sell": "10510000",
                "buy": "10500000",
                "high": "10600000",
                "low": "10400000",
                "last": "10505000",
                "vol": "1234.5678",
                "timestamp": 1700000000000,
            },
        }

        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_ticker = mocker.AsyncMock(return_value=mock_api_response)

        result = await get_ticker_data("btc_jpy", test_config)

        assert isinstance(result, BitbankTickerData)
        assert result.pair == "btc_jpy"
        assert result.buy == "10500000"
        assert result.sell == "10510000"
        assert result.last == "10505000"

    @pytest.mark.asyncio
    async def test_get_ticker_data_invalid_pair(self, test_config: BitbankAPIConfig) -> None:
        """Test ValueError raised for invalid currency pair"""
        with pytest.raises(ValueError, match="Invalid currency pair"):
            await get_ticker_data("invalid_pair", test_config)

    @pytest.mark.asyncio
    async def test_get_ticker_data_api_error(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test RuntimeError propagated from API client"""
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_ticker = mocker.AsyncMock(side_effect=RuntimeError("HTTP 500 error"))

        with pytest.raises(RuntimeError, match="HTTP 500"):
            await get_ticker_data("btc_jpy", test_config)


class TestGetCandlestickData:
    """Tests for get_candlestick_data tool function (TASK-011)."""

    @pytest.mark.asyncio
    async def test_get_candlestick_data_success(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test successful candlestick data retrieval and parsing"""
        mock_api_response = {
            "success": 1,
            "data": {
                "candlestick": [
                    {
                        "type": "1hour",
                        "ohlcv": [
                            [10500000.0, 10520000.0, 10490000.0, 10510000.0, 123.456, 1700000000000],
                            [10510000.0, 10530000.0, 10500000.0, 10520000.0, 234.567, 1700003600000],
                        ],
                    }
                ]
            },
        }

        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_candlestick = mocker.AsyncMock(return_value=mock_api_response)

        result = await get_candlestick_data("btc_jpy", "1hour", 2025, test_config)

        assert isinstance(result, BitbankCandlestickData)
        assert result.pair == "btc_jpy"
        assert result.candle_type == "1hour"
        assert result.count == 2
        assert len(result.ohlcv) == 2

    @pytest.mark.asyncio
    async def test_get_candlestick_data_invalid_pair(self, test_config: BitbankAPIConfig) -> None:
        """Test ValueError raised for invalid currency pair"""
        with pytest.raises(ValueError, match="Invalid currency pair"):
            await get_candlestick_data("invalid_pair", "1hour", 2025, test_config)

    @pytest.mark.asyncio
    async def test_get_candlestick_data_invalid_candle_type(self, test_config: BitbankAPIConfig) -> None:
        """Test ValueError raised for invalid candle type"""
        with pytest.raises(ValueError, match="Invalid candle type"):
            await get_candlestick_data("btc_jpy", "invalid_type", 2025, test_config)

    @pytest.mark.asyncio
    async def test_get_candlestick_data_api_error(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test RuntimeError propagated from API client"""
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_candlestick = mocker.AsyncMock(side_effect=RuntimeError("HTTP 500 error"))

        with pytest.raises(RuntimeError, match="HTTP 500"):
            await get_candlestick_data("btc_jpy", "1hour", 2025, test_config)


class TestCalculateFinancialMetrics:
    """Tests for calculate_financial_metrics tool function (TASK-014)."""

    def test_calculate_financial_metrics_success(self, test_config: BitbankAPIConfig) -> None:
        """Test successful financial metrics calculation from candlestick data"""
        ohlcv_data = [
            BitbankCandlestickOHLCV(
                open=10000000.0,
                high=10500000.0,
                low=9500000.0,
                close=10200000.0,
                volume=100.5,
                timestamp=1700000000000,
            ),
            BitbankCandlestickOHLCV(
                open=10200000.0,
                high=10800000.0,
                low=10000000.0,
                close=10600000.0,
                volume=150.3,
                timestamp=1700003600000,
            ),
            BitbankCandlestickOHLCV(
                open=10600000.0,
                high=11000000.0,
                low=10400000.0,
                close=10800000.0,
                volume=200.7,
                timestamp=1700007200000,
            ),
        ]

        candlestick_data = BitbankCandlestickData(pair="btc_jpy", candle_type="1hour", ohlcv=ohlcv_data)

        result = calculate_financial_metrics(candlestick_data, test_config)

        assert isinstance(result, FinancialSummary)
        assert result.mean_price > 0
        assert result.annualized_volatility >= 0
        assert result.end_price > result.start_price  # Price increased
        assert result.total_volume == 451.5
        assert result.trading_days == 3

    def test_calculate_financial_metrics_empty_data(self, test_config: BitbankAPIConfig) -> None:
        """Test ValueError raised for empty candlestick data"""
        candlestick_data = BitbankCandlestickData(pair="btc_jpy", candle_type="1hour", ohlcv=[])

        with pytest.raises(ValueError, match="Candlestick data is empty"):
            calculate_financial_metrics(candlestick_data, test_config)

    def test_calculate_financial_metrics_zero_price(self, test_config: BitbankAPIConfig) -> None:
        """Test ValueError raised for zero price data (prevent division by zero)"""
        ohlcv_data = [
            BitbankCandlestickOHLCV(
                open=10000000.0, high=10500000.0, low=9500000.0, close=0.0, volume=100.5, timestamp=1700000000000
            ),
        ]
        candlestick_data = BitbankCandlestickData(pair="btc_jpy", candle_type="1hour", ohlcv=ohlcv_data)

        with pytest.raises(ValueError, match="Price data contains zero values"):
            calculate_financial_metrics(candlestick_data, test_config)


class TestBitbankAPIAgent:
    """Tests for BitbankAPIAgent class (TASK-015)."""

    @pytest.mark.asyncio
    async def test_bitbank_api_agent_ticker_task(
        self, test_member_config: MemberAgentConfig, mocker: MockerFixture
    ) -> None:
        """Test agent successfully handles ticker retrieval task"""
        # Import agent class (will fail initially in Red phase)
        from examples.custom_agents.bitbank.agent import BitbankAPIAgent

        # Mock API client to avoid real API calls
        mock_ticker_response = {
            "success": 1,
            "data": {
                "sell": "10510000",
                "buy": "10500000",
                "high": "10600000",
                "low": "10400000",
                "last": "10505000",
                "vol": "1234.5678",
                "timestamp": 1700000000000,
            },
        }
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_ticker = mocker.AsyncMock(return_value=mock_ticker_response)

        # Create agent and mock Pydantic AI agent run method
        agent = BitbankAPIAgent(test_member_config)

        # Mock the agent.run() method to return a mock result
        mock_run_result = mocker.MagicMock()
        mock_run_result.output = "# BTC_JPY Ticker Data\n\n- **Buy**: 10,500,000 JPY\n- **Last**: 10,505,000 JPY"

        mocker.patch.object(agent.agent, "run", new_callable=mocker.AsyncMock, return_value=mock_run_result)

        result = await agent.execute("btc_jpyの価格を取得")

        # Verify result
        assert isinstance(result, MemberAgentResult)
        assert result.is_success()
        assert "btc_jpy" in result.content.lower()
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_bitbank_api_agent_candlestick_task(
        self, test_member_config: MemberAgentConfig, mocker: MockerFixture
    ) -> None:
        """Test agent successfully handles candlestick retrieval task"""
        from examples.custom_agents.bitbank.agent import BitbankAPIAgent

        mock_candlestick_response = {
            "success": 1,
            "data": {
                "candlestick": [
                    {
                        "type": "1hour",
                        "ohlcv": [
                            [10500000.0, 10520000.0, 10490000.0, 10510000.0, 123.456, 1700000000000],
                            [10510000.0, 10530000.0, 10500000.0, 10520000.0, 234.567, 1700003600000],
                        ],
                    }
                ]
            },
        }
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_candlestick = mocker.AsyncMock(return_value=mock_candlestick_response)

        # Create agent and mock Pydantic AI agent run method
        agent = BitbankAPIAgent(test_member_config)

        mock_run_result = mocker.MagicMock()
        mock_run_result.output = "# BTC_JPY Candlestick Data\n\n- **Interval**: 1hour\n- **Data Points**: 2"

        mocker.patch.object(agent.agent, "run", new_callable=mocker.AsyncMock, return_value=mock_run_result)

        result = await agent.execute("btc_jpyの1hourロウソク足を取得")

        assert isinstance(result, MemberAgentResult)
        assert result.is_success()
        assert "btc_jpy" in result.content.lower() or "1hour" in result.content.lower()

    @pytest.mark.asyncio
    async def test_bitbank_api_agent_statistics_task(
        self, test_member_config: MemberAgentConfig, mocker: MockerFixture
    ) -> None:
        """Test agent successfully handles statistical analysis task"""
        from examples.custom_agents.bitbank.agent import BitbankAPIAgent

        mock_candlestick_response = {
            "success": 1,
            "data": {
                "candlestick": [
                    {
                        "type": "1hour",
                        "ohlcv": [
                            [10000000.0, 10500000.0, 9500000.0, 10200000.0, 100.5, 1700000000000],
                            [10200000.0, 10800000.0, 10000000.0, 10600000.0, 150.3, 1700003600000],
                            [10600000.0, 11000000.0, 10400000.0, 10800000.0, 200.7, 1700007200000],
                        ],
                    }
                ]
            },
        }
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_candlestick = mocker.AsyncMock(return_value=mock_candlestick_response)

        # Create agent and mock Pydantic AI agent run method
        agent = BitbankAPIAgent(test_member_config)

        mock_run_result = mocker.MagicMock()
        mock_run_result.output = (
            "# BTC_JPY Financial Metrics\n\n"
            "- **Mean Price**: 10,500,000 JPY\n"
            "- **標準偏差**: 5.2%\n"
            "- **Sharpe Ratio**: 1.5"
        )

        mocker.patch.object(agent.agent, "run", new_callable=mocker.AsyncMock, return_value=mock_run_result)

        result = await agent.execute("btc_jpyの統計情報を分析")

        assert isinstance(result, MemberAgentResult)
        assert result.is_success()
        assert len(result.content) > 0
        # Verify statistical terms appear in analysis
        content_lower = result.content.lower()
        assert any(keyword in content_lower for keyword in ["mean", "平均", "std", "標準偏差"])

    @pytest.mark.asyncio
    async def test_bitbank_api_agent_result_format(
        self, test_member_config: MemberAgentConfig, mocker: MockerFixture
    ) -> None:
        """Test that agent returns MemberAgentResult with correct format"""
        from examples.custom_agents.bitbank.agent import BitbankAPIAgent

        mock_ticker_response = {
            "success": 1,
            "data": {
                "sell": "10510000",
                "buy": "10500000",
                "high": "10600000",
                "low": "10400000",
                "last": "10505000",
                "vol": "1234.5678",
                "timestamp": 1700000000000,
            },
        }
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_ticker = mocker.AsyncMock(return_value=mock_ticker_response)

        # Create agent and mock Pydantic AI agent run method
        agent = BitbankAPIAgent(test_member_config)

        mock_run_result = mocker.MagicMock()
        mock_run_result.output = "# BTC_JPY Ticker Data\n\n- **Last**: 10,505,000 JPY"

        mocker.patch.object(agent.agent, "run", new_callable=mocker.AsyncMock, return_value=mock_run_result)

        result = await agent.execute("btc_jpyの価格を取得")

        # Verify MemberAgentResult structure
        assert isinstance(result, MemberAgentResult)
        assert hasattr(result, "status")
        assert hasattr(result, "content")
        assert hasattr(result, "metadata")
        assert hasattr(result, "agent_name")
        assert hasattr(result, "agent_type")
        assert result.status == ResultStatus.SUCCESS
        assert isinstance(result.content, str)
        assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_bitbank_api_agent_error_handling(
        self, test_member_config: MemberAgentConfig, mocker: MockerFixture
    ) -> None:
        """Test that agent returns success=False when API error occurs"""
        from examples.custom_agents.bitbank.agent import BitbankAPIAgent

        # Mock API client to raise RuntimeError
        mock_client = mocker.patch("examples.custom_agents.bitbank.tools.BitbankAPIClient")
        mock_client.return_value.get_ticker = mocker.AsyncMock(side_effect=RuntimeError("HTTP 500 error"))

        # Create agent and mock Pydantic AI agent run method to raise error
        agent = BitbankAPIAgent(test_member_config)

        mocker.patch.object(
            agent.agent, "run", new_callable=mocker.AsyncMock, side_effect=RuntimeError("HTTP 500 error")
        )

        result = await agent.execute("btc_jpyの価格を取得")

        assert isinstance(result, MemberAgentResult)
        assert result.is_error()
        assert result.error_message is not None
        assert "500" in result.error_message or "HTTP" in result.error_message
