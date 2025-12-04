"""Dynamic loading utilities for custom Member Agents.

This module provides functions to dynamically load custom agent classes
from Python modules or file paths (FR-020, FR-021, FR-022).

Loading Methods:
    - agent_module (recommended): Load from pip-installable Python packages
    - path (alternative): Load from standalone Python files for development

Priority (FR-021):
    1. agent_module is tried first if specified
    2. path is used as fallback if agent_module fails or is not specified
"""

import hashlib
import importlib
import importlib.util
import logging
import sys
from pathlib import Path

from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig

logger = logging.getLogger(__name__)


def load_agent_from_module(
    agent_module: str,
    agent_class: str,
    config: MemberAgentConfig,
) -> BaseMemberAgent:
    """Load custom agent class from Python module path.

    This is the recommended method for production environments where the custom
    agent is distributed as a pip-installable package.

    Args:
        agent_module: Python module path (e.g., "my_package.agents.custom")
        agent_class: Agent class name (e.g., "MyCustomAgent")
        config: Agent configuration

    Returns:
        Instantiated custom agent

    Raises:
        ModuleNotFoundError: Module not found (FR-022: detailed error message)
        AttributeError: Class not found in module (FR-022)
        TypeError: Class doesn't inherit from BaseMemberAgent (FR-022)

    Examples:
        >>> config = MemberAgentConfig(...)
        >>> agent = load_agent_from_module(
        ...     agent_module="my_analytics.agents.data_analyst",
        ...     agent_class="DataAnalystAgent",
        ...     config=config
        ... )
    """
    # Attempt module import (FR-022: explicit error handling)
    try:
        module = importlib.import_module(agent_module)
    except ModuleNotFoundError as e:
        # FR-022: Detailed error message with installation hint
        error_msg = (
            f"Error: Failed to load custom agent from module '{agent_module}'. "
            f"ModuleNotFoundError: {e}. "
            f"Install package: pip install <package-name>"
        )
        raise ModuleNotFoundError(error_msg) from e

    # Attempt class retrieval
    try:
        cls: type[BaseMemberAgent] = getattr(module, agent_class)
    except AttributeError as e:
        # FR-022: Detailed error message with configuration hint
        error_msg = (
            f"Error: Custom agent class '{agent_class}' not found in module '{agent_module}'. "
            f"Check agent_class in TOML config."
        )
        raise AttributeError(error_msg) from e

    # Verify inheritance from BaseMemberAgent
    if not issubclass(cls, BaseMemberAgent):
        # FR-022: Detailed error message for type mismatch
        error_msg = f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        raise TypeError(error_msg)

    # Instantiate agent
    return cls(config)


def load_agent_from_path(
    path: str,
    agent_class: str,
    config: MemberAgentConfig,
) -> BaseMemberAgent:
    """Load custom agent class from file path.

    This is the alternative method for development/prototyping where the custom
    agent is in a standalone Python file.

    Args:
        path: File path (e.g., "/path/to/custom_agent.py")
        agent_class: Agent class name (e.g., "MyCustomAgent")
        config: Agent configuration

    Returns:
        Instantiated custom agent

    Raises:
        FileNotFoundError: File not found (FR-022: detailed error message)
        ImportError: Failed to create module spec (FR-022)
        AttributeError: Class not found in file (FR-022)
        TypeError: Class doesn't inherit from BaseMemberAgent (FR-022)

    Examples:
        >>> config = MemberAgentConfig(...)
        >>> agent = load_agent_from_path(
        ...     path="/home/user/agents/custom_agent.py",
        ...     agent_class="CustomAgent",
        ...     config=config
        ... )
    """
    # Verify file exists
    path_obj = Path(path)
    if not path_obj.exists():
        # FR-022: Detailed error message with file check hint
        error_msg = (
            f"Error: Failed to load custom agent from path '{path}'. "
            f"FileNotFoundError: File not found. "
            f"Check file path in TOML config."
        )
        raise FileNotFoundError(error_msg)

    # Generate unique module name to avoid collision when loading multiple agents
    # Uses SHA256 hash of absolute path for stability across executions
    path_hash = hashlib.sha256(str(path_obj.resolve()).encode()).hexdigest()[:16]
    module_name = f"custom_agent_{path_hash}"

    # Create module spec from file path
    spec = importlib.util.spec_from_file_location(module_name, path_obj)
    if spec is None or spec.loader is None:
        # FR-022: Detailed error for spec creation failure
        error_msg = f"Error: Failed to create module spec from path '{path}'."
        raise ImportError(error_msg)

    # Load module from spec
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # SECURITY WARNING: Executing Python code from file
    # This executes all module-level code in the specified file.
    # Only use files from trusted sources to avoid code injection vulnerabilities.
    # For production environments, prefer 'agent_module' method with pip-installed packages.
    spec.loader.exec_module(module)

    # Attempt class retrieval
    try:
        cls: type[BaseMemberAgent] = getattr(module, agent_class)
    except AttributeError as e:
        # FR-022: Detailed error message with configuration hint
        error_msg = (
            f"Error: Custom agent class '{agent_class}' not found in file '{path}'. Check agent_class in TOML config."
        )
        raise AttributeError(error_msg) from e

    # Verify inheritance from BaseMemberAgent
    if not issubclass(cls, BaseMemberAgent):
        # FR-022: Detailed error message for type mismatch
        error_msg = f"Error: Custom agent class '{agent_class}' must inherit from BaseMemberAgent."
        raise TypeError(error_msg)

    # Instantiate agent
    return cls(config)
