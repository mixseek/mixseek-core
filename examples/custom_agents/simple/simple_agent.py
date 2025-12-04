"""Simple Custom Member Agent - Minimal Example.

This is the simplest possible custom agent implementation for MixSeek-Core.
It demonstrates the minimum requirements to create a working custom agent.

Usage:
    1. Set your API key:
       export GOOGLE_API_KEY="your-api-key"

    2. Run the agent:
       mixseek member "Your question here" --config simple_agent.toml
"""

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentResult


class SimpleCustomAgent(BaseMemberAgent):
    """A simple custom agent that echoes back the user's task.

    This agent demonstrates the minimum implementation required for a custom
    Member Agent. It simply echoes back the user's input with a prefix.
    """

    async def execute(
        self,
        task: str,
        context: dict[str, object] | None = None,
        **kwargs: object,
    ) -> MemberAgentResult:
        """Execute the task and return a simple response.

        Args:
            task: User task/prompt to process
            context: Optional context information (unused in this example)
            **kwargs: Additional parameters (unused in this example)

        Returns:
            MemberAgentResult with success response
        """
        # Simple processing - echo back with a message
        response = f"[SimpleCustomAgent] Received task: {task}"

        if context:
            response += f"\nContext keys: {list(context.keys())}"

        return MemberAgentResult.success(
            content=response,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
        )
