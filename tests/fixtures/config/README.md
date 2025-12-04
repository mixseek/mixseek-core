# Configuration Test Fixtures

Sample TOML configuration files for testing the Configuration Manager feature (051-configuration).

## Files Overview

### config-minimal.toml
**Purpose**: Minimal required settings only
**Use Case**: Testing basic initialization with only required fields
**Contains**:
- OrchestratorSettings with workspace_path only
- All other settings use defaults

### config-complete.toml
**Purpose**: All settings explicitly configured
**Use Case**: Testing complete configuration coverage
**Contains**:
- OrchestratorSettings with all fields
- LeaderAgentSettings with all fields
- MemberAgentSettings with all fields
- EvaluatorSettings with all fields

### config-dev.toml
**Purpose**: Development environment configuration
**Use Case**: Local development and testing
**Contains**:
- Conservative timeouts for dev environment
- Standard models and settings
- Small concurrency limits
- Examples: timeout=300s, max_teams=4, num_rounds=3

### config-prod.toml
**Purpose**: Production environment configuration
**Use Case**: Production deployment validation
**Contains**:
- High performance settings
- Premium models (GPT-4 Turbo, Claude Opus)
- Large concurrency limits
- Examples: timeout=1800s, max_teams=16, num_rounds=10

### config-partial.toml
**Purpose**: Mixed explicit and default values
**Use Case**: Testing default value fallback behavior
**Contains**:
- Some fields explicitly set
- Some fields commented out to use defaults
- Tests priority chain: TOML > defaults

### config-custom.toml
**Purpose**: Non-standard values for edge case testing
**Use Case**: Testing custom values and constraints
**Contains**:
- Non-standard timeout values (100s, 60s)
- Custom model names
- Extreme temperature values (0.95)
- Minimum concurrency (1)

## Usage in Tests

### Example: Load config-dev.toml
```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import OrchestratorSettings

config_path = Path("tests/fixtures/config/config-dev.toml")
manager = ConfigurationManager(workspace=config_path.parent)
settings = manager.load_settings(OrchestratorSettings)

assert settings.timeout_per_team_seconds == 300
assert settings.max_concurrent_teams == 4
```

### Example: Test with environment override
```python
import os
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import OrchestratorSettings

# Use config-prod.toml as base
os.environ["MIXSEEK_CONFIG_FILE"] = str(Path("tests/fixtures/config/config-prod.toml"))

# Override with environment variable
os.environ["MIXSEEK_TIMEOUT_PER_TEAM_SECONDS"] = "900"

manager = ConfigurationManager()
settings = manager.load_settings(OrchestratorSettings)

# ENV value wins over TOML
assert settings.timeout_per_team_seconds == 900
```

## Adding New Fixtures

When adding new test fixtures:

1. **Name**: Follow pattern `config-<scenario>.toml`
2. **Documentation**: Add entry to this README with:
   - Purpose
   - Use case
   - Key values and characteristics
3. **Comments**: Include comments explaining non-obvious values
4. **Consistency**: Ensure values are realistic and testable

## Article 9 Compliance

These fixtures are designed to test Article 9 (Data Accuracy Mandate):
- All values are explicitly set (no implicit defaults in fixtures)
- Each file represents a clear scenario (dev, prod, minimal, partial)
- Fixtures enable testing of proper error handling for missing values
- Fixtures support tracing and source identification

## Related Documentation

- `/specs/051-configuration/quickstart.md` - Usage examples
- `/specs/051-configuration/spec.md` - Full specification
- `/tests/integration/config/test_toml_loading.py` - TOML loading tests
