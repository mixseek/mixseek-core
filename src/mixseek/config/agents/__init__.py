"""Bundled agent configurations.

This package contains standard agent configuration TOML files that are
bundled with mixseek-core.

Standard Agents:
    - plain: Basic inference agent without tools
    - web-search: Agent with web search capabilities
    - code-exec: Agent with code execution capabilities (Anthropic Claude only)
"""

__all__ = ["plain", "web-search", "code-exec"]

# Package resource marker - この__init__.pyの存在により
# importlib.resources.files("mixseek.config.agents") が動作可能
