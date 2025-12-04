"""Web Fetch Member Agent implementation.

This module implements the Web Fetch Member Agent, which provides URL content
retrieval capabilities through Pydantic AI's WebFetchTool.

Supports multiple providers:
- Anthropic: Full support with configurable parameters (max_uses, domains, citations)
- Google: Basic support (parameters not configurable)
- OpenAI/Grok: NOT SUPPORTED (will raise error on initialization)
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, IncompleteToolCall, WebFetchTool

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.core.auth import AuthenticationError, create_authenticated_model
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult, WebFetchToolConfig


@dataclass
class WebFetchAgentDeps:
    """Dependencies for Web Fetch Member Agent."""

    config: MemberAgentConfig
    web_fetch_config: WebFetchToolConfig | None = None


class WebFetchMemberAgent(BaseMemberAgent):
    """Web Fetch Member Agent for retrieving URL content.

    This agent uses Pydantic AI's WebFetchTool to fetch and analyze content
    from specified URLs. It supports Anthropic and Google models only.
    """

    def __init__(self, config: MemberAgentConfig) -> None:
        """Initialize Web Fetch Member Agent.

        Args:
            config: Validated agent configuration

        Raises:
            ValueError: If model provider is not supported (OpenAI/Grok)
        """
        super().__init__(config)

        # Provider validation - only Anthropic and Google supported
        is_anthropic = config.model.startswith("anthropic:")
        is_google = config.model.startswith("google-gla:") or config.model.startswith("google-vertex:")

        if not (is_anthropic or is_google):
            raise ValueError(
                f"Web Fetch Agent only supports Anthropic and Google models. "
                f"Got: {config.model}. "
                f"Use 'anthropic:claude-sonnet-4-5-20250929' or 'google-gla:gemini-2.5-flash'."
            )

        # Article 9 compliant authentication - NO implicit fallbacks
        try:
            model = create_authenticated_model(config.model)
        except AuthenticationError as e:
            # Article 9: Explicit error propagation, no silent fallbacks
            raise ValueError(f"Authentication failed: {e}") from e

        # Create ModelSettings from config
        model_settings = self._create_model_settings()

        # Build agent arguments dynamically
        agent_args: dict[str, Any] = {
            "model": model,
            "deps_type": WebFetchAgentDeps,
            "output_type": str,
            "instructions": config.system_instruction,
            "retries": config.max_retries,
        }

        # Create WebFetchTool with appropriate parameters (DRY refactored)
        tool_kwargs: dict[str, Any] = {}
        if is_anthropic and config.tool_settings and config.tool_settings.web_fetch:
            # Anthropic: Apply configurable parameters
            wf_config = config.tool_settings.web_fetch
            if wf_config.max_uses is not None:
                tool_kwargs["max_uses"] = wf_config.max_uses
            if wf_config.allowed_domains is not None:
                tool_kwargs["allowed_domains"] = wf_config.allowed_domains
            if wf_config.blocked_domains is not None:
                tool_kwargs["blocked_domains"] = wf_config.blocked_domains
            if wf_config.enable_citations:
                tool_kwargs["enable_citations"] = wf_config.enable_citations
            if wf_config.max_content_tokens is not None:
                tool_kwargs["max_content_tokens"] = wf_config.max_content_tokens
        # Google or no config: tool_kwargs remains empty, using default WebFetchTool
        agent_args["builtin_tools"] = [WebFetchTool(**tool_kwargs)]

        agent_args["model_settings"] = model_settings

        # Add system_prompt if configured (system_instruction と system_prompt を併用可能)
        if config.system_prompt is not None:
            agent_args["system_prompt"] = config.system_prompt

        # Create Pydantic AI agent with dynamic arguments
        self._agent = Agent(**agent_args)

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task with web fetch enabled agent.

        Args:
            task: User task or prompt to execute (typically includes URL)
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
            web_fetch_config = None
            if self.config.tool_settings and self.config.tool_settings.web_fetch:
                web_fetch_config = self.config.tool_settings.web_fetch

            deps = WebFetchAgentDeps(config=self.config, web_fetch_config=web_fetch_config)

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
                "capabilities": ["web_fetch"],
            }
            if context:
                metadata["context"] = context
            if web_fetch_config:
                metadata["fetch_config"] = {
                    "max_uses": web_fetch_config.max_uses,
                    "enable_citations": web_fetch_config.enable_citations,
                    "max_content_tokens": web_fetch_config.max_content_tokens,
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
            # Refactored to reduce code duplication (PR #245 review feedback)
            if isinstance(e, IncompleteToolCall):
                error_message = f"Tool call generation incomplete due to token limit: {e}"
                error_code = "TOKEN_LIMIT_EXCEEDED"
                log_context: dict[str, Any] = {"task": task, "kwargs": kwargs, "error_type": "IncompleteToolCall"}
            else:
                error_message = str(e)
                error_code = "EXECUTION_ERROR"
                log_context = {"task": task, "kwargs": kwargs}

            execution_time_ms = int((time.time() - start_time) * 1000)
            self.logger.log_error(execution_id=execution_id, error=e, context=log_context)

            result_obj = MemberAgentResult.error(
                error_message=error_message,
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                error_code=error_code,
                execution_time_ms=execution_time_ms,
            )

            self.logger.log_execution_complete(execution_id=execution_id, result=result_obj)
            return result_obj
