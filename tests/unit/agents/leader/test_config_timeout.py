"""Unit tests for LeaderAgentConfig timeout settings.

This test suite validates the timeout_seconds field in LeaderAgentConfig,
including validation rules, default values, and boundary conditions.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the implementation to ensure proper HTTP timeout handling.
"""

import pytest
from pydantic import ValidationError

from mixseek.agents.leader.config import LeaderAgentConfig


class TestLeaderAgentConfigTimeout:
    """Test LeaderAgentConfig timeout_seconds field validation."""

    def test_timeout_default_value(self) -> None:
        """Test timeout_seconds has correct default value."""
        config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite")
        assert config.timeout_seconds == 300  # 5分

    def test_timeout_explicit_value(self) -> None:
        """Test timeout_seconds accepts explicit valid values."""
        config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=120)
        assert config.timeout_seconds == 120

    def test_timeout_none_value(self) -> None:
        """Test timeout_seconds accepts None (optional field)."""
        config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=None)
        assert config.timeout_seconds is None

    def test_timeout_minimum_bound(self) -> None:
        """Test timeout_seconds minimum boundary (10 seconds)."""
        # Valid: exactly 10 seconds
        config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=10)
        assert config.timeout_seconds == 10

        # Invalid: below minimum
        with pytest.raises(ValidationError, match="greater than or equal to 10"):
            LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=9)

    def test_timeout_maximum_bound(self) -> None:
        """Test timeout_seconds maximum boundary (600 seconds / 10 minutes)."""
        # Valid: exactly 600 seconds
        config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=600)
        assert config.timeout_seconds == 600

        # Invalid: above maximum
        with pytest.raises(ValidationError, match="less than or equal to 600"):
            LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=601)

    def test_timeout_typical_values(self) -> None:
        """Test timeout_seconds with typical use case values."""
        typical_values = [
            10,  # Minimum
            30,  # Short timeout
            60,  # 1 minute
            120,  # 2 minutes
            300,  # 5 minutes (default)
            600,  # 10 minutes (maximum)
        ]

        for timeout in typical_values:
            config = LeaderAgentConfig(model="google-gla:gemini-2.5-flash-lite", timeout_seconds=timeout)
            assert config.timeout_seconds == timeout

    def test_timeout_with_other_fields(self) -> None:
        """Test timeout_seconds works correctly with other LeaderAgentConfig fields."""
        config = LeaderAgentConfig(
            model="google-gla:gemini-2.5-flash-lite",
            temperature=0.8,
            system_instruction="Test instruction",
            timeout_seconds=180,
        )
        assert config.timeout_seconds == 180
        assert config.temperature == 0.8
        assert config.system_instruction == "Test instruction"
