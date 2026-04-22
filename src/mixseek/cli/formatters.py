"""Result formatters for different output formats.

This module provides formatting utilities for displaying Member Agent results
in various formats including structured text, JSON, and plain text.
"""

import dataclasses
import json
import textwrap
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

import typer
from pydantic_ai.messages import ModelRequest, ModelResponse

from mixseek.models.member_agent import MemberAgentResult


def _json_encoder(obj: Any) -> Any:
    """Custom JSON encoder for Pydantic models, dataclasses, datetime, and enums.

    Args:
        obj: Object to encode

    Returns:
        JSON-serializable representation

    Raises:
        TypeError: If object cannot be serialized
    """
    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Handle Enum objects
    elif isinstance(obj, Enum):
        return obj.value
    # Try Pydantic v2 model_dump()
    elif hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    # Try Pydantic v1 dict()
    elif hasattr(obj, "dict"):
        return obj.dict()
    # Try dataclasses (check if instance, not class)
    elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    # Try __dict__
    elif hasattr(obj, "__dict__"):
        return vars(obj)
    # Last resort: convert to string
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class ResultFormatter:
    """Formatter for Member Agent results in different output formats."""

    @staticmethod
    def _echo_truncated_content(content: str, prefix: str, max_len: int = 200) -> None:
        """Truncate and print content with a prefix.

        Args:
            content: Content to display
            prefix: Prefix string to add before content
            max_len: Maximum content length before truncation (default: 200)
        """
        content_str = str(content)
        if len(content_str) > max_len:
            typer.echo(f"{prefix}{content_str[:max_len]}...")
        else:
            typer.echo(f"{prefix}{content_str}")

    @staticmethod
    def _format_message_history(messages: list[Any]) -> None:
        """Format message history for verbose output.

        Args:
            messages: List of Pydantic AI ModelMessage objects
        """
        for idx, message in enumerate(messages, start=1):
            typer.echo()
            typer.secho(f"  [{idx}] {message.__class__.__name__}", fg=typer.colors.BRIGHT_CYAN, bold=True)

            if isinstance(message, ModelRequest):
                # User request
                instructions = message.instructions if message.instructions else ""
                ResultFormatter._echo_truncated_content(instructions, "      Instructions: ", max_len=100)
                for part in message.parts:
                    part_type = part.__class__.__name__
                    typer.echo(f"      Part: {part_type}")
                    if hasattr(part, "content"):
                        content = str(part.content) if part.content else ""
                        ResultFormatter._echo_truncated_content(content, "        Content: ")

            elif isinstance(message, ModelResponse):
                # Model response (text or tool calls)
                typer.echo(f"      Model: {message.model_name}")
                if message.usage:
                    usage_str = f"input={message.usage.input_tokens}, output={message.usage.output_tokens}"
                    typer.echo(f"      Usage: {usage_str}")

                # Type cast to Any to handle various part types
                parts: list[Any] = list(message.parts)
                for part in parts:
                    part_type = part.__class__.__name__
                    typer.secho(f"      Part: {part_type}", fg=typer.colors.YELLOW)

                    if part_type == "TextPart" and hasattr(part, "content"):
                        content = str(part.content) if part.content else ""
                        ResultFormatter._echo_truncated_content(content, "        Content: ")

                    elif part_type == "ToolCallPart" and hasattr(part, "tool_name"):
                        # Tool call details
                        typer.secho(f"        Tool: {part.tool_name}", fg=typer.colors.GREEN, bold=True)
                        if hasattr(part, "args") and part.args:
                            # Convert args to dict for JSON serialization
                            args_dict = part.args.model_dump() if hasattr(part.args, "model_dump") else part.args
                            args_str = json.dumps(args_dict, indent=2, ensure_ascii=False)
                            # Indent each line of the JSON output using textwrap
                            indented_args = textwrap.indent(args_str, "          ")
                            typer.echo(f"        Args:\n{indented_args}")

                    elif part_type == "ToolReturnPart" and hasattr(part, "tool_name"):
                        # Tool return details
                        typer.secho(f"        Tool Return: {part.tool_name}", fg=typer.colors.MAGENTA, bold=True)
                        if hasattr(part, "content"):
                            content = str(part.content) if part.content else ""
                            ResultFormatter._echo_truncated_content(content, "        Content: ")

                    else:
                        # Unknown part type - display as JSON
                        typer.echo(f"        Data: {part}")

    @staticmethod
    def format_structured(result: MemberAgentResult, execution_time_ms: int, verbose: bool = False) -> None:
        """Format result in structured text format with colors and sections.

        Args:
            result: The Member Agent result to format
            execution_time_ms: Total execution time in milliseconds
            verbose: Whether to include verbose details
        """
        # Status indicator with color
        status_colors = {"success": typer.colors.GREEN, "warning": typer.colors.YELLOW, "error": typer.colors.RED}
        status_color = status_colors.get(result.status, typer.colors.WHITE)

        # Header section
        typer.secho("=" * 60, fg=typer.colors.BLUE)
        typer.secho("MEMBER AGENT EXECUTION RESULT", fg=typer.colors.BLUE, bold=True)
        typer.secho("=" * 60, fg=typer.colors.BLUE)
        typer.echo()

        # Status and basic info
        typer.echo("Status: ", nl=False)
        typer.secho(result.status.upper(), fg=status_color, bold=True)

        typer.echo(f"Agent: {result.agent_name} ({result.agent_type})")
        typer.echo(f"Execution Time: {execution_time_ms}ms")
        typer.echo(f"Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        if result.retry_count and result.retry_count > 0:
            typer.secho(f"Retries: {result.retry_count}", fg=typer.colors.YELLOW)

        typer.echo()

        # Main content
        typer.secho("Response:", fg=typer.colors.CYAN, bold=True)
        typer.secho("-" * 40, fg=typer.colors.CYAN)

        if result.content:
            # Format content with proper wrapping
            typer.echo(result.content)
        else:
            typer.secho("(No content)", fg=typer.colors.BRIGHT_BLACK, italic=True)

        # Warnings
        if result.warning_message:
            typer.echo()
            typer.secho("⚠️  Warning:", fg=typer.colors.YELLOW, bold=True)
            typer.secho(result.warning_message, fg=typer.colors.YELLOW)

        # Error details
        if result.status == "error" and result.error_message:
            typer.echo()
            typer.secho("❌ Error Details:", fg=typer.colors.RED, bold=True)
            typer.secho(result.error_message, fg=typer.colors.RED)
            if result.error_code:
                typer.echo(f"Error Code: {result.error_code}")

        # Verbose details
        if verbose:
            typer.echo()
            typer.secho("Execution Details:", fg=typer.colors.MAGENTA, bold=True)
            typer.secho("-" * 40, fg=typer.colors.MAGENTA)

            # Model information
            if result.metadata:
                model_id = result.metadata.get("model_id", "unknown")
                temperature = result.metadata.get("temperature", "unknown")
                max_tokens = result.metadata.get("max_tokens", "unknown")

                typer.echo(f"  Model: {model_id}")
                typer.echo(f"  Temperature: {temperature}")
                typer.echo(f"  Max Tokens: {max_tokens}")

            # Usage information
            if result.usage_info:
                typer.echo("  Usage:")
                for key, value in result.usage_info.items():
                    if value is not None:
                        typer.echo(f"    {key}: {value}")

            # Additional metadata
            if result.metadata and len(result.metadata) > 3:  # More than basic model info
                typer.echo("  Additional Metadata:")
                for key, value in result.metadata.items():
                    if key not in ["model_id", "temperature", "max_tokens"]:
                        typer.echo(f"    {key}: {value}")

            # Message history (all_messages)
            if result.all_messages:
                typer.echo()
                typer.secho("Message History:", fg=typer.colors.CYAN, bold=True)
                typer.secho("-" * 40, fg=typer.colors.CYAN)
                ResultFormatter._format_message_history(result.all_messages)

        typer.echo()
        typer.secho("=" * 60, fg=typer.colors.BLUE)

    @staticmethod
    def format_json(result: MemberAgentResult, execution_time_ms: int, verbose: bool = False) -> None:
        """Format result as JSON.

        Args:
            result: The Member Agent result to format
            execution_time_ms: Total execution time in milliseconds
            verbose: Not used for JSON format (all_messages always included)
        """
        output = {
            "status": result.status,
            "agent_name": result.agent_name,
            "agent_type": result.agent_type,
            "content": result.content,
            "execution_time_ms": execution_time_ms,
            "timestamp": result.timestamp.isoformat(),
        }

        # Add optional fields if present
        if result.warning_message:
            output["warning_message"] = result.warning_message

        if result.error_message:
            output["error_message"] = result.error_message

        if result.error_code:
            output["error_code"] = result.error_code

        if result.retry_count and result.retry_count > 0:
            output["retry_count"] = result.retry_count

        if result.max_retries_exceeded:
            output["max_retries_exceeded"] = result.max_retries_exceeded

        if result.usage_info:
            output["usage_info"] = result.usage_info

        if result.metadata:
            output["metadata"] = result.metadata

        # Include all_messages if present (always include for JSON format)
        if result.all_messages:
            output["all_messages"] = result.all_messages

        typer.echo(json.dumps(output, indent=2, ensure_ascii=False, default=_json_encoder))

    @staticmethod
    def format_text(result: MemberAgentResult, execution_time_ms: int, verbose: bool = False) -> None:
        """Format result as plain text (content only).

        Args:
            result: The Member Agent result to format
            execution_time_ms: Total execution time in milliseconds (ignored for text format)
            verbose: Whether to include status info (ignored for text format)
        """
        if result.content:
            typer.echo(result.content)
        elif result.error_message:
            typer.echo(f"Error: {result.error_message}")
        else:
            typer.echo("(No content)")

    @staticmethod
    def format_csv(results: list[MemberAgentResult], execution_times: list[int]) -> None:
        """Format multiple results as CSV for batch processing.

        Args:
            results: List of Member Agent results
            execution_times: List of execution times corresponding to results
        """
        # CSV Header
        typer.echo("timestamp,agent_name,agent_type,status,execution_time_ms,content_length,error_code")

        for result, exec_time in zip(results, execution_times):
            # Escape content for CSV
            content_length = len(result.content) if result.content else 0
            error_code = result.error_code or ""

            typer.echo(
                f"{result.timestamp.isoformat()},{result.agent_name},{result.agent_type},"
                f"{result.status.value},{exec_time},{content_length},{error_code}"
            )

    @staticmethod
    def get_formatter(format_name: str) -> Callable[..., None]:
        """Get formatter function by name.

        Args:
            format_name: Name of the format ('structured', 'json', 'text', 'csv')

        Returns:
            Formatter function

        Raises:
            ValueError: If format name is not recognized
        """
        formatters: dict[str, Callable[..., None]] = {
            "structured": ResultFormatter.format_structured,
            "json": ResultFormatter.format_json,
            "text": ResultFormatter.format_text,
            "csv": ResultFormatter.format_csv,
        }

        if format_name not in formatters:
            available = ", ".join(formatters.keys())
            raise ValueError(f"Unknown format '{format_name}'. Available formats: {available}")

        return formatters[format_name]


class ProgressFormatter:
    """Formatter for showing progress during long-running operations."""

    @staticmethod
    def show_spinner(message: str = "Processing") -> None:
        """Show a simple spinner for operations in progress.

        Args:
            message: Message to display with spinner
        """
        # Simple implementation - in a real scenario you'd use a proper spinner library
        typer.echo(f"{message}...", nl=False)

    @staticmethod
    def show_progress_bar(current: int, total: int, description: str = "Progress") -> None:
        """Show a progress bar for batch operations.

        Args:
            current: Current progress value
            total: Total value for completion
            description: Description of the operation
        """
        if total == 0:
            percentage = 100
        else:
            percentage = int((current / total) * 100)

        bar_length = 40
        filled_length = int((bar_length * current) // total) if total > 0 else bar_length

        bar = "█" * filled_length + "-" * (bar_length - filled_length)
        typer.echo(f"\r{description}: |{bar}| {percentage}% ({current}/{total})", nl=False)

        if current >= total:
            typer.echo()  # New line when complete
