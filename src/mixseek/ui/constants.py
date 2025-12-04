"""Constants for Mixseek UI."""

TOML_TEMPLATE = """# Mixseek Configuration File
# Created at: {timestamp}

# Member Agents
[[member_agents]]
agent_id = "example_member"
provider = "anthropic"
model = "claude-sonnet-4"
system_prompt = "You are a helpful assistant."
temperature = 0.7
max_tokens = 4096

# Leader Agents
[[leader_agents]]
agent_id = "example_leader"
provider = "google-adk"
model = "gemini-2.0-flash-exp"
system_prompt = "You are a team leader."
temperature = 0.5
max_tokens = 8192

# Orchestrations
[[orchestrations]]
orchestration_id = "example_orch"
leader_agent_id = "example_leader"
member_agent_ids = ["example_member"]
description = "Example orchestration configuration"
"""
