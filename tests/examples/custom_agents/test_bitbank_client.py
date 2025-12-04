"""Tests for bitbank API client (TASK-007).

This module contains tests for BitbankAPIClient class.
All tests follow TDD Red phase - tests are written before implementation.
"""

import pytest
from httpx import Request, Response, TimeoutException
from pytest_mock import MockerFixture

from examples.custom_agents.bitbank.client import BitbankAPIClient
from examples.custom_agents.bitbank.models import BitbankAPIConfig


@pytest.fixture
def test_config() -> BitbankAPIConfig:
    """Create test configuration."""
    return BitbankAPIConfig(
        base_url="https://public.bitbank.cc",
        timeout_seconds=30,
        max_retries=3,
        retry_delay_seconds=1,
        min_request_interval_seconds=1,
        supported_pairs=["btc_jpy", "xrp_jpy"],
        supported_candle_types=["1hour", "1day"],
    )


class TestBitbankAPIClient:
    """Tests for BitbankAPIClient class."""

    @pytest.mark.asyncio
    async def test_get_ticker_success(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test successful ticker API call with mocked response"""
        mock_response = {
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

        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.return_value = Response(
            200, json=mock_response, request=Request("GET", "https://public.bitbank.cc/btc_jpy/ticker")
        )

        client = BitbankAPIClient(test_config)
        result = await client.get_ticker("btc_jpy")

        assert result["success"] == 1
        assert result["data"]["buy"] == "10500000"
        mock_httpx.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_candlestick_success(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test successful candlestick API call with mocked response"""
        mock_response = {
            "success": 1,
            "data": {
                "candlestick": [
                    {
                        "type": "1hour",
                        "ohlcv": [[10500000.0, 10520000.0, 10490000.0, 10510000.0, 123.456, 1700000000000]],
                    }
                ]
            },
        }

        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.return_value = Response(
            200, json=mock_response, request=Request("GET", "https://public.bitbank.cc/btc_jpy/candlestick/1hour/2025")
        )

        client = BitbankAPIClient(test_config)
        result = await client.get_candlestick("btc_jpy", "1hour", 2025)

        assert result["success"] == 1
        assert "candlestick" in result["data"]
        mock_httpx.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ticker_http_404_error(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test HTTP 404 error raises RuntimeError"""
        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.return_value = Response(404, text="Not Found", request=Request("GET", "https://test.com"))

        client = BitbankAPIClient(test_config)

        with pytest.raises(RuntimeError, match="404"):
            await client.get_ticker("invalid_pair")

    @pytest.mark.asyncio
    async def test_get_ticker_http_429_retry_logic(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test HTTP 429 rate limiting triggers retry logic"""
        mock_success_response = {
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

        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.side_effect = [
            Response(429, text="Too Many Requests", request=Request("GET", "https://test.com")),
            Response(200, json=mock_success_response, request=Request("GET", "https://test.com")),
        ]

        client = BitbankAPIClient(test_config)
        result = await client.get_ticker("btc_jpy")

        assert result["success"] == 1
        assert mock_httpx.call_count == 2

    @pytest.mark.asyncio
    async def test_get_ticker_http_500_error(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test HTTP 500 error raises RuntimeError"""
        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.return_value = Response(
            500, text="Internal Server Error", request=Request("GET", "https://test.com")
        )

        client = BitbankAPIClient(test_config)

        with pytest.raises(RuntimeError, match="500"):
            await client.get_ticker("btc_jpy")

    @pytest.mark.asyncio
    async def test_get_ticker_timeout_error(self, test_config: BitbankAPIConfig, mocker: MockerFixture) -> None:
        """Test timeout raises RuntimeError"""
        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.side_effect = TimeoutException("Request timeout")

        client = BitbankAPIClient(test_config)

        with pytest.raises(RuntimeError, match="timeout"):
            await client.get_ticker("btc_jpy")

    @pytest.mark.asyncio
    async def test_get_ticker_invalid_json_response(
        self, test_config: BitbankAPIConfig, mocker: MockerFixture
    ) -> None:
        """Test invalid JSON response raises RuntimeError"""
        mock_httpx = mocker.patch("httpx.AsyncClient.get")
        mock_httpx.return_value = Response(200, text="invalid json", request=Request("GET", "https://test.com"))

        client = BitbankAPIClient(test_config)

        with pytest.raises(RuntimeError, match="JSON"):
            await client.get_ticker("btc_jpy")
