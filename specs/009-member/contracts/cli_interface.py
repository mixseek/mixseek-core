# CLI Interface Contract
# This file defines the CLI command contracts and interfaces
#
# NOTE: This is a specification contract file. In the actual implementation,
# MemberAgentResult will be imported from:
# - from mixseek.models.result import MemberAgentResult

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

# Forward references for specification purposes
if TYPE_CHECKING:
    from mixseek.models.member_agent import MemberAgentResult
else:
    # For specification purposes, define minimal type stub
    class MemberAgentResult:
        """Type stub - actual implementation in mixseek.models.member_agent"""

        pass


class OutputFormat(str, Enum):
    """Supported CLI output formats."""

    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class CLICommand(BaseModel):
    """Base model for CLI commands."""

    verbose: bool = Field(default=False, description="Enable verbose output")
    output_format: OutputFormat = Field(
        default=OutputFormat.STRUCTURED, description="Output format for command results"
    )

    model_config = ConfigDict(use_enum_values=True)


class TestMemberCommand(CLICommand):
    """Command model for 'mixseek member' CLI command."""

    # Required parameters
    prompt: str = Field(..., min_length=1, description="User prompt to send to Member Agent")

    # Agent specification (mutually exclusive)
    config_file: Path | None = Field(default=None, description="Path to agent TOML configuration file")
    agent_name: str | None = Field(default=None, description="Name of predefined agent configuration")

    # Execution options
    timeout: int = Field(default=30, gt=0, le=300, description="Execution timeout in seconds")
    max_tokens: int | None = Field(default=None, gt=0, le=8192, description="Override max tokens for this execution")
    temperature: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override temperature for this execution"
    )

    def validate_agent_specification(self) -> None:
        """Validate that exactly one agent specification is provided."""
        specs_provided = sum([self.config_file is not None, self.agent_name is not None])

        if specs_provided == 0:
            raise ValueError("One of --config or --agent must be specified")
        elif specs_provided > 1:
            raise ValueError("Cannot specify both --config and --agent")

    def get_effective_config_path(self, base_config_dir: Path) -> Path:
        """Get effective configuration file path."""
        if self.config_file:
            if not self.config_file.is_absolute():
                # Make relative paths relative to current directory
                return Path.cwd() / self.config_file
            return self.config_file
        elif self.agent_name:
            # Look for agent in standard config directory
            return base_config_dir / f"{self.agent_name}.toml"
        else:
            raise ValueError("No agent specification provided")


class ListAgentsCommand(CLICommand):
    """Command model for listing available agents."""

    config_dir: Path | None = Field(default=None, description="Directory to search for agent configurations")
    show_details: bool = Field(default=False, description="Show detailed agent information")


class ValidateConfigCommand(CLICommand):
    """Command model for validating agent configurations."""

    config_file: Path = Field(..., description="Path to configuration file to validate")
    strict: bool = Field(default=False, description="Enable strict validation mode")


class CLIResult(BaseModel):
    """CLI command execution result."""

    success: bool = Field(..., description="Whether command succeeded")
    message: str = Field(..., description="Result message or error description")

    # Command context
    command: str = Field(..., description="Command that was executed")
    execution_time_ms: int = Field(..., description="CLI execution time in milliseconds")

    # Optional result data
    data: dict[str, Any] | None = Field(default=None, description="Command-specific result data")

    # Member agent result (for member command)
    agent_result: MemberAgentResult | None = Field(default=None, description="Member agent execution result")

    # Warnings and additional info
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings during execution")

    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)

    def format_output(self, format_type: OutputFormat) -> str:
        """Format result for CLI output.

        Args:
            format_type: Desired output format

        Returns:
            Formatted output string
        """
        if format_type == OutputFormat.JSON:
            return self.model_dump_json(indent=2, exclude_none=True)

        elif format_type == OutputFormat.TEXT:
            # Simple text output - just the message
            output = self.message
            if self.warnings:
                output += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in self.warnings)
            return output

        else:  # STRUCTURED
            lines = [
                f"Command: {self.command}",
                f"Status: {'SUCCESS' if self.success else 'ERROR'}",
                f"Duration: {self.execution_time_ms}ms",
                "",
                f"Message: {self.message}",
            ]

            # Add agent result details if present
            if self.agent_result:
                lines.extend(
                    [
                        "",
                        "Agent Details:",
                        f"  Name: {self.agent_result.agent_name}",
                        f"  Type: {self.agent_result.agent_type}",
                        f"  Status: {self.agent_result.status}",
                        f"  Execution Time: {self.agent_result.execution_time_ms or 0}ms",
                    ]
                )

                # Add usage info if available
                if self.agent_result.usage_info:
                    lines.append("  Usage:")
                    for key, value in self.agent_result.usage_info.items():
                        lines.append(f"    {key}: {value}")

                # Add content preview
                content = self.agent_result.content
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    lines.extend(["", "Agent Output:", f"  {preview}"])

                # Add error details if present
                if self.agent_result.error_message:
                    lines.extend(["", "Error Details:", f"  {self.agent_result.error_message}"])

            # Add warnings
            if self.warnings:
                lines.extend(["", "Warnings:"])
                for warning in self.warnings:
                    lines.append(f"  - {warning}")

            # Add additional data if present
            if self.data:
                lines.extend(["", "Additional Data:", str(self.data)])

            return "\n".join(lines)

    @classmethod
    def create_success(
        cls,
        message: str,
        command: str,
        execution_time_ms: int,
        data: dict[str, Any] | None = None,
        agent_result: MemberAgentResult | None = None,
    ) -> "CLIResult":
        """Create successful CLI result."""
        return cls(
            success=True,
            message=message,
            command=command,
            execution_time_ms=execution_time_ms,
            data=data,
            agent_result=agent_result,
        )

    @classmethod
    def error(
        cls, message: str, command: str, execution_time_ms: int, data: dict[str, Any] | None = None
    ) -> "CLIResult":
        """Create error CLI result."""
        return cls(success=False, message=message, command=command, execution_time_ms=execution_time_ms, data=data)


# CLI Command Handler Protocol


class CLICommandHandler(Protocol):
    """Protocol for CLI command handlers."""

    def handle(self, command: CLICommand) -> CLIResult:
        """Handle CLI command execution.

        Args:
            command: Validated CLI command to execute

        Returns:
            CLI execution result
        """
        ...

    def validate_command(self, command: CLICommand) -> bool:
        """Validate command before execution.

        Args:
            command: Command to validate

        Returns:
            True if command is valid

        Raises:
            ValueError: If command is invalid
        """
        ...


class TestMemberCommandHandler:
    """Handler for 'mixseek member' command."""

    def __init__(self, config_base_dir: Path, development_mode: bool = True):
        """Initialize command handler.

        Args:
            config_base_dir: Base directory for agent configurations
            development_mode: Enable development mode warnings
        """
        self.config_base_dir = config_base_dir
        self.development_mode = development_mode

    def handle(self, command: TestMemberCommand) -> CLIResult:
        """Handle member command execution."""
        # Implementation will be in the actual CLI module
        raise NotImplementedError("Implementation will be in the actual CLI module")

    def validate_command(self, command: TestMemberCommand) -> bool:
        """Validate member command."""
        try:
            command.validate_agent_specification()
            config_path = command.get_effective_config_path(self.config_base_dir)

            if not config_path.exists():
                raise ValueError(f"Configuration file not found: {config_path}")

            return True
        except ValueError:
            raise


class ListAgentsCommandHandler:
    """Handler for listing available agents."""

    def __init__(self, config_base_dir: Path):
        """Initialize command handler.

        Args:
            config_base_dir: Base directory for agent configurations
        """
        self.config_base_dir = config_base_dir

    def handle(self, command: ListAgentsCommand) -> CLIResult:
        """Handle list-agents command execution."""
        # Implementation will be in the actual CLI module
        raise NotImplementedError("Implementation will be in the actual CLI module")

    def validate_command(self, command: ListAgentsCommand) -> bool:
        """Validate list-agents command."""
        config_dir = command.config_dir or self.config_base_dir
        if not config_dir.exists():
            raise ValueError(f"Configuration directory not found: {config_dir}")
        return True


class ValidateConfigCommandHandler:
    """Handler for configuration validation."""

    def handle(self, command: ValidateConfigCommand) -> CLIResult:
        """Handle validate-config command execution."""
        # Implementation will be in the actual CLI module
        raise NotImplementedError("Implementation will be in the actual CLI module")

    def validate_command(self, command: ValidateConfigCommand) -> bool:
        """Validate validate-config command."""
        if not command.config_file.exists():
            raise ValueError(f"Configuration file not found: {command.config_file}")
        return True


# CLI Application Interface


class CLIApplication(Protocol):
    """Protocol for the main CLI application."""

    def run(self, args: list[str]) -> int:
        """Run the CLI application.

        Args:
            args: Command line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        ...

    def register_command(self, command_name: str, handler: CLICommandHandler) -> None:
        """Register a command handler.

        Args:
            command_name: Name of the command
            handler: Command handler implementation
        """
        ...


# Development Mode Warning Contract


class DevelopmentWarning:
    """Utility for displaying development mode warnings."""

    @staticmethod
    def show_development_warning() -> str:
        """Generate development mode warning message."""
        return (
            "⚠️  DEVELOPMENT MODE WARNING ⚠️\n"
            "\n"
            "This Member Agent execution is intended for development and testing only.\n"
            "For production use, integrate with the full MixSeek-Core framework.\n"
            "\n"
            "Features limited in development mode:\n"
            "  - No TUMIX framework integration\n"
            "  - No Leader Agent coordination\n"
            "  - No persistent result storage\n"
            "  - Usage tracking may be incomplete\n"
            "\n"
            "Set MIXSEEK_DEVELOPMENT_MODE=false to suppress this warning.\n"
        )

    @staticmethod
    def should_show_warning(development_mode: bool, suppress_warnings: bool = False) -> bool:
        """Determine if development warning should be shown.

        Args:
            development_mode: Whether development mode is enabled
            suppress_warnings: Whether to suppress warnings

        Returns:
            True if warning should be displayed
        """
        return development_mode and not suppress_warnings


# Export all CLI contracts
__all__ = [
    # Enums
    "OutputFormat",
    # Command Models
    "CLICommand",
    "TestMemberCommand",
    "ListAgentsCommand",
    "ValidateConfigCommand",
    "CLIResult",
    # Protocols
    "CLICommandHandler",
    "CLIApplication",
    # Command Handlers
    "TestMemberCommandHandler",
    "ListAgentsCommandHandler",
    "ValidateConfigCommandHandler",
    # Utilities
    "DevelopmentWarning",
]
