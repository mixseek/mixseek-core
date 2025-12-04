"""Unit tests for MemberAgentFactory custom agent loading with priority handling.

This module tests the priority handling logic (FR-021) when loading custom agents:
1. First priority: agent_module (recommended)
2. Second priority: path (fallback)
"""

import sys

import pytest

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.models.member_agent import MemberAgentConfig, PluginMetadata

# Valid custom agent code for testing
VALID_AGENT_CODE = '''"""Test custom agent for unit testing."""

from typing import Any
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult


class TestPriorityAgent(BaseMemberAgent):
    """A test custom agent for priority testing."""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemberAgentResult:
        """Execute the task."""
        return MemberAgentResult.success(
            content=f"Priority: {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
'''


class TestCustomAgentPriorityHandling:
    """Tests for FR-021 priority handling in custom agent loading."""

    def setup_method(self) -> None:
        """Setup before each test - ensure clean state."""
        # Remove any manually registered "custom" agent to test plugin configuration
        self._original_custom_agent: type | None
        if "custom" in MemberAgentFactory._agent_classes:
            self._original_custom_agent = MemberAgentFactory._agent_classes.pop("custom")
        else:
            self._original_custom_agent = None

    def teardown_method(self) -> None:
        """Teardown after each test - restore original state."""
        # Restore original "custom" agent if it existed
        if self._original_custom_agent is not None:
            MemberAgentFactory._agent_classes["custom"] = self._original_custom_agent
        elif "custom" in MemberAgentFactory._agent_classes:
            # Clean up if test registered "custom"
            MemberAgentFactory._agent_classes.pop("custom")

    def test_agent_module_priority(self, tmp_path, monkeypatch):
        """When both agent_module and path are specified, agent_module should be prioritized."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a Python package for agent_module
        package_dir = tmp_path / "priority_module"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")
        module_file = package_dir / "agent.py"
        module_file.write_text(VALID_AGENT_CODE)

        # Create a Python file for path (different location)
        path_file = tmp_path / "path_agent.py"
        path_file.write_text(VALID_AGENT_CODE)

        # Add to sys.path temporarily
        sys.path.insert(0, str(tmp_path))
        try:
            # Create config with BOTH agent_module and path
            plugin = PluginMetadata(
                agent_module="priority_module.agent",  # Priority 1
                path=str(path_file),  # Priority 2 (fallback)
                agent_class="TestPriorityAgent",
            )

            config = MemberAgentConfig(
                name="test-priority-agent",
                type="custom",
                model="anthropic:claude-3-5-haiku-20241022",
                system_instruction="Test agent",
                description="Test priority handling",
                plugin=plugin,
            )

            # Create agent - should use agent_module (priority 1)
            agent = MemberAgentFactory.create_agent(config)

            # Verify agent was successfully created
            assert isinstance(agent, BaseMemberAgent)
            assert agent.agent_name == "test-priority-agent"
            assert agent.agent_type == "custom"
            # Note: Dynamic loading does NOT register agents to prevent overwriting
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            if "priority_module" in sys.modules:
                del sys.modules["priority_module"]
            if "priority_module.agent" in sys.modules:
                del sys.modules["priority_module.agent"]

    def test_fallback_to_path(self, tmp_path, monkeypatch):
        """When agent_module fails, should fallback to path method."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a valid Python file for path (fallback)
        path_file = tmp_path / "fallback_agent.py"
        path_file.write_text(VALID_AGENT_CODE)

        # Create config with INVALID agent_module but VALID path
        plugin = PluginMetadata(
            agent_module="nonexistent_package.agents.custom",  # Will fail
            path=str(path_file),  # Should fallback to this
            agent_class="TestPriorityAgent",
        )

        config = MemberAgentConfig(
            name="test-fallback-agent",
            type="custom",
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test fallback to path",
            plugin=plugin,
        )

        # Create agent - should fallback to path method
        agent = MemberAgentFactory.create_agent(config)

        # Verify agent was successfully created using path fallback
        assert isinstance(agent, BaseMemberAgent)
        assert agent.agent_name == "test-fallback-agent"
        assert agent.agent_type == "custom"
        # Note: Dynamic loading does NOT register agents to prevent overwriting

    def test_both_methods_fail_error(self, tmp_path, monkeypatch):
        """When both agent_module and path fail, should raise appropriate error."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create config with BOTH invalid
        plugin = PluginMetadata(
            agent_module="nonexistent_package.agents.custom",  # Will fail
            path="/nonexistent/path/agent.py",  # Will also fail
            agent_class="NonexistentAgent",
        )

        config = MemberAgentConfig(
            name="test-fail-agent",
            type="custom",
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test both methods fail",
            plugin=plugin,
        )

        # Should raise FileNotFoundError from path method (after agent_module fails)
        with pytest.raises(FileNotFoundError) as exc_info:
            MemberAgentFactory.create_agent(config)

        error_message = str(exc_info.value)
        assert "Failed to load custom agent from path" in error_message
        assert "/nonexistent/path/agent.py" in error_message

    def test_neither_specified_error(self):
        """When neither agent_module nor path is specified, should raise ValueError."""
        # Create config without plugin metadata
        config = MemberAgentConfig(
            name="test-custom-agent",
            type="custom",
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test custom agent without plugin config",
            metadata={},  # No plugin section
        )

        with pytest.raises(ValueError) as exc_info:
            MemberAgentFactory.create_agent(config)

        error_message = str(exc_info.value)
        # Error message should mention both agent_module and path as options
        assert "either 'agent_module' or 'path'" in error_message.lower()

    def test_plugin_section_missing_error(self):
        """When plugin section is completely missing, should raise clear error."""
        config = MemberAgentConfig(
            name="test-custom-agent",
            type="custom",
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test custom agent without plugin section",
            metadata={},  # No plugin at all
        )

        with pytest.raises(ValueError) as exc_info:
            MemberAgentFactory.create_agent(config)

        error_message = str(exc_info.value)
        # Should mention plugin section requirement
        assert "plugin" in error_message.lower()

    def test_plugin_with_only_agent_module(self, tmp_path, monkeypatch):
        """When only agent_module is specified (no path), should work correctly."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a Python package for agent_module
        package_dir = tmp_path / "module_only"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")
        module_file = package_dir / "agent.py"
        module_file.write_text(VALID_AGENT_CODE)

        # Add to sys.path temporarily
        sys.path.insert(0, str(tmp_path))
        try:
            # Create config with ONLY agent_module (no path)
            plugin = PluginMetadata(
                agent_module="module_only.agent",
                path=None,  # No path specified
                agent_class="TestPriorityAgent",
            )

            config = MemberAgentConfig(
                name="test-module-only-agent",
                type="custom",
                model="anthropic:claude-3-5-haiku-20241022",
                system_instruction="Test agent",
                description="Test agent_module only",
                plugin=plugin,
            )

            # Create agent - should use agent_module
            agent = MemberAgentFactory.create_agent(config)

            # Verify agent was successfully created
            assert isinstance(agent, BaseMemberAgent)
            assert agent.agent_name == "test-module-only-agent"
            assert agent.agent_type == "custom"
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            if "module_only" in sys.modules:
                del sys.modules["module_only"]
            if "module_only.agent" in sys.modules:
                del sys.modules["module_only.agent"]

    def test_plugin_with_only_path(self, tmp_path, monkeypatch):
        """When only path is specified (no agent_module), should work correctly."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a valid Python file for path
        path_file = tmp_path / "path_only_agent.py"
        path_file.write_text(VALID_AGENT_CODE)

        # Create config with ONLY path (no agent_module)
        plugin = PluginMetadata(
            agent_module=None,  # No agent_module specified
            path=str(path_file),
            agent_class="TestPriorityAgent",
        )

        config = MemberAgentConfig(
            name="test-path-only-agent",
            type="custom",
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test path only",
            plugin=plugin,
        )

        # Create agent - should use path
        agent = MemberAgentFactory.create_agent(config)

        # Verify agent was successfully created
        assert isinstance(agent, BaseMemberAgent)
        assert agent.agent_name == "test-path-only-agent"
        assert agent.agent_type == "custom"
