# Member Agent Interface Contract
# This file defines the interface contracts for Member Agent implementation
#
# NOTE: This is a specification contract file. In the actual implementation,
# these types will be imported from their respective modules:
# - from mixseek.models.member_agent import MemberAgentConfig, AgentType
# - from mixseek.models.result import MemberAgentResult

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

# Forward references for specification purposes
# In actual implementation, these will be proper imports
if TYPE_CHECKING:
    from mixseek.models.member_agent import AgentType, MemberAgentConfig, MemberAgentResult

    from .cli_interface import CLIResult  # type: ignore[import-not-found]
else:
    # For specification purposes, define minimal type stubs
    class AgentType:
        PLAIN = "plain"
        WEB_SEARCH = "web_search"
        CODE_EXECUTION = "code_execution"

    class MemberAgentConfig:
        """Type stub - actual implementation in mixseek.models.member_agent"""

        pass

    class MemberAgentResult:
        """Type stub - actual implementation in mixseek.models.member_agent"""

        pass


@runtime_checkable
class MemberAgentProtocol(Protocol):
    """Protocol defining the interface for all Member Agents.

    This protocol ensures all Member Agent implementations provide
    consistent interfaces for the MixSeek-Core framework integration.
    """

    @property
    def config(self) -> MemberAgentConfig:
        """Agent configuration."""
        ...

    @property
    def agent_name(self) -> str:
        """Agent name identifier."""
        ...

    @property
    def agent_type(self) -> AgentType:
        """Agent type/capabilities."""
        ...

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute a task and return result (FR-005 compliant interface).

        This is the standard interface defined in specs/001-specs (FR-005).
        All Member Agents must implement this method for Leader Agent compatibility.

        Args:
            task: Task description from Leader Agent
            context: Optional context from Leader Agent or TUMIX
            **kwargs: Additional parameters for execution

        Returns:
            MemberAgentResult with execution outcome

        Raises:
            MemberAgentError: On execution failures
            ValidationError: On invalid input parameters
        """
        ...

    def validate_config(self) -> bool:
        """Validate agent configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: On invalid configuration
        """
        ...


class BaseMemberAgent(ABC):
    """Abstract base class for all Member Agent implementations.

    Provides common functionality and enforces interface compliance
    for all Member Agent types in the MixSeek-Core framework.
    """

    def __init__(self, config: MemberAgentConfig):
        """Initialize Member Agent with configuration.

        Args:
            config: Validated Member Agent configuration
        """
        self._config = config
        self._initialized = False

    @property
    def config(self) -> MemberAgentConfig:
        """Agent configuration."""
        return self._config

    @property
    def agent_name(self) -> str:
        """Agent name identifier."""
        return self._config.name

    @property
    def agent_type(self) -> str:
        """Agent type/capabilities."""
        return self._config.type

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task (FR-005 compliant interface - implementation required).

        This is the standard interface defined in specs/001-specs (FR-005).
        All Member Agent subclasses must implement this method for Leader Agent compatibility.

        Args:
            task: Task description from Leader Agent
            context: Optional context from Leader Agent or TUMIX
            **kwargs: Additional parameters for execution

        Returns:
            MemberAgentResult with execution outcome
        """
        pass

    def validate_config(self) -> bool:
        """Validate agent configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: On invalid configuration
        """
        try:
            # Pydantic validation already performed during __init__
            return True
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration: {e}")

    async def initialize(self) -> None:
        """Initialize agent resources (override if needed).

        Called before first use to set up any required resources,
        connections, or client instances.
        """
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up agent resources (override if needed).

        Called to release resources when agent is no longer needed.
        """
        self._initialized = False

    def is_initialized(self) -> bool:
        """Check if agent is initialized."""
        return self._initialized


class MemberAgentFactory:
    """Factory for creating Member Agent instances.

    Provides centralized agent creation with proper configuration
    validation and type-specific instantiation.
    """

    _agent_classes: dict[str, type[BaseMemberAgent]] = {}

    @classmethod
    def register_agent_type(cls, agent_type: str, agent_class: type[BaseMemberAgent]) -> None:
        """Register a Member Agent implementation.

        Args:
            agent_type: Type of agent to register
            agent_class: Agent implementation class
        """
        cls._agent_classes[agent_type] = agent_class

    @classmethod
    def create_agent(cls, config: MemberAgentConfig) -> BaseMemberAgent:
        """Create Member Agent instance from configuration.

        Args:
            config: Validated Member Agent configuration

        Returns:
            Initialized Member Agent instance

        Raises:
            UnsupportedAgentTypeError: If agent type not registered
            ConfigurationError: If configuration is invalid
        """
        agent_type = config.type

        if agent_type not in cls._agent_classes:
            raise UnsupportedAgentTypeError(
                f"Agent type '{agent_type}' not registered. Available types: {list(cls._agent_classes.keys())}"
            )

        agent_class: type[BaseMemberAgent] = cls._agent_classes[agent_type]
        return agent_class(config)

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported agent types.

        Returns:
            List of registered agent types
        """
        return list(cls._agent_classes.keys())


# CLI Command Interface Contract


@runtime_checkable
class CLICommandProtocol(Protocol):
    """Protocol for CLI command implementations."""

    def execute(self, args: dict[str, Any]) -> "CLIResult":
        """Execute CLI command.

        Args:
            args: Parsed command line arguments

        Returns:
            CLI execution result
        """
        ...

    def validate_args(self, args: dict[str, Any]) -> bool:
        """Validate command arguments.

        Args:
            args: Command line arguments to validate

        Returns:
            True if arguments are valid

        Raises:
            ArgumentError: If arguments are invalid
        """
        ...


# Configuration Loading Interface


@runtime_checkable
class ConfigLoaderProtocol(Protocol):
    """Protocol for configuration loading implementations."""

    def load_config(self, config_path: str) -> MemberAgentConfig:
        """Load Member Agent configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Validated Member Agent configuration

        Raises:
            ConfigurationError: If configuration is invalid
            FileNotFoundError: If configuration file doesn't exist
        """
        ...

    def validate_config_file(self, config_path: str) -> bool:
        """Validate configuration file format and content.

        Args:
            config_path: Path to configuration file

        Returns:
            True if configuration file is valid
        """
        ...


# TUMIX Integration Interface (Future)


class TUMIXClientProtocol(Protocol):
    """Protocol for TUMIX framework client integration.

    This interface defines how Member Agents will integrate with
    the TUMIX framework for Leader Agent communication.
    """

    async def register_agent(self, agent: BaseMemberAgent) -> str:
        """Register Member Agent with TUMIX framework.

        Args:
            agent: Member Agent to register

        Returns:
            Registration ID for agent
        """
        ...

    async def process_request(self, request_id: str, prompt: str, context: dict[str, Any]) -> MemberAgentResult:
        """Process request from Leader Agent via TUMIX.

        Args:
            request_id: Unique request identifier
            prompt: Processing prompt
            context: Context from Leader Agent

        Returns:
            Processing result
        """
        ...

    async def report_result(self, request_id: str, result: MemberAgentResult) -> None:
        """Report processing result back to Leader Agent.

        Args:
            request_id: Request identifier
            result: Processing result to report
        """
        ...


# Custom Exceptions


class MemberAgentError(Exception):
    """Base exception for Member Agent errors."""

    def __init__(self, message: str, agent_name: str | None = None, error_code: str | None = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.error_code = error_code


class ConfigurationError(MemberAgentError):
    """Exception for configuration-related errors."""

    pass


class UnsupportedAgentTypeError(MemberAgentError):
    """Exception for unsupported agent types."""

    pass


class ProcessingError(MemberAgentError):
    """Exception for processing failures."""

    def __init__(
        self, message: str, agent_name: str | None = None, error_code: str | None = None, prompt: str | None = None
    ):
        super().__init__(message, agent_name, error_code)
        self.prompt = prompt


class AuthenticationError(MemberAgentError):
    """Exception for authentication failures."""

    pass


class ArgumentError(Exception):
    """Exception for invalid CLI arguments."""

    pass


# Type Annotations for Interface Compliance


# Contract validation helpers
def validate_member_agent_interface(agent: Any) -> bool:
    """Validate that an object implements MemberAgentProtocol.

    Args:
        agent: Object to validate

    Returns:
        True if object implements the protocol
    """
    return isinstance(agent, MemberAgentProtocol)


def validate_cli_command_interface(command: Any) -> bool:
    """Validate that an object implements CLICommandProtocol.

    Args:
        command: Object to validate

    Returns:
        True if object implements the protocol
    """
    return isinstance(command, CLICommandProtocol)


def validate_config_loader_interface(loader: Any) -> bool:
    """Validate that an object implements ConfigLoaderProtocol.

    Args:
        loader: Object to validate

    Returns:
        True if object implements the protocol
    """
    return isinstance(loader, ConfigLoaderProtocol)


# Export all interface contracts
__all__ = [
    # Protocols
    "MemberAgentProtocol",
    "CLICommandProtocol",
    "ConfigLoaderProtocol",
    "TUMIXClientProtocol",
    # Base Classes
    "BaseMemberAgent",
    "MemberAgentFactory",
    # Exceptions
    "MemberAgentError",
    "ConfigurationError",
    "UnsupportedAgentTypeError",
    "ProcessingError",
    "AuthenticationError",
    "ArgumentError",
    # Validation Functions
    "validate_member_agent_interface",
    "validate_cli_command_interface",
    "validate_config_loader_interface",
]
