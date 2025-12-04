"""Web Search Member Agent implementation.

This module implements the Web Search Member Agent, which provides research
and fact-checking capabilities through web search tools.

Supports multiple providers:
- Anthropic: Uses pydantic-ai's WebSearchTool
- OpenAI: Uses pydantic-ai's WebSearchTool
- Grok (xAI): Uses native OpenAI-compatible web_search tool via openai_builtin_tools
  (Grok API doesn't support WebSearchTool's search_context_size parameter)
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.core.auth import AuthenticationError, create_authenticated_model
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult, WebSearchToolConfig


@dataclass
class WebSearchAgentDeps:
    """Dependencies for Web Search Member Agent."""

    config: MemberAgentConfig
    web_search_config: WebSearchToolConfig | None = None


class WebSearchMemberAgent(BaseMemberAgent):
    """Web Search Member Agent for research and fact-checking with web search capabilities."""

    def __init__(self, config: MemberAgentConfig) -> None:
        """Initialize Web Search Member Agent.

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

        # Build agent arguments dynamically to reduce code duplication
        # Common args for all providers
        agent_args: dict[str, Any] = {
            "model": model,
            "deps_type": WebSearchAgentDeps,
            "output_type": str,
            "instructions": config.system_instruction,
            "retries": config.max_retries,
        }

        # Determine web search tool based on provider
        # Grok (xAI) uses native OpenAI-compatible web_search tool
        # Other providers use pydantic-ai's WebSearchTool
        is_grok = config.model.startswith("grok-responses:")

        if is_grok:
            # Grok: Use native web_search tool via openai_builtin_tools
            # Grok API doesn't support WebSearchTool's search_context_size parameter
            # xAI docs: https://docs.x.ai/docs/guides/tools/search-tools
            grok_model_settings: OpenAIResponsesModelSettings = {
                "openai_builtin_tools": [{"type": "web_search"}],
            }
            # Merge with base model settings if any (ModelSettings is TypedDict)
            if model_settings:
                if "max_tokens" in model_settings:
                    grok_model_settings["max_tokens"] = model_settings["max_tokens"]
                if "temperature" in model_settings:
                    grok_model_settings["temperature"] = model_settings["temperature"]
            agent_args["model_settings"] = grok_model_settings
        else:
            # Other providers: Use pydantic-ai's WebSearchTool
            agent_args["builtin_tools"] = [WebSearchTool()]
            agent_args["model_settings"] = model_settings

        # Add system_prompt if configured (system_instructionとsystem_promptを併用可能)
        if config.system_prompt is not None:
            agent_args["system_prompt"] = config.system_prompt

        # Create Pydantic AI agent with dynamic arguments
        self._agent = Agent(**agent_args)

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task with web search enabled agent.

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
            web_search_config = None
            if self.config.tool_settings and self.config.tool_settings.web_search:
                web_search_config = self.config.tool_settings.web_search

            deps = WebSearchAgentDeps(config=self.config, web_search_config=web_search_config)

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
                "capabilities": ["web_search"],
            }
            if context:
                metadata["context"] = context
            if web_search_config:
                metadata["search_config"] = {
                    "max_results": web_search_config.max_results,
                    "timeout": web_search_config.timeout,
                }

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
