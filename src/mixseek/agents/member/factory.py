"""Member Agent Factory.

This module provides the factory pattern for creating Member Agent instances
based on their type and configuration.
"""

import asyncio
import logging

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.agents.member.code_execution import CodeExecutionMemberAgent
from mixseek.agents.member.dynamic_loader import load_agent_from_module, load_agent_from_path
from mixseek.agents.member.plain import PlainMemberAgent
from mixseek.agents.member.web_fetch import WebFetchMemberAgent
from mixseek.agents.member.web_search import WebSearchMemberAgent
from mixseek.framework.integration_hooks import emit_agent_created_event
from mixseek.models.member_agent import AgentType, MemberAgentConfig

logger = logging.getLogger(__name__)


class MemberAgentFactory:
    """Factory for creating Member Agent instances based on configuration."""

    _agent_classes: dict[str, type[BaseMemberAgent]] = {
        AgentType.PLAIN.value: PlainMemberAgent,
        AgentType.WEB_SEARCH.value: WebSearchMemberAgent,
        AgentType.WEB_FETCH.value: WebFetchMemberAgent,
        AgentType.CODE_EXECUTION.value: CodeExecutionMemberAgent,
    }

    @classmethod
    def register_agent(cls, agent_type: str, agent_class: type[BaseMemberAgent]) -> None:
        """Register an agent class for a specific agent type.

        Args:
            agent_type: The agent type to register (string identifier)
            agent_class: The agent class implementation
        """
        cls._agent_classes[agent_type] = agent_class

    @classmethod
    def _load_custom_agent(cls, config: MemberAgentConfig) -> BaseMemberAgent:
        """Load custom agent using dynamic loading (FR-021 priority handling).

        Priority:
            1. agent_module (recommended): Try module import first
            2. path (fallback): Try file path if module fails or not specified

        Args:
            config: Agent configuration with plugin metadata

        Returns:
            Instantiated custom agent

        Raises:
            ValueError: plugin metadata missing or neither method specified
            ModuleNotFoundError: agent_module loading failed
            FileNotFoundError: path loading failed
        """
        # Check plugin metadata exists
        if config.plugin is None:
            raise ValueError(
                "Error: Custom agent must have plugin configuration. "
                "Add [plugin] section to TOML config with either 'agent_module' or 'path'."
            )

        plugin = config.plugin

        # FR-021 Priority 1: agent_module (recommended)
        if plugin.agent_module is not None:
            try:
                agent = load_agent_from_module(
                    agent_module=plugin.agent_module,
                    agent_class=plugin.agent_class,
                    config=config,
                )
                # Success - return agent instance directly (no registration needed for dynamic loading)
                logger.info(f"Successfully loaded custom agent '{config.name}' from module '{plugin.agent_module}'")
                return agent
            except (ModuleNotFoundError, AttributeError, TypeError) as e:
                # FR-021: Fallback to path if available
                if plugin.path is None:
                    # No fallback available, re-raise original error
                    raise
                # Log fallback attempt
                logger.warning(
                    f"Failed to load custom agent from agent_module '{plugin.agent_module}', "
                    f"falling back to path '{plugin.path}': {e}"
                )

        # FR-021 Priority 2: path (fallback or primary if agent_module not specified)
        if plugin.path is not None:
            agent = load_agent_from_path(
                path=plugin.path,
                agent_class=plugin.agent_class,
                config=config,
            )
            # Success - return agent instance directly (no registration needed for dynamic loading)
            logger.info(f"Successfully loaded custom agent '{config.name}' from path '{plugin.path}'")
            return agent

        # Neither method specified
        raise ValueError(
            "Error: Custom agent must specify either 'agent_module' or 'path' "
            "in plugin configuration. Check TOML config."
        )

    @classmethod
    def create_agent(cls, config: MemberAgentConfig) -> BaseMemberAgent:
        """Create agent instance based on configuration.

        Args:
            config: Validated agent configuration

        Returns:
            Agent instance of appropriate type

        Raises:
            ValueError: If agent type is not supported or custom agent config invalid
            ModuleNotFoundError: If custom agent module not found
            FileNotFoundError: If custom agent file not found
        """
        # Custom agent: use dynamic loading (FR-020, FR-021, FR-022) or manual registration
        if config.type == "custom":
            # Plugin configuration provided: use dynamic loading (FR-020)
            if config.plugin is not None:
                agent = cls._load_custom_agent(config)
            else:
                # No plugin configuration: check for manually registered custom agent (backward compatibility)
                agent_class = cls._agent_classes.get(config.type)
                if not agent_class:
                    raise ValueError(
                        "Error: Custom agent must have plugin configuration. "
                        "Add [plugin] section to TOML config with either 'agent_module' or 'path'."
                    )
                # Use manually registered custom agent
                agent = agent_class(config)
        else:
            # Standard agent: dictionary lookup
            agent_class = cls._agent_classes.get(config.type)
            if not agent_class:
                available_types = list(cls._agent_classes.keys())
                raise ValueError(f"Unsupported agent type: {config.type}. Available types: {available_types}")

            # Create agent instance
            agent = agent_class(config)

        # Emit agent created event asynchronously (fire and forget)
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(emit_agent_created_event(config))
            # Add callback to handle any exceptions that occur during event emission
            task.add_done_callback(_handle_event_task_exception)
        except RuntimeError:
            # No running loop, log warning but allow agent creation to succeed
            logger.warning(
                f"Cannot emit agent created event: no running event loop. Agent: {config.name} ({config.type})"
            )

        return agent

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported agent types.

        Returns:
            List of supported agent types (string identifiers)
        """
        return list(cls._agent_classes.keys())


def _handle_event_task_exception(task: asyncio.Task[None]) -> None:
    """Handle exceptions from agent created event emission tasks.

    Args:
        task: The completed asyncio Task
    """
    try:
        task.result()
    except Exception as e:
        logger.warning(f"Failed to emit agent created event: {e}")
