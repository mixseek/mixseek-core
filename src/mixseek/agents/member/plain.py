"""Plain Member Agent implementation.

This module implements the Plain Member Agent, which provides general reasoning
and analysis capabilities without external tools.
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.core.auth import AuthenticationError, create_authenticated_model
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult


@dataclass
class PlainAgentDeps:
    """Dependencies for Plain Member Agent."""

    config: MemberAgentConfig


class PlainMemberAgent(BaseMemberAgent):
    """Plain Member Agent for general reasoning without external tools."""

    def __init__(self, config: MemberAgentConfig):
        """Initialize Plain Member Agent.

        Args:
            config: Validated agent configuration
        """
        super().__init__(config)

        # Article 9 compliant authentication - NO implicit fallbacks
        try:
            model = create_authenticated_model(config.model)
        except AuthenticationError as e:
            # Article 9: Explicit error propagation, no silent fallbacks
            raise ValueError(f"Authentication failed: {e}") from e

        # Create ModelSettings from config
        model_settings = self._create_model_settings()

        # Create Pydantic AI agent (system_instructionとsystem_promptを併用可能)
        if config.system_prompt is not None:
            self._agent = Agent(
                model=model,
                deps_type=PlainAgentDeps,
                output_type=str,
                instructions=config.system_instruction,
                system_prompt=config.system_prompt,
                model_settings=model_settings,
                retries=config.max_retries,
            )
        else:
            self._agent = Agent(
                model=model,
                deps_type=PlainAgentDeps,
                output_type=str,
                instructions=config.system_instruction,
                model_settings=model_settings,
                retries=config.max_retries,
            )

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task with plain reasoning agent.

        Args:
            task: User task or prompt to execute
            context: Optional context information
            **kwargs: Additional execution parameters

        Returns:
            MemberAgentResult with execution outcome
        """
        start_time = time.time()

        # Log execution start
        execution_id = self.logger.log_execution_start(
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            task=task,
            model_id=self.config.model,
            context=context,
            **kwargs,
        )

        # Validate input
        if not task.strip():
            return MemberAgentResult.error(
                error_message="Task cannot be empty or contain only whitespace",
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                error_code="EMPTY_TASK",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Create dependencies
            deps = PlainAgentDeps(config=self.config)

            # Execute with Pydantic AI agent
            result = await self._agent.run(task, deps=deps, **kwargs)

            # Capture complete message history (FR-016)
            all_messages = result.all_messages()

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Extract usage information if available
            usage_info = {}
            if hasattr(result, "usage"):
                usage = result.usage()
                usage_info = {
                    "total_tokens": getattr(usage, "total_tokens", None),
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "requests": getattr(usage, "requests", None),
                }

            # Build metadata
            metadata: dict[str, Any] = {
                "model_id": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            if context:
                metadata["context"] = context

            result_obj = MemberAgentResult.success(
                content=str(result.output),
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                execution_time_ms=execution_time_ms,
                usage_info=usage_info if usage_info else None,
                metadata=metadata,
                all_messages=all_messages,
            )

            # Log completion
            self.logger.log_execution_complete(execution_id=execution_id, result=result_obj, usage_info=usage_info)

            return result_obj

        except Exception as e:
            # Handle IncompleteToolCall explicitly (token limit reached during tool call generation)
            # Reference: Pydantic AI v1.3.0 - https://github.com/pydantic/pydantic-ai/releases
            from pydantic_ai import IncompleteToolCall

            if isinstance(e, IncompleteToolCall):
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Log error
                self.logger.log_error(
                    execution_id=execution_id,
                    error=e,
                    context={"task": task, "kwargs": kwargs, "error_type": "IncompleteToolCall"},
                )

                result_obj = MemberAgentResult.error(
                    error_message=f"Tool call generation incomplete due to token limit: {e}",
                    agent_name=self.agent_name,
                    agent_type=self.agent_type,
                    error_code="TOKEN_LIMIT_EXCEEDED",
                    execution_time_ms=execution_time_ms,
                )

                # Log completion for error case
                self.logger.log_execution_complete(execution_id=execution_id, result=result_obj)

                return result_obj

            # Handle all other errors
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log error
            self.logger.log_error(execution_id=execution_id, error=e, context={"task": task, "kwargs": kwargs})

            result_obj = MemberAgentResult.error(
                error_message=str(e),
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                error_code="EXECUTION_ERROR",
                execution_time_ms=execution_time_ms,
            )

            # Log completion for error case
            self.logger.log_execution_complete(execution_id=execution_id, result=result_obj)

            return result_obj
