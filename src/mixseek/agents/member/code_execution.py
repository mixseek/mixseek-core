"""Code Execution Member Agent implementation.

This module implements the Code Execution Member Agent, which provides data analysis,
calculations, and computational capabilities through code execution tools.
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, CodeExecutionTool

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.core.auth import AuthenticationError, create_authenticated_model
from mixseek.models.member_agent import CodeExecutionToolConfig, MemberAgentConfig, MemberAgentResult


@dataclass
class CodeExecutionAgentDeps:
    """Dependencies for Code Execution Member Agent."""

    config: MemberAgentConfig
    code_execution_config: CodeExecutionToolConfig | None = None


class CodeExecutionMemberAgent(BaseMemberAgent):
    """Code Execution Member Agent for data analysis, calculations, and computational tasks.

    IMPORTANT: Only Anthropic Claude models support actual code execution.
    Other providers (Google AI, Vertex AI, OpenAI) will raise an error at initialization.

    Reference:
        - spec.md:239 - Supported Provider: Anthropic Claude only
        - spec.md:366-369 - Clarifications (2025-10-21 approved)
        - findings/2025-10-21-code-execution-provider-compatibility.md
    """

    def __init__(self, config: MemberAgentConfig):
        """Initialize Code Execution Member Agent.

        Args:
            config: Validated agent configuration

        Raises:
            ValueError: If model is not an Anthropic Claude model
        """
        super().__init__(config)

        # Validate provider: Only Anthropic Claude supports code execution
        # Reference: spec.md:239, spec.md:366-369 (Clarifications)
        if not config.model.startswith("anthropic:"):
            raise ValueError(
                f"Code Execution Agent only supports Anthropic Claude models.\n"
                f"Current model: '{config.model}'\n\n"
                f"Supported providers for code execution:\n"
                f"  ✅ Anthropic Claude (e.g., 'anthropic:claude-sonnet-4-5-20250929')\n"
                f"  ❌ Google AI - Not supported (returns 400 INVALID_ARGUMENT)\n"
                f"  ❌ Vertex AI - Not supported (returns 400 INVALID_ARGUMENT)\n"
                f"  ❌ OpenAI - Not supported (CodeExecutionTool not available)\n\n"
                f"Please update your configuration to use an Anthropic Claude model.\n"
                f'Example: model = "anthropic:claude-sonnet-4-5-20250929"\n'
                f"Required environment variable: ANTHROPIC_API_KEY\n\n"
                f"For more details, see:\n"
                f"  - specs/009-member/spec.md:239\n"
                f"  - specs/009-member/findings/2025-10-21-code-execution-provider-compatibility.md"
            )

        # Article 9 compliant authentication - NO implicit fallbacks
        try:
            model = create_authenticated_model(config.model)
        except AuthenticationError as e:
            # Article 9: Explicit error propagation, no silent fallbacks
            raise ValueError(f"Authentication failed: {e}") from e

        # Create ModelSettings from config
        model_settings = self._create_model_settings()

        # Create Pydantic AI agent with CodeExecutionTool (system_instructionとsystem_promptを併用可能)
        if config.system_prompt is not None:
            self._agent = Agent(
                model=model,
                deps_type=CodeExecutionAgentDeps,
                output_type=str,
                instructions=config.system_instruction,
                system_prompt=config.system_prompt,
                builtin_tools=[CodeExecutionTool()],
                model_settings=model_settings,
                retries=config.max_retries,
            )
        else:
            self._agent = Agent(
                model=model,
                deps_type=CodeExecutionAgentDeps,
                output_type=str,
                instructions=config.system_instruction,
                builtin_tools=[CodeExecutionTool()],
                model_settings=model_settings,
                retries=config.max_retries,
            )

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute task with code execution enabled agent.

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
            code_execution_config = None
            if self.config.tool_settings and self.config.tool_settings.code_execution:
                code_execution_config = self.config.tool_settings.code_execution

            deps = CodeExecutionAgentDeps(config=self.config, code_execution_config=code_execution_config)

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
                "capabilities": ["code_execution"],
            }
            if context:
                metadata["context"] = context
            if code_execution_config:
                metadata["execution_config"] = {
                    "provider_controlled": code_execution_config.provider_controlled,
                    "expected_min_timeout": code_execution_config.expected_min_timeout_seconds,
                    "expected_network_access": code_execution_config.expected_network_access,
                    "expected_modules": code_execution_config.expected_available_modules,
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
