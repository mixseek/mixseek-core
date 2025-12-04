"""Leader Agent module.

Agent Delegation pattern implementation for MixSeek-Core.
Leader Agent dynamically selects appropriate Member Agents based on task analysis.

Components:
    - agent: Leader Agent creation (create_leader_agent)
    - models: Data models (MemberSubmission, MemberSubmissionsRecord)
    - config: TOML configuration (TeamConfig, load_team_config)
    - tools: Member Agent tool registration (register_member_tools)
    - dependencies: RunContext dependencies (TeamDependencies)

References:
    - Spec: specs/008-leader/spec.md
    - Plan: specs/008-leader/plan.md
"""

from mixseek.agents.leader.agent import create_leader_agent
from mixseek.agents.leader.config import (
    LeaderAgentConfig,
    TeamConfig,
    TeamMemberAgentConfig,
    load_team_config,
    team_settings_to_team_config,
)
from mixseek.agents.leader.dependencies import TeamDependencies
from mixseek.agents.leader.models import MemberSubmission, MemberSubmissionsRecord
from mixseek.agents.leader.tools import register_member_tools

__all__ = [
    "create_leader_agent",
    "LeaderAgentConfig",
    "TeamMemberAgentConfig",
    "TeamConfig",
    "load_team_config",
    "team_settings_to_team_config",
    "TeamDependencies",
    "MemberSubmission",
    "MemberSubmissionsRecord",
    "register_member_tools",
]
