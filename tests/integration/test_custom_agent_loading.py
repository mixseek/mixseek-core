"""Integration tests for custom agent loading end-to-end.

This module tests the complete flow of loading and executing custom agents:
- agent_module method: Load from Python package → Execute
- path method: Load from file path → Execute
"""

import sys

import pytest

from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.config.member_agent_loader import MemberAgentLoader
from mixseek.models.member_agent import ResultStatus

# Test custom agent implementation (similar to SimpleCustomAgent)
TEST_AGENT_CODE = '''"""Test custom agent for integration testing."""

from typing import Any
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult


class TestCustomAgent(BaseMemberAgent):
    """A test custom agent for integration testing."""

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemberAgentResult:
        """Execute the task and return a test response."""
        response = f"[TestCustomAgent] Received: {task}"

        return MemberAgentResult.success(
            content=response,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
'''


class TestCustomAgentE2E:
    """End-to-end tests for custom agent loading and execution."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_from_path_and_execute(self, tmp_path, monkeypatch):
        """Load custom agent via path method and execute a task."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a custom agent Python file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text(TEST_AGENT_CODE)

        # Create TOML config pointing to the file
        toml_content = f"""[agent]
name = "test-custom-agent"
type = "custom"
model = "anthropic:claude-3-5-haiku-20241022"
max_tokens = 1024
description = "Test custom agent for integration testing"

[agent.system_instruction]
text = "You are a test agent."

[agent.plugin]
path = "{agent_file}"
agent_class = "TestCustomAgent"
"""
        toml_file = tmp_path / "test_agent.toml"
        toml_file.write_text(toml_content)

        # Load config → Create agent → Execute task
        config = MemberAgentLoader.load_config(toml_file)
        agent = MemberAgentFactory.create_agent(config)

        result = await agent.execute("Hello, integration test!")

        # Verify result is successful
        assert result.status == ResultStatus.SUCCESS
        assert result.content == "[TestCustomAgent] Received: Hello, integration test!"
        assert result.agent_name == "test-custom-agent"
        assert result.agent_type == "custom"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_from_module_and_execute(self, tmp_path, monkeypatch):
        """Load custom agent via agent_module method and execute a task."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a mock Python package with custom agent
        package_dir = tmp_path / "test_package"
        package_dir.mkdir()

        # Create __init__.py to make it a package
        (package_dir / "__init__.py").write_text("")

        # Create agents module
        agents_dir = package_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "__init__.py").write_text("")

        # Create custom agent file
        agent_file = agents_dir / "test_agent.py"
        agent_file.write_text(TEST_AGENT_CODE)

        # Add tmp_path to sys.path temporarily for import
        sys.path.insert(0, str(tmp_path))
        try:
            # Create TOML config pointing to the package
            toml_content = """[agent]
name = "test-module-agent"
type = "custom"
model = "anthropic:claude-3-5-haiku-20241022"
max_tokens = 1024
description = "Test custom agent loaded from module"

[agent.system_instruction]
text = "You are a test agent loaded from module."

[agent.plugin]
agent_module = "test_package.agents.test_agent"
agent_class = "TestCustomAgent"
"""
            toml_file = tmp_path / "test_module_agent.toml"
            toml_file.write_text(toml_content)

            # Load config → Create agent → Execute task
            config = MemberAgentLoader.load_config(toml_file)
            agent = MemberAgentFactory.create_agent(config)

            result = await agent.execute("Hello from module!")

            # Verify result is successful
            assert result.status == ResultStatus.SUCCESS
            assert result.content == "[TestCustomAgent] Received: Hello from module!"
            assert result.agent_name == "test-module-agent"
            assert result.agent_type == "custom"
        finally:
            # Clean up sys.path
            sys.path.remove(str(tmp_path))

    @pytest.mark.integration
    def test_load_from_toml_with_path(self, tmp_path, monkeypatch):
        """Load custom agent configuration from TOML file with path."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create a custom agent Python file
        agent_file = tmp_path / "test_agent_config.py"
        agent_file.write_text(TEST_AGENT_CODE)

        # Create TOML file with path configuration
        toml_content = f"""[agent]
name = "test-path-config"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
max_tokens = 2048
description = "Test custom agent config with path"

[agent.system_instruction]
text = "Test agent for config loading."

[agent.plugin]
path = "{agent_file}"
agent_class = "TestCustomAgent"
"""
        toml_file = tmp_path / "test_path_config.toml"
        toml_file.write_text(toml_content)

        # Use MemberAgentLoader to parse TOML
        config = MemberAgentLoader.load_config(toml_file)

        # Verify plugin metadata is correctly parsed
        assert config.name == "test-path-config"
        assert config.type == "custom"
        assert config.plugin is not None
        assert config.plugin.path == str(agent_file)
        assert config.plugin.agent_class == "TestCustomAgent"
        assert config.plugin.agent_module is None

        # Verify other config fields
        assert config.model == "google-gla:gemini-2.5-flash-lite"
        assert config.max_tokens == 2048

    @pytest.mark.integration
    def test_load_from_toml_with_agent_module(self, tmp_path, monkeypatch):
        """Load custom agent configuration from TOML file with agent_module."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create TOML file with agent_module configuration
        toml_content = """[agent]
name = "test-module-config"
type = "custom"
model = "anthropic:claude-3-5-haiku-20241022"
max_tokens = 4096
description = "Test custom agent config with agent_module"

[agent.system_instruction]
text = "Test agent for module config loading."

[agent.plugin]
agent_module = "my_package.agents.custom"
agent_class = "MyCustomAgent"
"""
        toml_file = tmp_path / "test_module_config.toml"
        toml_file.write_text(toml_content)

        # Use MemberAgentLoader to parse TOML
        config = MemberAgentLoader.load_config(toml_file)

        # Verify plugin metadata is correctly parsed
        assert config.name == "test-module-config"
        assert config.type == "custom"
        assert config.plugin is not None
        assert config.plugin.agent_module == "my_package.agents.custom"
        assert config.plugin.agent_class == "MyCustomAgent"
        assert config.plugin.path is None

        # Verify other config fields
        assert config.model == "anthropic:claude-3-5-haiku-20241022"
        assert config.max_tokens == 4096

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_multiple_agents_from_path(self, tmp_path, monkeypatch):
        """Load multiple different custom agents from path to verify no collision."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create first custom agent
        agent1_code = """
from typing import Any
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult

class Agent1(BaseMemberAgent):
    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        return MemberAgentResult.success(
            content=f"[Agent1] {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
"""
        agent1_file = tmp_path / "agent1.py"
        agent1_file.write_text(agent1_code)

        # Create second custom agent
        agent2_code = """
from typing import Any
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult

class Agent2(BaseMemberAgent):
    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        return MemberAgentResult.success(
            content=f"[Agent2] {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
"""
        agent2_file = tmp_path / "agent2.py"
        agent2_file.write_text(agent2_code)

        # Create TOML configs
        toml1_content = f"""[agent]
name = "agent-one"
type = "custom"
model = "anthropic:claude-3-5-haiku-20241022"
max_tokens = 1024

[agent.system_instruction]
text = "Agent 1"

[agent.plugin]
path = "{agent1_file}"
agent_class = "Agent1"
"""
        toml1_file = tmp_path / "agent1.toml"
        toml1_file.write_text(toml1_content)

        toml2_content = f"""[agent]
name = "agent-two"
type = "custom"
model = "anthropic:claude-3-5-haiku-20241022"
max_tokens = 1024

[agent.system_instruction]
text = "Agent 2"

[agent.plugin]
path = "{agent2_file}"
agent_class = "Agent2"
"""
        toml2_file = tmp_path / "agent2.toml"
        toml2_file.write_text(toml2_content)

        # Load both agents
        config1 = MemberAgentLoader.load_config(toml1_file)
        agent1 = MemberAgentFactory.create_agent(config1)

        config2 = MemberAgentLoader.load_config(toml2_file)
        agent2 = MemberAgentFactory.create_agent(config2)

        # Execute both agents
        result1 = await agent1.execute("Test 1")
        result2 = await agent2.execute("Test 2")

        # Verify both agents work correctly (no collision)
        assert result1.status == ResultStatus.SUCCESS
        assert result1.content == "[Agent1] Test 1"
        assert result1.agent_name == "agent-one"

        assert result2.status == ResultStatus.SUCCESS
        assert result2.content == "[Agent2] Test 2"
        assert result2.agent_name == "agent-two"
