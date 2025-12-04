"""Google ADK Research Agent sample for MixSeek-Core.

This module provides a sample custom Member Agent implementation using Google ADK
(Agent Development Kit) to demonstrate how to wrap external AI frameworks within
the MixSeek-Core BaseMemberAgent interface.

Example:
    >>> from examples.custom_agents.adk_research import ADKResearchAgent, ADKAgentConfig
    >>> config = MemberAgentConfig(...)  # Load from TOML
    >>> agent = ADKResearchAgent(config)
    >>> result = await agent.execute("What are the latest AI trends?")

Note:
    Requires google-adk >= 1.19.0 and a valid GOOGLE_API_KEY environment variable.
"""

from examples.custom_agents.adk_research.models import (
    ADKAgentConfig,
    ResearchReport,
    SearchResult,
)

__all__ = [
    "ADKAgentConfig",
    "SearchResult",
    "ResearchReport",
]

# ADKResearchAgent requires google-adk which may not be installed
try:
    from examples.custom_agents.adk_research.agent import ADKResearchAgent  # noqa: F401

    __all__.append("ADKResearchAgent")
except ImportError:
    # google-adk not installed, ADKResearchAgent will not be available
    pass
