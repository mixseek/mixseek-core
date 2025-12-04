# Member Agent DRY Principle Quick Reference

## What Already Exists (Reuse These)

### 1. Pydantic Model Patterns
**Location**: `/app/src/mixseek/models/config.py` (Lines 11-46)

Study this pattern and replicate for MemberAgentConfig:
- Field validators with `@field_validator`
- Model validators with `@model_validator(mode="after")`
- Factory methods: `create_default()`, `from_env()`
- Type hints with Literal types for enums

### 2. TOML Configuration
**Location**: `/app/src/mixseek/config/templates.py` (Lines 1-37)

Study this pattern for agent config generation:
- Manual TOML file writing with comments
- Uses Path.write_text() or file handle for generation
- Example config exists: `/app/workspace/configs/member_agent_config.toml`

### 3. CLI Command Pattern
**Location**: `/app/src/mixseek/cli/commands/init.py` (Full file)

Study this pattern for member agent CLI:
- typer.Option() for parameters
- Try/except with specific error handling
- Result models with print_result()
- Exit codes: 0=success, 1=error, 130=Ctrl+C

### 4. Result Models
**Location**: `/app/src/mixseek/models/result.py` (Lines 1-57)

Study InitResult pattern:
- success: bool field
- Factory methods: success_result(), error_result()
- print_result() for CLI output
- All fields fully typed

### 5. Exception Classes
**Location**: `/app/src/mixseek/exceptions.py` (Full file)

Pattern for error handling:
- Inherit from appropriate base (ValueError, PermissionError)
- Store context in self.attributes
- Provide helpful error messages

### 6. Logging Setup
**Location**: `/app/src/mixseek/utils/logging.py` (Full file)

Reuse pattern:
```python
logger = logging.getLogger(__name__)
# Then use logger.info(), logger.error(), etc.
```

### 7. Environment Variable Pattern
**Location**: `/app/src/mixseek/utils/env.py` (Full file)

Pattern to follow:
- Define constants in `/app/src/mixseek/config/constants.py`
- Create getter functions with priority: CLI > ENV > Error
- Raise specific exceptions on missing values

### 8. Test Patterns
**Location**: `/app/tests/` (Full test structure)

- Unit tests: `/app/tests/unit/`
- Integration tests: `/app/tests/integration/`
- Contract tests: `/app/tests/contract/`
- Use pytest with markers: `@pytest.mark.unit`, `@pytest.mark.integration`

---

## Files to Create/Modify

### Create New
1. `/app/src/mixseek/models/agent.py` - MemberAgentConfig model
2. `/app/src/mixseek/models/agent_result.py` - MemberAgentResult model
3. `/app/src/mixseek/cli/commands/test_member.py` - CLI command
4. `/app/src/mixseek/agents/` directory - Agent implementations
5. `/app/tests/unit/test_member_agent_config.py`
6. `/app/tests/integration/test_member_agent_integration.py`
7. `/app/tests/contract/test_member_agent_contract.py`

### Extend Existing
1. `/app/src/mixseek/exceptions.py` - Add agent-specific exceptions
2. `/app/src/mixseek/config/constants.py` - Add agent constants
3. `/app/src/mixseek/utils/env.py` - Add Google credential handling
4. `/app/src/mixseek/cli/main.py` - Register test-member command

---

## Checklist Before Implementation

- [ ] Read `/app/src/mixseek/models/config.py` (understand Pydantic patterns)
- [ ] Read `/app/src/mixseek/config/templates.py` (understand TOML pattern)
- [ ] Read `/app/src/mixseek/cli/commands/init.py` (understand CLI pattern)
- [ ] Read `/app/tests/unit/test_models.py` (understand test patterns)
- [ ] Check `/app/workspace/configs/member_agent_config.toml` (config reference)

---

## What's NEW (Don't Duplicate)

These are fresh areas - establish best practices:
1. Pydantic AI agent implementation
2. Google Gemini API integration
3. WebSearchTool integration
4. CodeExecutionTool integration
5. Agent result parsing and output
6. Tool registration patterns

---

## Key Constants to Add

In `/app/src/mixseek/config/constants.py`:

```python
# Member Agent configuration
MEMBER_AGENT_TOML_TEMPLATE: str = "member_agent_config.toml"
MEMBER_AGENT_DEFAULT_TIMEOUT: int = 120
MEMBER_AGENT_DEFAULT_RETRIES: int = 3

# Google credentials
GOOGLE_API_CREDENTIALS_ENV_VAR: str = "GOOGLE_APPLICATION_CREDENTIALS"
GOOGLE_GENAI_USE_VERTEXAI_ENV_VAR: str = "GOOGLE_GENAI_USE_VERTEXAI"
```

---

## Key Exceptions to Add

In `/app/src/mixseek/exceptions.py`:

```python
class MemberAgentConfigError(ValueError):
    """Raised when agent config is invalid"""
    pass

class MemberAgentExecutionError(Exception):
    """Raised when agent execution fails"""
    pass

class GoogleAPIError(Exception):
    """Raised when Google API call fails"""
    pass

class AgentTimeoutError(TimeoutError):
    """Raised when agent execution times out"""
    pass
```

---

## Pydantic Model Template

Follow this for MemberAgentConfig:

```python
from pydantic import BaseModel, field_validator, Field
from typing import Literal

class MemberAgentConfig(BaseModel):
    """Member Agent configuration from TOML"""
    
    agent_id: str
    name: str
    description: str = ""
    
    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("agent_id cannot be empty")
        return v
    
    @classmethod
    def from_toml_file(cls, path: Path) -> "MemberAgentConfig":
        """Load config from TOML file"""
        import tomllib  # Python 3.11+
        # Implementation here
        pass
```

---

## CLI Command Template

Follow this pattern:

```python
import typer
from mixseek.models.agent_result import MemberAgentResult

def test_member(
    prompt: str = typer.Argument(..., help="User prompt to process"),
    config: Path = typer.Option(..., "--config", "-c", help="Agent config file"),
) -> None:
    """Test Member Agent execution (development/test mode only)."""
    try:
        # Load config
        # Create agent
        # Execute
        result = MemberAgentResult.success_result(...)
        result.print_result()
    except Exception as e:
        handle_error(e)

def handle_error(error: Exception) -> None:
    typer.echo(f"Error: {error}", err=True)
    import sys
    sys.exit(1)
```

---

## DRY Compliance = SUCCESS

No duplications detected. All foundational patterns exist. Proceed with confidence.

