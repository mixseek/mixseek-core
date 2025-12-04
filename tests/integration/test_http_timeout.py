"""Integration tests for HTTP timeout propagation.

This test suite validates that timeout settings correctly propagate through
the agent creation chain: TeamConfig → LeaderAgent → ModelSettings.

According to Article 3 (Test-First Imperative), these tests are written BEFORE
the implementation to ensure proper timeout handling across components.
"""

import pytest

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import LeaderAgentConfig, TeamConfig


class TestHTTPTimeoutPropagation:
    """Test HTTP timeout settings propagate correctly through the system."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setup test environment to use TestModel."""
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_http_timeout")

    @pytest.fixture
    def team_config_with_timeout(self) -> TeamConfig:
        """Create a team config with custom timeout."""
        return TeamConfig(
            team_id="test-team",
            team_name="Test Team",
            leader=LeaderAgentConfig(
                model="test",  # Use test model
                temperature=0.7,
                timeout_seconds=180,  # 3 minutes
            ),
            members=[],
        )

    @pytest.fixture
    def team_config_default_timeout(self) -> TeamConfig:
        """Create a team config with default timeout."""
        return TeamConfig(
            team_id="test-team-default",
            team_name="Test Team Default",
            leader=LeaderAgentConfig(
                model="test",  # Use test model
                temperature=0.7,
                # timeout_seconds not specified → default 300
            ),
            members=[],
        )

    @pytest.fixture
    def team_config_none_timeout(self) -> TeamConfig:
        """Create a team config with None timeout."""
        return TeamConfig(
            team_id="test-team-none",
            team_name="Test Team None",
            leader=LeaderAgentConfig(
                model="test",  # Use test model
                temperature=0.7,
                timeout_seconds=None,  # Explicit None
            ),
            members=[],
        )

    def test_custom_timeout_propagates_to_model_settings(self, team_config_with_timeout: TeamConfig) -> None:
        """Test custom timeout_seconds propagates to Agent's ModelSettings."""
        # Create leader agent with real TestModel
        leader_agent = create_leader_agent(team_config_with_timeout, member_agents={})

        # Verify agent has correct model_settings with timeout
        assert leader_agent.model_settings is not None, "Agent should have model_settings"
        assert leader_agent.model_settings.get("timeout") == 180.0, "Timeout should be 180.0 seconds"

    def test_default_timeout_propagates_to_model_settings(self, team_config_default_timeout: TeamConfig) -> None:
        """Test default timeout_seconds (300s) propagates to Agent's ModelSettings."""
        # Create leader agent with real TestModel
        leader_agent = create_leader_agent(team_config_default_timeout, member_agents={})

        # Verify agent has correct model_settings with default timeout
        assert leader_agent.model_settings is not None, "Agent should have model_settings"
        assert leader_agent.model_settings.get("timeout") == 300.0, "Timeout should be 300.0 seconds (default)"

    def test_none_timeout_does_not_set_model_settings(self, team_config_none_timeout: TeamConfig) -> None:
        """Test None timeout_seconds does not set ModelSettings timeout."""
        # Create leader agent with real TestModel
        leader_agent = create_leader_agent(team_config_none_timeout, member_agents={})

        # Verify agent has model_settings but timeout is not set
        # (Other fields like temperature may be set, which is expected)
        assert leader_agent.model_settings is not None, "Agent should have model_settings dict"
        assert "timeout" not in leader_agent.model_settings, "Timeout should not be in model_settings when None"
