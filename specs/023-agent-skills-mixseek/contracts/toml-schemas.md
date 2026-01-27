# Contract: TOML Configuration Schemas

**Feature**: 023-agent-skills-mixseek
**Date**: 2026-01-21
**Source**: `src/mixseek/config/schema.py`

## 概要

MixSeek Agent Skillsが生成するTOML設定ファイルのスキーマ定義。各スキルはこのスキーマに準拠した設定ファイルを生成する。

## 1. Team Configuration (team.toml)

### Schema

```toml
[team]
team_id = "string"              # Required: Unique identifier
team_name = "string"            # Required: Display name
max_concurrent_members = 15     # Optional: 1-50, default 15

[team.leader]
system_instruction = "string"   # Required: Leader instructions
model = "provider:model-name"   # Required: e.g., "google-gla:gemini-2.5-pro"
temperature = 0.7               # Optional: 0.0-2.0
max_tokens = 2000               # Optional: positive integer
timeout_seconds = 300           # Optional: default 300
max_retries = 3                 # Optional: default 3
stop_sequences = ["END"]        # Optional: list of strings
top_p = 0.9                     # Optional: 0.0-1.0
seed = 42                       # Optional: integer

[[team.members]]
agent_name = "string"           # Required: unique within team
agent_type = "plain"            # Required: plain|web_search|code_execution|web_fetch|custom
tool_name = "string"            # Optional: default "delegate_to_{agent_name}"
tool_description = "string"     # Required: description for LLM
model = "provider:model-name"   # Required
system_instruction = "string"   # Required
temperature = 0.2               # Optional
max_tokens = 2048               # Optional
timeout_seconds = 30            # Optional
max_retries = 3                 # Optional

# For reference-style member definition
[[team.members]]
config = "configs/agents/member.toml"  # Path to external config
tool_name = "delegate_to_member"       # Optional override
tool_description = "string"            # Required if tool_name specified
```

### Field Constraints

| Field | Type | Constraint |
|-------|------|------------|
| `team.team_id` | string | Non-empty, unique |
| `team.team_name` | string | Non-empty |
| `team.max_concurrent_members` | integer | 1-50 |
| `team.leader.model` | string | Format: `provider:model-name` |
| `team.leader.temperature` | float | 0.0-2.0 |
| `team.members[].agent_type` | enum | plain, web_search, code_execution, web_fetch, custom |

### Validation Rules

```python
# Member count validation
assert len(team.members) <= team.max_concurrent_members

# Unique agent names
agent_names = [m.agent_name for m in team.members]
assert len(agent_names) == len(set(agent_names))

# Unique tool names
tool_names = [m.tool_name for m in team.members]
assert len(tool_names) == len(set(tool_names))
```

## 2. Orchestrator Configuration (orchestrator.toml)

### Schema

```toml
[orchestrator]
timeout_per_team_seconds = 600          # Optional: 10-3600, default 300
max_rounds = 5                          # Optional: 1-10, default 5
min_rounds = 2                          # Optional: >=1, default 2
submission_timeout_seconds = 300        # Optional: default 300
judgment_timeout_seconds = 60           # Optional: default 60

[[orchestrator.teams]]
config = "configs/agents/team-*.toml"   # Required: path to team config
```

### Field Constraints

| Field | Type | Constraint |
|-------|------|------------|
| `timeout_per_team_seconds` | integer | 10-3600 |
| `max_rounds` | integer | 1-10 |
| `min_rounds` | integer | >=1 |
| `teams[].config` | string | Valid path within workspace |

### Validation Rules

```python
# Round configuration validation
assert orchestrator.min_rounds <= orchestrator.max_rounds

# At least one team required
assert len(orchestrator.teams) >= 1

# Team config files must exist
for team in orchestrator.teams:
    assert os.path.exists(workspace / team.config)
```

## 3. Evaluator Configuration (evaluator.toml)

### Schema

```toml
default_model = "provider:model-name"   # Required
temperature = 0.0                       # Optional: 0.0-2.0
max_tokens = 2000                       # Optional
max_retries = 3                         # Optional
timeout_seconds = 300                   # Optional
stop_sequences = ["END"]                # Optional
top_p = 0.9                             # Optional
seed = 42                               # Optional

[[metrics]]
name = "ClarityCoherence"               # Required: metric class name
weight = 0.334                          # Optional: 0.0-1.0
model = "provider:model-name"           # Optional: override default
system_instruction = "string"           # Optional: custom instruction
temperature = 0.0                       # Optional: metric-specific
max_tokens = 1000                       # Optional
max_retries = 5                         # Optional
timeout_seconds = 120                   # Optional

[[metrics]]
name = "Coverage"
weight = 0.333

[[metrics]]
name = "Relevance"
weight = 0.333
```

### Standard Metrics

| Name | Description |
|------|-------------|
| `ClarityCoherence` | 回答の明確性と一貫性を評価 |
| `Coverage` | 質問に対するカバレッジを評価 |
| `Relevance` | 回答の関連性を評価 |

### Validation Rules

```python
# Weight validation
weights = [m.weight for m in metrics if m.weight is not None]

if len(weights) > 0:
    # All or none must have weights
    assert len(weights) == len(metrics), "All metrics must have weights if any specified"

    # Weights must sum to 1.0 (±0.001)
    total = sum(weights)
    assert 0.999 <= total <= 1.001, f"Weights must sum to 1.0, got {total}"

# If no weights specified, equal weights applied automatically
if len(weights) == 0:
    equal_weight = 1.0 / len(metrics)
    for m in metrics:
        m.weight = equal_weight
```

## 4. Judgment Configuration (judgment.toml)

### Schema

```toml
model = "provider:model-name"           # Required
temperature = 0.0                       # Optional: default 0.0 (deterministic)
max_tokens = 1000                       # Optional
max_retries = 3                         # Optional
timeout_seconds = 60                    # Optional: default 60
stop_sequences = ["END"]                # Optional
top_p = 0.9                             # Optional
seed = 42                               # Optional

# Optional: custom system instruction
# system_instruction = """
# Custom judgment instruction...
# """
```

### Field Constraints

| Field | Type | Constraint |
|-------|------|------------|
| `model` | string | Format: `provider:model-name` |
| `temperature` | float | 0.0-2.0, default 0.0 |
| `timeout_seconds` | integer | >0, default 60 |

## Model Format Contract

### Format

```
provider:model-name
```

### Valid Providers

| Provider | Internal ID | Example Models |
|----------|-------------|----------------|
| Google | `google-gla` | gemini-2.5-pro, gemini-2.5-flash |
| Anthropic | `anthropic` | claude-sonnet-4-5-20250929, claude-opus-4-1 |
| OpenAI | `openai` | gpt-5, gpt-4o, o3-mini |
| Grok | `grok` | grok-4-fast |

### Validation

```python
def validate_model_format(model: str) -> bool:
    if ":" not in model:
        return False
    provider, model_name = model.split(":", 1)
    return provider != "" and model_name != ""
```

## Default Values

### Team Settings

| Field | Default |
|-------|---------|
| Leader model | `google-gla:gemini-2.5-pro` |
| Member model | `google-gla:gemini-2.5-flash` |
| max_concurrent_members | 15 |
| timeout_seconds | 300 |
| max_retries | 3 |

### Orchestrator Settings

| Field | Default |
|-------|---------|
| timeout_per_team_seconds | 300 |
| max_rounds | 5 |
| min_rounds | 2 |
| submission_timeout_seconds | 300 |
| judgment_timeout_seconds | 60 |

### Evaluator Settings

| Field | Default |
|-------|---------|
| temperature | 0.0 |
| max_retries | 3 |
| timeout_seconds | 300 |

### Judgment Settings

| Field | Default |
|-------|---------|
| temperature | 0.0 |
| timeout_seconds | 60 |
| max_retries | 3 |
