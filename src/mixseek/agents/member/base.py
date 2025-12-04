"""Base Member Agent implementation.

This module contains the abstract base class for all Member Agent types,
implementing the common interface and error handling patterns.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic_ai.settings import ModelSettings

from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult
from mixseek.utils.logging import MemberAgentLogger


class BaseMemberAgent(ABC):
    """Abstract base class for all Member Agent implementations."""

    def __init__(self, config: MemberAgentConfig):
        """Initialize base agent with configuration.

        Args:
            config: Validated agent configuration
        """
        self.config = config
        # デフォルトの log_level は "INFO"（別の issue で対応予定）
        self.logger = MemberAgentLogger(log_level="INFO", enable_file_logging=True)

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

        Generates Pydantic AI ModelSettings from the agent configuration,
        including temperature, max_tokens, stop_sequences, top_p, seed, and timeout.

        Returns:
            ModelSettings TypedDict (may be empty if no settings configured)

        Note:
            ModelSettings is a TypedDict with all optional fields (total=False).
            Only non-None values from config are included in the returned dict.
            An empty dict is a valid ModelSettings and will use model defaults.

            The 'seed' parameter is supported by OpenAI and Gemini but not by Anthropic.
            If using Anthropic models with seed configured, the seed will be ignored.
        """
        # Build ModelSettings TypedDict with only non-None values
        settings: ModelSettings = {}

        if self.config.temperature is not None:
            settings["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            settings["max_tokens"] = self.config.max_tokens
        if self.config.stop_sequences is not None:
            settings["stop_sequences"] = self.config.stop_sequences
        if self.config.top_p is not None:
            settings["top_p"] = self.config.top_p
        if self.config.seed is not None:
            settings["seed"] = self.config.seed
        if self.config.timeout_seconds is not None:
            settings["timeout"] = float(self.config.timeout_seconds)

        return settings
