"""Integration tests for custom agent through CLI code paths.

This module tests that custom agents work through the normal pipelines,
including AgentType enum casting and MemberSubmission creation.
"""

import pytest

from mixseek.agents.member.factory import MemberAgentFactory
from mixseek.models.leader_agent import MemberSubmission
from mixseek.models.member_agent import AgentType, MemberAgentConfig, PluginMetadata

# Test custom agent code
TEST_CUSTOM_AGENT = '''"""Test custom agent for CLI integration."""

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult


class CLITestAgent(BaseMemberAgent):
    """Test agent for CLI integration."""

    async def execute(
        self,
        task: str,
        context: dict[str, object] | None = None,
        **kwargs: object,
    ) -> MemberAgentResult:
        """Execute and return result."""
        return MemberAgentResult.success(
            content=f"CLI Test: {task}",
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
'''


class TestCustomAgentCLIIntegration:
    """Tests for custom agent through CLI code paths."""

    @pytest.mark.integration
    def test_agent_type_enum_includes_custom(self):
        """AgentType enum should include CUSTOM to support type casting in CLI."""
        # This is what CLI does: AgentType(member_config.agent_type)
        agent_type = AgentType("custom")

        assert agent_type == AgentType.CUSTOM
        assert str(agent_type) == "custom"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_custom_agent_result_to_member_submission(self, tmp_path, monkeypatch):
        """MemberAgentResult with type='custom' should convert to MemberSubmission without errors."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create custom agent file
        agent_file = tmp_path / "cli_test_agent.py"
        agent_file.write_text(TEST_CUSTOM_AGENT)

        # Create config with custom type
        plugin = PluginMetadata(
            path=str(agent_file),
            agent_class="CLITestAgent",
        )

        config = MemberAgentConfig(
            name="cli-test-agent",
            type="custom",  # This will be cast to AgentType.CUSTOM
            model="anthropic:claude-3-5-haiku-20241022",
            system_instruction="Test agent",
            description="Test custom agent for CLI",
            plugin=plugin,
        )

        # Create agent and execute (simulating CLI behavior)
        agent = MemberAgentFactory.create_agent(config)
        result = await agent.execute("Hello CLI!")

        # Verify result has custom type
        assert result.agent_type == "custom"

        # This is what leader aggregation model does:
        # MemberSubmission.from_member_result(result)
        # It casts result.agent_type to AgentType(...)
        submission = MemberSubmission.from_member_result(result)

        # Verify submission was created successfully
        assert submission.agent_name == "cli-test-agent"
        assert submission.agent_type == AgentType.CUSTOM
        assert submission.content == "CLI Test: Hello CLI!"
        assert submission.is_successful() is True

    @pytest.mark.integration
    def test_cli_config_to_agent_config_cast(self, tmp_path, monkeypatch):
        """Simulates CLI's AgentType(member_config.agent_type) cast for custom type."""
        # Set workspace for testing
        monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))

        # Create custom agent file
        agent_file = tmp_path / "cli_config_test.py"
        agent_file.write_text(TEST_CUSTOM_AGENT)

        # Simulate CLI behavior: config has agent_type as string
        class MockMemberConfig:
            agent_name = "mock-custom"
            agent_type = "custom"  # String from TOML
            model = "anthropic:claude-3-5-haiku-20241022"
            temperature = 0.7
            max_tokens = 1024
            system_instruction = "Test"
            system_prompt = None

        member_config = MockMemberConfig()

        # This is what CLI does (team.py:L217-225)
        try:
            agent_type_enum = AgentType(member_config.agent_type)
        except ValueError as e:
            pytest.fail(f"AgentType cast failed for 'custom': {e}")

        # Verify cast succeeded
        assert agent_type_enum == AgentType.CUSTOM

        # Create MemberAgentConfig with enum (as CLI does)
        plugin = PluginMetadata(
            path=str(agent_file),
            agent_class="CLITestAgent",
        )

        member_agent_config = MemberAgentConfig(
            name=member_config.agent_name,
            type=agent_type_enum,  # AgentType.CUSTOM
            model=member_config.model,
            temperature=member_config.temperature,
            max_tokens=member_config.max_tokens,
            system_instruction=member_config.system_instruction,
            system_prompt=member_config.system_prompt,
            plugin=plugin,
        )

        # Verify agent can be created (as CLI does)
        agent = MemberAgentFactory.create_agent(member_agent_config)
        assert agent.agent_name == "mock-custom"
        assert agent.agent_type == "custom"
