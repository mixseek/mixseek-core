"""Bundled member agent configuration loader.

Provides a loader class for working with bundled member agent configurations
that ship with mixseek-core package.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from mixseek.config.schema import MemberAgentSettings


class BundledMemberAgentError(Exception):
    """Raised when bundled member agent operation fails."""

    pass


class BundledMemberAgentLoader:
    """Loader for bundled member agent configurations.

    This loader manages the three bundled member agents (plain, web-search, code-exec)
    that ship with mixseek-core package.

    Args:
        workspace: Workspace path (optional, used by ConfigurationManager)

    Example:
        >>> loader = BundledMemberAgentLoader(workspace=Path("/workspace"))
        >>> settings = loader.load("plain")
        >>> print(settings.agent_name)
        'plain'
    """

    AVAILABLE_AGENTS: set[str] = {"plain", "web-search", "code-exec"}

    def __init__(self, workspace: Path | None = None) -> None:
        """Initialize BundledMemberAgentLoader.

        Args:
            workspace: Workspace path (optional, used by ConfigurationManager)
        """
        self.workspace = workspace

    def get_agent_path(self, agent_name: Literal["plain", "web-search", "code-exec"]) -> Path:
        """Get path to bundled member agent TOML file.

        Args:
            agent_name: Name of bundled member agent

        Returns:
            Path to member agent configuration file

        Raises:
            BundledMemberAgentError: If member agent not found

        Note:
            Uses __file__ attribute for reliable path resolution across different installation methods.

        Example:
            >>> loader = BundledMemberAgentLoader()
            >>> path = loader.get_agent_path("plain")
            >>> print(path)
            /path/to/mixseek/config/agents/plain.toml
        """
        if agent_name not in self.AVAILABLE_AGENTS:
            available = ", ".join(sorted(self.AVAILABLE_AGENTS))
            raise BundledMemberAgentError(f"Unknown member agent '{agent_name}'. Available agents: {available}")

        try:
            # Use __file__ for reliable path resolution (works for all installation methods)
            import mixseek.config.agents

            agents_dir = Path(mixseek.config.agents.__file__).parent
            agent_path = agents_dir / f"{agent_name}.toml"

            # Verify the file exists
            if not agent_path.exists():
                raise FileNotFoundError(f"Bundled member agent file not found: {agent_path}")

            return agent_path

        except FileNotFoundError as e:
            raise BundledMemberAgentError(f"Bundled member agent '{agent_name}' configuration not found") from e
        except Exception as e:
            raise BundledMemberAgentError(f"Failed to get path for bundled member agent '{agent_name}': {e}") from e

    def load(self, agent_name: Literal["plain", "web-search", "code-exec"]) -> "MemberAgentSettings":
        """Load bundled member agent configuration using ConfigurationManager.

        Args:
            agent_name: Name of bundled member agent

        Returns:
            MemberAgentSettings instance

        Raises:
            BundledMemberAgentError: If member agent not found or loading fails

        Note:
            Article 10 (DRY): Uses ConfigurationManager for consistent loading logic.

        Example:
            >>> loader = BundledMemberAgentLoader(workspace=Path("/workspace"))
            >>> settings = loader.load("plain")
            >>> print(settings.agent_name)
            'plain'
        """
        from mixseek.config.manager import ConfigurationManager

        agent_path = self.get_agent_path(agent_name)

        try:
            config_manager = ConfigurationManager(workspace=self.workspace)
            return config_manager.load_member_settings(agent_path)
        except Exception as e:
            raise BundledMemberAgentError(f"Failed to load bundled member agent '{agent_name}': {e}") from e

    def list_available(self) -> list[str]:
        """List all available bundled member agents.

        Returns:
            Sorted list of member agent names

        Example:
            >>> loader = BundledMemberAgentLoader()
            >>> agents = loader.list_available()
            >>> print(agents)
            ['code-exec', 'plain', 'web-search']
        """
        return sorted(self.AVAILABLE_AGENTS)
