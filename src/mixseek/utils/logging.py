"""Logging utilities for MixSeek."""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mixseek.config.constants import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL


def setup_logging(level: str = DEFAULT_LOG_LEVEL, format_string: str = DEFAULT_LOG_FORMAT) -> None:
    """
    Setup basic logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Log message format string
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
    )


class MemberAgentLogger:
    """Comprehensive logging for Member Agent operations per FR-011."""

    def __init__(self, log_level: str = "INFO", enable_file_logging: bool = True):
        """Initialize Member Agent Logger.

        Args:
            log_level: Logging level for the logger
            enable_file_logging: Whether to enable file-based logging
        """
        self.log_level = log_level
        self.logger = logging.getLogger("mixseek.member_agents")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Avoid duplicate handlers
        if not self.logger.handlers:
            self.setup_logging(enable_file_logging)

    def setup_logging(self, enable_file_logging: bool) -> None:
        """Setup structured logging with multiple outputs."""
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console handler: INFO level and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler: DEBUG level to MIXSEEK_WORKSPACE/logs/
        if enable_file_logging:
            # Article 9準拠: ConfigurationManager経由でworkspaceを取得
            try:
                from mixseek.utils.env import get_workspace_path

                workspace_path = get_workspace_path(cli_arg=None)
                log_dir = workspace_path / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)

                log_file = log_dir / f"member-agent-{datetime.now().strftime('%Y-%m-%d')}.log"

                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            except (OSError, PermissionError) as e:
                # 権限エラーは即座に発生させる（フォールバック禁止）
                raise PermissionError(
                    f"Cannot create log directory or file: {log_dir}\nError: {e}\nPlease check directory permissions."
                ) from e

    def log_execution_start(self, agent_name: str, agent_type: str, task: str, model_id: str, **kwargs: Any) -> str:
        """Log agent execution start, return execution_id.

        Args:
            agent_name: Name of the agent
            agent_type: Type of agent (plain, web_search, code_execution)
            task: Task description (truncated for logging)
            model_id: Model identifier
            **kwargs: Additional context

        Returns:
            Unique execution ID for tracking this execution
        """
        execution_id = str(uuid.uuid4())[:8]

        log_data = {
            "event": "execution_start",
            "execution_id": execution_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "task_preview": task[:100] + "..." if len(task) > 100 else task,
            "model_id": model_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_data.update(kwargs)

        json_data = json.dumps(log_data, default=str, ensure_ascii=False)
        self.logger.info(f"Execution started: {json_data}")
        return execution_id

    def log_execution_complete(
        self,
        execution_id: str,
        result: Any,  # MemberAgentResult type (avoiding circular import)
        usage_info: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> None:
        """Log execution completion with metrics.

        Args:
            execution_id: Execution ID from log_execution_start
            result: MemberAgentResult instance
            usage_info: Usage information from the result
            retry_count: Number of retries attempted
        """
        log_data = {
            "event": "execution_complete",
            "execution_id": execution_id,
            "status": result.status,
            "agent_name": result.agent_name,
            "agent_type": result.agent_type,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": retry_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if usage_info:
            log_data["usage"] = usage_info

        if result.error_message:
            log_data["error_message"] = result.error_message
            log_data["error_code"] = result.error_code

        # Log at different levels based on result status
        json_data = json.dumps(log_data, default=str, ensure_ascii=False)
        if result.status == "success":
            self.logger.info(f"Execution completed: {json_data}")
        elif result.status == "error":
            self.logger.error(f"Execution failed: {json_data}")
        else:
            self.logger.warning(f"Execution completed with warnings: {json_data}")

    def log_tool_invocation(
        self, execution_id: str, tool_name: str, parameters: dict[str, Any], execution_time_ms: int, status: str
    ) -> None:
        """Log tool usage details.

        Args:
            execution_id: Execution ID from log_execution_start
            tool_name: Name of the tool being invoked
            parameters: Tool parameters (sanitized)
            execution_time_ms: Tool execution time
            status: Tool execution status (success, error, etc.)
        """
        log_data = {
            "event": "tool_invocation",
            "execution_id": execution_id,
            "tool_name": tool_name,
            "parameters": self._sanitize_parameters(parameters),
            "execution_time_ms": execution_time_ms,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        json_data = json.dumps(log_data, default=str, ensure_ascii=False)
        if status == "success":
            self.logger.debug(f"Tool invoked: {json_data}")
        else:
            self.logger.warning(f"Tool invocation failed: {json_data}")

    def log_configuration_loaded(
        self, config_path: Path | None, agent_name: str, agent_type: str, model_id: str
    ) -> None:
        """Log configuration loading event.

        Args:
            config_path: Path to configuration file (if any)
            agent_name: Name of the agent
            agent_type: Type of agent
            model_id: Model identifier
        """
        log_data = {
            "event": "configuration_loaded",
            "config_path": str(config_path) if config_path else None,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "model_id": model_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        json_data = json.dumps(log_data, default=str, ensure_ascii=False)
        self.logger.debug(f"Configuration loaded: {json_data}")

    def log_error(self, execution_id: str, error: Exception, context: dict[str, Any] | None = None) -> None:
        """Log error with context.

        Args:
            execution_id: Execution ID from log_execution_start
            error: Exception that occurred
            context: Additional error context
        """
        log_data: dict[str, Any] = {
            "event": "error",
            "execution_id": execution_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if context:
            log_data["context"] = context

        json_data = json.dumps(log_data, default=str, ensure_ascii=False)
        self.logger.error(f"Error occurred: {json_data}")

    def _sanitize_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Sanitize parameters to avoid logging sensitive data.

        Args:
            parameters: Raw parameters dictionary

        Returns:
            Sanitized parameters dictionary
        """
        sanitized = {}

        for key, value in parameters.items():
            # Sanitize potential sensitive keys
            if any(sensitive in key.lower() for sensitive in ["key", "token", "password", "secret"]):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate long strings
                sanitized[key] = value[:100] + "..."
            else:
                sanitized[key] = value

        return sanitized
