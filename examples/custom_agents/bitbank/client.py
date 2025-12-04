"""bitbank Public API Client (TASK-008).

This module provides an async HTTP client for interacting with the bitbank Public API.
Article 9 compliant: All configuration values are externalized to TOML.
"""

import asyncio
import json
from typing import Any, cast

import httpx

from examples.custom_agents.bitbank.models import BitbankAPIConfig


class BitbankAPIClient:
    """Async HTTP client for bitbank Public API."""

    def __init__(self, config: BitbankAPIConfig) -> None:
        """Initialize the bitbank API client.

        Args:
            config: bitbank API configuration (from TOML).
        """
        self.config = config
        self._last_request_time: float = 0.0

    async def _enforce_rate_limit(self) -> None:
        """Enforce minimum request interval (rate limiting)."""
        current_time = asyncio.get_running_loop().time()
        elapsed = current_time - self._last_request_time

        if elapsed < self.config.min_request_interval_seconds:
            await asyncio.sleep(self.config.min_request_interval_seconds - elapsed)

        self._last_request_time = asyncio.get_running_loop().time()

    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        """Execute HTTP request with exponential backoff retry.

        Args:
            url: Full API endpoint URL.

        Returns:
            JSON response as dictionary.

        Raises:
            RuntimeError: On network errors, timeouts, or HTTP errors.
        """
        for attempt in range(self.config.max_retries):
            try:
                await self._enforce_rate_limit()

                async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                    response = await client.get(url)

                    # Handle rate limiting (HTTP 429)
                    if response.status_code == 429:
                        if attempt < self.config.max_retries - 1:
                            wait_time = self.config.retry_delay_seconds * (2**attempt)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise RuntimeError(f"Rate limit exceeded after {self.config.max_retries} retries")

                    # Raise for other HTTP errors
                    response.raise_for_status()

                    # Parse and return JSON
                    try:
                        return cast(dict[str, Any], response.json())
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Invalid JSON response from API: {e}")

            except httpx.TimeoutException:
                if attempt == self.config.max_retries - 1:
                    raise RuntimeError(
                        f"Request timeout after {self.config.timeout_seconds}s. "
                        f"Check network connectivity or increase timeout_seconds in TOML config."
                    )
                await asyncio.sleep(self.config.retry_delay_seconds * (2**attempt))

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise RuntimeError(f"HTTP 404: API endpoint not found: {url}")
                elif e.response.status_code >= 500:
                    raise RuntimeError(f"bitbank API server error: {e.response.status_code}")
                else:
                    raise RuntimeError(f"HTTP error {e.response.status_code}: {e.response.text}")

            except httpx.NetworkError as e:
                raise RuntimeError(f"Network connection error: {e}. Check internet connectivity.")

        raise RuntimeError(f"Max retries ({self.config.max_retries}) exceeded")

    async def get_ticker(self, pair: str) -> dict[str, Any]:
        """Get ticker data for a currency pair.

        Args:
            pair: Currency pair (e.g., "btc_jpy").

        Returns:
            Ticker API response.

        Raises:
            RuntimeError: On API errors.
        """
        url = f"{self.config.base_url}/{pair}/ticker"
        return await self._request_with_retry(url)

    async def get_candlestick(self, pair: str, candle_type: str, year: int) -> dict[str, Any]:
        """Get candlestick data for a currency pair.

        Args:
            pair: Currency pair (e.g., "btc_jpy").
            candle_type: Candlestick interval (e.g., "1hour", "1day").
            year: Year for data retrieval (e.g., 2024).

        Returns:
            Candlestick API response.

        Raises:
            RuntimeError: On API errors.
        """
        url = f"{self.config.base_url}/{pair}/candlestick/{candle_type}/{year}"
        return await self._request_with_retry(url)
