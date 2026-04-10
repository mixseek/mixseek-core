"""Unit tests for member_dispatch field in TeamSettings and TeamConfig."""

import pytest
from pydantic import ValidationError

from mixseek.agents.leader.config import TeamConfig, team_settings_to_team_config
from mixseek.config.schema import TeamSettings


class TestMemberDispatchField:
    """Tests for member_dispatch field on TeamSettings."""

    def test_default_value_is_selective(self) -> None:
        """member_dispatch未指定時はselectiveがデフォルト."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        assert settings.member_dispatch == "selective"

    def test_broadcast_value_accepted(self) -> None:
        """member_dispatch=broadcastが受け付けられる."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        assert settings.member_dispatch == "broadcast"

    def test_invalid_value_rejected(self) -> None:
        """無効なmember_dispatch値はValidationErrorになる."""
        with pytest.raises(ValidationError, match="member_dispatch"):
            TeamSettings(
                team_id="test-team",
                team_name="Test Team",
                member_dispatch="invalid",  # type: ignore[arg-type]
                leader={"model": "google-gla:gemini-2.5-flash-lite"},
            )


class TestMemberDispatchTeamConfig:
    """Tests for member_dispatch on TeamConfig."""

    def test_default_value_is_selective(self) -> None:
        """TeamConfigのデフォルトもselective."""
        config = TeamConfig(
            team_id="test-team",
            team_name="Test Team",
        )
        assert config.member_dispatch == "selective"

    def test_broadcast_value_accepted(self) -> None:
        """TeamConfigでbroadcastが受け付けられる."""
        config = TeamConfig(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
        )
        assert config.member_dispatch == "broadcast"


class TestMemberDispatchConversion:
    """Tests for team_settings_to_team_config conversion."""

    def test_selective_converted(self) -> None:
        """selectiveがTeamConfigに正しく変換される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="selective",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "selective"

    def test_broadcast_converted(self) -> None:
        """broadcastがTeamConfigに正しく変換される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            member_dispatch="broadcast",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "broadcast"

    def test_default_preserved_when_not_specified(self) -> None:
        """未指定時のデフォルトが変換後も保持される."""
        settings = TeamSettings(
            team_id="test-team",
            team_name="Test Team",
            leader={"model": "google-gla:gemini-2.5-flash-lite"},
        )
        config = team_settings_to_team_config(settings)
        assert config.member_dispatch == "selective"
