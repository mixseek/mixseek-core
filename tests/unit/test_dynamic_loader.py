"""Unit tests for dynamic custom agent loading.

This module tests the dynamic loading mechanism for custom Member Agents,
including both agent_module (recommended) and path (alternative) methods.
"""

import sys

import pytest

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.dynamic_loader import load_agent_from_module, load_agent_from_path
from mixseek.models.member_agent import MemberAgentConfig


@pytest.fixture
def mock_config():
    """Create a mock MemberAgentConfig for testing."""
    return MemberAgentConfig(
        name="test-custom-agent",
        type="custom",
        model="anthropic:claude-3-5-haiku-20241022",
        system_instruction="Test agent for custom loading",
        description="Test custom agent",
    )


# Valid custom agent code for testing
VALID_AGENT_CODE = '''"""Test custom agent for unit testing."""

from typing import Any
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult


class TestAgent(BaseMemberAgent):
    """A test custom agent."""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemberAgentResult:
        """Execute the task."""
        return MemberAgentResult.success(
            content=f"Test: {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
'''

# Python file with no agent class
FILE_WITHOUT_CLASS = '''"""File without the expected class."""

def some_function():
    return "not an agent"
'''

# Python file with class that doesn't inherit BaseMemberAgent
FILE_WITH_INVALID_CLASS = '''"""File with invalid agent class."""


class TestAgent:
    """Not a BaseMemberAgent subclass."""

    def __init__(self):
        pass
'''


class TestLoadAgentFromModule:
    """Tests for agent_module loading method."""

    def test_module_not_found_error(self, mock_config):
        """ModuleNotFoundError should provide clear error message with installation hint."""
        with pytest.raises(ModuleNotFoundError) as exc_info:
            load_agent_from_module(
                agent_module="nonexistent_package.agents.custom",
                agent_class="CustomAgent",
                config=mock_config,
            )
        error_message = str(exc_info.value)
        assert "Failed to load custom agent from module" in error_message
        assert "nonexistent_package.agents.custom" in error_message
        assert "Install package: pip install" in error_message

    def test_class_not_found_error(self, tmp_path, mock_config):
        """AttributeError should indicate missing class in module."""
        # Create a Python package without the expected class
        package_dir = tmp_path / "test_module_no_class"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")

        agent_file = package_dir / "agent.py"
        agent_file.write_text(FILE_WITHOUT_CLASS)

        # Add to sys.path temporarily
        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(AttributeError) as exc_info:
                load_agent_from_module(
                    agent_module="test_module_no_class.agent",
                    agent_class="NonexistentAgent",
                    config=mock_config,
                )
            error_message = str(exc_info.value)
            assert "Custom agent class 'NonexistentAgent' not found" in error_message
            assert "test_module_no_class.agent" in error_message
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            if "test_module_no_class" in sys.modules:
                del sys.modules["test_module_no_class"]
            if "test_module_no_class.agent" in sys.modules:
                del sys.modules["test_module_no_class.agent"]

    def test_not_inherit_base_agent_error(self, tmp_path, mock_config):
        """TypeError should indicate class doesn't inherit from BaseMemberAgent."""
        # Create a Python package with invalid class
        package_dir = tmp_path / "test_module_invalid"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")

        agent_file = package_dir / "agent.py"
        agent_file.write_text(FILE_WITH_INVALID_CLASS)

        # Add to sys.path temporarily
        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(TypeError) as exc_info:
                load_agent_from_module(
                    agent_module="test_module_invalid.agent",
                    agent_class="TestAgent",
                    config=mock_config,
                )
            error_message = str(exc_info.value)
            assert "must inherit from BaseMemberAgent" in error_message
            assert "TestAgent" in error_message
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            if "test_module_invalid" in sys.modules:
                del sys.modules["test_module_invalid"]
            if "test_module_invalid.agent" in sys.modules:
                del sys.modules["test_module_invalid.agent"]

    def test_load_valid_module(self, tmp_path, mock_config, monkeypatch):
        """Should successfully load a valid custom agent from module."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a Python package with valid agent
        package_dir = tmp_path / "test_module_valid"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")

        agent_file = package_dir / "agent.py"
        agent_file.write_text(VALID_AGENT_CODE)

        # Add to sys.path temporarily
        sys.path.insert(0, str(tmp_path))
        try:
            agent = load_agent_from_module(
                agent_module="test_module_valid.agent",
                agent_class="TestAgent",
                config=mock_config,
            )

            # Verify agent is correctly instantiated
            assert isinstance(agent, BaseMemberAgent)
            assert agent.agent_name == "test-custom-agent"
            assert agent.agent_type == "custom"
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            if "test_module_valid" in sys.modules:
                del sys.modules["test_module_valid"]
            if "test_module_valid.agent" in sys.modules:
                del sys.modules["test_module_valid.agent"]


class TestLoadAgentFromPath:
    """Tests for path loading method."""

    def test_file_not_found_error(self, mock_config):
        """FileNotFoundError should provide clear error message with path check hint."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_agent_from_path(
                path="/nonexistent/path/custom_agent.py",
                agent_class="CustomAgent",
                config=mock_config,
            )
        error_message = str(exc_info.value)
        assert "Failed to load custom agent from path" in error_message
        assert "/nonexistent/path/custom_agent.py" in error_message
        assert "Check file path in TOML config" in error_message

    def test_class_not_found_in_file_error(self, tmp_path, mock_config):
        """AttributeError should indicate missing class in file."""
        # Create a Python file without the expected class
        agent_file = tmp_path / "no_class.py"
        agent_file.write_text(FILE_WITHOUT_CLASS)

        with pytest.raises(AttributeError) as exc_info:
            load_agent_from_path(
                path=str(agent_file),
                agent_class="NonexistentAgent",
                config=mock_config,
            )
        error_message = str(exc_info.value)
        assert "Custom agent class 'NonexistentAgent' not found in file" in error_message
        assert str(agent_file) in error_message
        assert "Check agent_class in TOML config" in error_message

    def test_not_inherit_base_agent_error(self, tmp_path, mock_config):
        """TypeError should indicate class doesn't inherit from BaseMemberAgent."""
        # Create a Python file with invalid class
        agent_file = tmp_path / "invalid_class.py"
        agent_file.write_text(FILE_WITH_INVALID_CLASS)

        with pytest.raises(TypeError) as exc_info:
            load_agent_from_path(
                path=str(agent_file),
                agent_class="TestAgent",
                config=mock_config,
            )
        error_message = str(exc_info.value)
        assert "must inherit from BaseMemberAgent" in error_message
        assert "TestAgent" in error_message

    def test_load_valid_file(self, tmp_path, mock_config, monkeypatch):
        """Should successfully load a valid custom agent from file path."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a valid custom agent file
        agent_file = tmp_path / "valid_agent.py"
        agent_file.write_text(VALID_AGENT_CODE)

        agent = load_agent_from_path(
            path=str(agent_file),
            agent_class="TestAgent",
            config=mock_config,
        )

        # Verify agent is correctly instantiated
        assert isinstance(agent, BaseMemberAgent)
        assert agent.agent_name == "test-custom-agent"
        assert agent.agent_type == "custom"

    def test_multiple_agents_no_collision(self, tmp_path, mock_config, monkeypatch):
        """Loading multiple agents from different paths should not cause collision."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create first agent file
        agent1_file = tmp_path / "agent1.py"
        agent1_code = VALID_AGENT_CODE.replace("TestAgent", "Agent1")
        agent1_file.write_text(agent1_code)

        # Create second agent file
        agent2_file = tmp_path / "agent2.py"
        agent2_code = VALID_AGENT_CODE.replace("TestAgent", "Agent2")
        agent2_file.write_text(agent2_code)

        # Load both agents
        agent1 = load_agent_from_path(
            path=str(agent1_file),
            agent_class="Agent1",
            config=mock_config,
        )

        agent2 = load_agent_from_path(
            path=str(agent2_file),
            agent_class="Agent2",
            config=mock_config,
        )

        # Verify both agents are correctly loaded and independent
        assert isinstance(agent1, BaseMemberAgent)
        assert isinstance(agent2, BaseMemberAgent)
        assert type(agent1).__name__ == "Agent1"
        assert type(agent2).__name__ == "Agent2"
