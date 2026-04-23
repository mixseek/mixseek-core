"""Base Member Agent implementation.

This module contains the abstract base class for all Member Agent types,
implementing the common interface and error handling patterns.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic_ai.settings import ModelSettings

from mixseek.agents.member.logging import MemberAgentLogger
from mixseek.core.model_settings import build_model_settings
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult


class BaseMemberAgent(ABC):
    """Abstract base class for all Member Agent implementations."""

    def __init__(self, config: MemberAgentConfig):
        """Initialize base agent with configuration.

        Args:
            config: Validated agent configuration
        """
        self.config = config
        self.logger = MemberAgentLogger()

    @property
    def agent_name(self) -> str:
        """Get agent name from configuration."""
        return self.config.name

    @property
    def agent_type(self) -> str:
        """Get agent type from configuration."""
        return self.config.type

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task with the agent.

        Args:
            task: User task or prompt to execute
            context: Optional context information
            **kwargs: Additional execution parameters

        Returns:
            MemberAgentResult with execution outcome

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement execute method")

    async def initialize(self) -> None:
        """Initialize agent resources (override if needed).

        This method is called before the agent is used and can be overridden
        by subclasses to perform any necessary initialization.
        """
        pass

    async def cleanup(self) -> None:
        """Cleanup agent resources (override if needed).

        This method can be overridden by subclasses to perform cleanup
        when the agent is no longer needed.
        """
        pass

    def _create_model_settings(self) -> ModelSettings:
        """Create ModelSettings from MemberAgentConfig.

        共通ヘルパ mixseek.core.model_settings.build_model_settings に委譲する。
        reasoning_effort のプロバイダ別ディスパッチもこの中で行われる。
        """
        return build_model_settings(self.config)
