"""Unit tests for bundled member agent configuration loader.

Tests the BundledMemberAgentLoader class which loads standard member agent configurations
from package resources.
"""

from pathlib import Path

import pytest

from mixseek.config.bundled_member_agents import BundledMemberAgentError, BundledMemberAgentLoader


class TestBundledMemberAgentLoader:
    """Tests for bundled member agent configuration loader."""

    def test_load_plain_agent_success(self, tmp_path: Path) -> None:
        """Test successful loading of plain agent."""
        loader = BundledMemberAgentLoader(workspace=tmp_path)
        settings = loader.load("plain")

        assert settings.agent_name == "plain"
        assert settings.agent_type == "plain"
        assert "gemini-2.5-flash-lite" in settings.model
        assert settings.system_instruction  # Now str | None, check it's truthy

    def test_load_web_search_agent_success(self, tmp_path: Path) -> None:
        """Test successful loading of web-search agent."""
        loader = BundledMemberAgentLoader(workspace=tmp_path)
        settings = loader.load("web-search")

        assert settings.agent_name == "web-search"
        assert settings.agent_type == "web_search"
        assert "gemini-2.5-flash-lite" in settings.model

    def test_load_code_exec_agent_success(self, tmp_path: Path) -> None:
        """Test successful loading of code-exec agent."""
        loader = BundledMemberAgentLoader(workspace=tmp_path)
        settings = loader.load("code-exec")

        assert settings.agent_name == "code-exec"
        assert settings.agent_type == "code_execution"
        assert "claude-haiku-4-5" in settings.model

    def test_load_invalid_agent_name_error(self, tmp_path: Path) -> None:
        """Test error for invalid agent name."""
        loader = BundledMemberAgentLoader(workspace=tmp_path)

        with pytest.raises(BundledMemberAgentError) as exc_info:
            loader.load("invalid-agent")  # type: ignore[arg-type]

        assert "Unknown member agent 'invalid-agent'" in str(exc_info.value)
        assert "Available agents:" in str(exc_info.value)

    def test_list_available_agents(self) -> None:
        """Test listing all available bundled member agents."""
        loader = BundledMemberAgentLoader()
        agents = loader.list_available()

        assert set(agents) == {"plain", "web-search", "code-exec"}
