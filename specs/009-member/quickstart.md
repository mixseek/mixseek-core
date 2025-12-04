# Quickstart Guide: MixSeek-Core Member Agent バンドル

**Date**: 2025-10-21
**Phase**: 1 - Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing and using the MixSeek-Core Member Agent bundle. Follow this guide to get up and running quickly with the three bundled agent types.

---

## Prerequisites

### System Requirements
- Python 3.13.9 or higher
- uv package manager (recommended)
- Google API credentials (Gemini API key or Vertex AI service account)

### Dependencies
```bash
# Core dependencies (will be added to pyproject.toml)
pydantic-ai >= 0.0.8
google-generativeai >= 0.8.0
google-cloud-aiplatform >= 1.40.0
tomli >= 2.0.0  # Python < 3.11 compatibility
typer >= 0.9.0  # CLI framework (already in project dependencies)
```

---

## Installation

### 1. Install MixSeek-Core with Member Agent Bundle

```bash
# Install from PyPI (future)
pip install mixseek-core[member-agents]

# Or install development version
git clone https://github.com/your-org/mixseek-core.git
cd mixseek-core
uv sync --extra member-agents
```

### 2. Environment Variables Reference

**重要**: API キーは Pydantic AI の標準環境変数を使用してください（`MIXSEEK_` プレフィックスなし）。

#### Provider Authentication (Pydantic AI Standard)

##### Google Gemini Developer API

```bash
export GOOGLE_API_KEY="AIzaSy..."
```

取得方法: https://aistudio.google.com/apikey

##### Google Vertex AI

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="my-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

詳細: https://cloud.google.com/docs/authentication

##### Anthropic Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

取得方法: https://console.anthropic.com/settings/keys

##### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

取得方法: https://platform.openai.com/api-keys

#### MixSeek-Specific Settings (Optional)

MixSeek 固有の設定のみ `MIXSEEK_` プレフィックスを使用します。

```bash
export MIXSEEK_DEVELOPMENT_MODE=true
export MIXSEEK_LOG_LEVEL="DEBUG"
export MIXSEEK_CLI_OUTPUT_FORMAT="json"
```

これらの設定は環境変数または TOML ファイルで指定できます。

---

### 3. Set Up Configuration

#### Option A: TOML Configuration (Recommended)

Create a configuration file at `~/.mixseek/environment.toml`:

```toml
[environment]
# MixSeek-specific settings only
development_mode = true
log_level = "INFO"
cli_output_format = "structured"

# Google-specific settings (NOT API key)
google_genai_use_vertexai = false

# ⚠️ SECURITY WARNING ⚠️
# DO NOT put API keys in TOML files!
# Use environment variables instead:
#
#   export GOOGLE_API_KEY="..."       # Google Gemini
#   export ANTHROPIC_API_KEY="..."    # Anthropic Claude
#   export OPENAI_API_KEY="..."       # OpenAI
#
# See "Environment Variables Reference" section for details.
```

#### Option B: Environment Variables (Override TOML)

```bash
# Development with Gemini API
export GOOGLE_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"  # Pydantic AI standard
export MIXSEEK_DEVELOPMENT_MODE=true

# Production with Vertex AI
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export MIXSEEK_DEVELOPMENT_MODE=false

# Using Anthropic Claude instead
export ANTHROPIC_API_KEY="sk-ant-..."  # Pydantic AI standard
export MIXSEEK_DEVELOPMENT_MODE=false
```

**Note**: Environment variables override TOML file settings. If you use environment variables, you don't need the TOML file.

### 🔒 Security Best Practices

**CRITICAL**: Never store API keys or credentials in configuration files that might be committed to version control.

#### Provider API Keys

- ✅ **DO**: Use Pydantic AI standard environment variables
  ```bash
  export GOOGLE_API_KEY="..."
  export ANTHROPIC_API_KEY="..."
  ```
- ✅ **DO**: Use `.env` files locally (add to `.gitignore`)
  ```bash
  # .env file
  GOOGLE_API_KEY=AIzaSy...
  ANTHROPIC_API_KEY=sk-ant-...
  ```
- ✅ **DO**: Use proper secrets management in production
  - AWS: AWS Secrets Manager
  - GCP: Secret Manager
  - Azure: Key Vault
  - Kubernetes: Sealed Secrets
- ❌ **DON'T**: Put API keys in TOML/JSON/YAML files
- ❌ **DON'T**: Use `MIXSEEK_` prefix for provider API keys

#### MixSeek-Specific Settings

- ✅ **CAN**: Put in TOML files (non-secret values)
  ```toml
  [environment]
  development_mode = true
  log_level = "INFO"
  ```
- ✅ **CAN**: Use `MIXSEEK_` prefix for environment variable overrides
  ```bash
  export MIXSEEK_DEVELOPMENT_MODE=true
  ```

**Constitution Compliance**: This follows Article 9 (Data Accuracy Mandate) requiring explicit data sources and prohibiting hardcoded credentials.

---

## Quick Start Examples

### 1. Plain Member Agent

Create a basic reasoning agent with no external tools.

#### Configuration File: `plain_agent.toml`
```toml
[agent]
name = "plain-assistant"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 2048
description = "General reasoning, analysis, and question answering"
capabilities = []  # Plain agents have no special capabilities

[agent.instructions]
text = """
You are a helpful assistant specialized in reasoning and analysis.
You provide clear, well-structured responses to user questions.
Focus on logical thinking and comprehensive explanations.
"""

[agent.retry_config]
max_retries = 1
initial_delay = 1.0
backoff_factor = 2.0

[agent.usage_limits]
request_limit = 10
total_tokens_limit = 10000
tool_calls_limit = 5

[agent.metadata]
version = "1.0.0"
author = "MixSeek-Core"
created = "2025-01-01"
```

#### Usage
```bash
# Test the plain agent
mixseek member "Explain the concept of recursion in programming" --config plain_agent.toml

# Or use predefined agent name (if configured)
mixseek member "What are the benefits of functional programming?" --agent plain
```

### 2. Web Search Member Agent

Create an agent with web search capabilities for current information.

#### Configuration File: `web_search_agent.toml`
```toml
[agent]
name = "research-agent"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 3072
description = "Web search, current events research, fact verification"
capabilities = ["web_search"]

[agent.instructions]
text = """
You are a research assistant with web search capabilities.
Search for current information when needed to provide accurate, up-to-date responses.
Always cite your sources and indicate when information is recent.
Synthesize information from multiple sources for comprehensive answers.
"""

[agent.retry_config]
max_retries = 2
initial_delay = 1.0
backoff_factor = 2.0

[agent.usage_limits]
request_limit = 15
total_tokens_limit = 15000
tool_calls_limit = 10

[agent.tool_settings.web_search]
max_results = 10
timeout = 30

[agent.metadata]
version = "1.0.0"
author = "MixSeek-Core"
created = "2025-01-01"
```

#### Usage
```bash
# Research current information
mixseek member "What are the latest developments in AI safety?" --config web_search_agent.toml

# With custom output format
mixseek member "Current stock market trends" --agent web-search --output-format json
```

### 3. Code Execution Member Agent

Create an agent that can execute code for calculations and data analysis.

#### Configuration File: `code_execution_agent.toml`
```toml
[agent]
name = "data-analyst"
type = "code_execution"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.1
max_tokens = 4096
description = "Data analysis, calculations, code execution, visualization"
capabilities = ["code_execution"]

[agent.instructions]
text = """
You are a data analyst with code execution capabilities.
Use Python code to perform calculations, data analysis, and generate visualizations.
Always explain your approach and interpret the results.
Ensure code is well-commented and follows best practices.
"""

[agent.retry_config]
max_retries = 1
initial_delay = 1.5
backoff_factor = 2.0

[agent.usage_limits]
request_limit = 20
total_tokens_limit = 20000
tool_calls_limit = 15

# WARNING: Code execution security is controlled by the model provider.
# The following configuration has NO EFFECT with Pydantic AI builtin CodeExecutionTool.
# Actual security constraints are provider-specific and non-configurable.
#
# Anthropic Claude provides:
# - 5 GiB RAM, 5 GiB Disk, 1 CPU (fixed)
# - Network access: Completely disabled (security)
# - Timeout: Minimum 5 minutes (non-configurable)
# - Pre-installed: pandas, numpy, matplotlib, scikit-learn, scipy, seaborn, Pillow, openpyxl
# - CVE-2025-54794/54795: Fixed, but monitor for updates
#
# [agent.tool_settings.code_execution]
# # These settings are documentation-only and do not affect actual execution:
# expected_min_timeout_seconds = 300  # Anthropic: 5 minutes minimum
# expected_network_access = false     # Anthropic: completely disabled

[agent.metadata]
version = "1.0.0"
author = "MixSeek-Core"
created = "2025-01-01"
```

#### Usage
```bash
# Perform data analysis
mixseek member "Calculate the compound annual growth rate for a $1000 investment that becomes $2500 over 5 years" --config code_execution_agent.toml

# Complex analysis
mixseek member "Analyze the statistical distribution of the following data: [1,2,3,4,5,6,7,8,9,10,15,20,25,30]" --agent code-exec --verbose
```

### 4. Custom Member Agent

Create your own custom agent with specialized domain knowledge and tools.

#### Prerequisites

Custom agents require one of two loading methods:
- **agent_module** (recommended): Python package installed via pip
- **path** (alternative): Standalone Python file for development

#### Option A: Using agent_module (Recommended)

**1. Install the custom agent package:**
```bash
# Install from PyPI or your package repository
pip install my-analytics-package
```

**2. Configuration File: `custom_data_analyst.toml`**
```toml
[agent]
name = "custom-data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.1
max_tokens = 4096
description = "Pandas/NumPy専門データ分析エージェント"

[agent.system_instruction]
text = """
You are a data analyst with expertise in pandas and numpy.
Analyze data using statistical methods and provide actionable insights.
Use professional visualization libraries when appropriate.
"""

[agent.plugin]
agent_module = "my_analytics_package.agents.data_analyst"
agent_class = "DataAnalystAgent"

[agent.retry_config]
max_retries = 2
initial_delay = 1.0
backoff_factor = 2.0

[agent.usage_limits]
max_requests_per_hour = 50
max_tokens_per_request = 4096
max_tokens_per_hour = 100000
```

**3. Usage:**
```bash
# Execute custom agent
mixseek member "売上データを分析してください" --config custom_data_analyst.toml

# With JSON output
mixseek member "Analyze customer churn patterns" \
  --config custom_data_analyst.toml \
  --output-format json
```

#### Option B: Using path (Development)

**1. Create Custom Agent Class: `custom_agent.py`**
```python
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult

class DataAnalystAgent(BaseMemberAgent):
    """データ分析専門カスタムエージェント"""

    async def execute(self, prompt: str, **kwargs) -> MemberAgentResult:
        """Execute analysis task"""
        # Custom implementation using self._agent (Pydantic AI Agent)
        result = await self._agent.run(prompt)

        return MemberAgentResult.success(
            content=result.data,
            agent_name=self.config.name,
            agent_type=self.config.type,
        )
```

**2. Configuration File: `custom_data_analyst.toml`**
```toml
[agent]
name = "custom-data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.1
max_tokens = 4096
description = "Pandas/NumPy専門データ分析エージェント"

[agent.system_instruction]
text = """
You are a data analyst with expertise in pandas and numpy.
Analyze data using statistical methods and provide actionable insights.
"""

[agent.plugin]
path = "/path/to/custom_agent.py"
agent_class = "DataAnalystAgent"
```

**3. Usage:**
```bash
# Execute using file path
mixseek member "売上データを分析してください" --config custom_data_analyst.toml
```

#### Fallback Configuration

For flexibility during development, you can specify both methods. The system will try `agent_module` first, then fall back to `path`:

```toml
[agent]
name = "custom-data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"

[agent.system_instruction]
text = "You are a data analyst..."

[agent.plugin]
agent_module = "my_analytics_package.agents.data_analyst"  # Priority 1
path = "/path/to/custom_agent.py"                          # Fallback (Priority 2)
agent_class = "DataAnalystAgent"
```

#### Error Handling

If the custom agent fails to load, you'll see detailed error messages:

**Module not found:**
```
Error: Failed to load custom agent from module 'my_package.agents.custom'.
ModuleNotFoundError: No module named 'my_package'.
Install package: pip install <package-name>
```

**File not found:**
```
Error: Failed to load custom agent from path '/path/to/custom_agent.py'.
FileNotFoundError: File not found.
Check file path in TOML config.
```

**Class not found:**
```
Error: Custom agent class 'WrongClassName' not found in module 'my_package.agents'.
Check agent_class in TOML config.
```

For detailed development guide, see the [Custom Agent Development Guide](../docs/member-agents.md#カスタムエージェント開発ガイド).

---

## CLI Command Reference

### `mixseek member`

Execute a Member Agent with a prompt (development/testing only).

#### Basic Syntax
```bash
mixseek member <prompt> [OPTIONS]
```

#### Required Arguments
- `<prompt>`: User prompt to send to the agent (quoted if contains spaces)

#### Agent Specification (choose one)
- `--config PATH`: Path to agent TOML configuration file
- `--agent NAME`: Name of predefined agent configuration

#### Options

**Basic Options**:
- `--workspace PATH, -w`: Workspace path (for log output and config relative path resolution)
- `--output-format FORMAT, -f`: Output format (`json`, `text`, `structured`, `csv`) [default: `structured`]
- `--verbose, -v`: Enable verbose output with debugging information
- `--timeout SECONDS`: Execution timeout (1-300 seconds) [default: 30]
- `--max-tokens NUMBER`: Override max tokens for this execution
- `--temperature FLOAT`: Override temperature (0.0-1.0) for this execution

> **Important: Workspace and Logging**
>
> - When using log file output, `--workspace` option or `MIXSEEK_WORKSPACE` environment variable is **strongly recommended**
> - Without workspace, log files are written to the current directory
> - Use `--no-log-file` to run without workspace (console logging only)
> - `--agent` option works without workspace, but log file output is affected

**Logging Options**:
- `--log-level LEVEL`: Log level (debug/info/warning/error/critical) [default: info]
- `--no-log-console`: Disable console log output
- `--no-log-file`: Disable file log output (works without workspace)

**Logfire Options (observability)**:
- `--logfire`: Enable Logfire full mode (message history and token usage)
- `--logfire-metadata`: Enable Logfire metadata mode (metadata only)
- `--logfire-http`: Enable Logfire HTTP capture mode (full mode + HTTP logging)

Note: Logfire options are mutually exclusive (only one can be specified)

#### Examples
```bash
# Basic usage
mixseek member "Hello, how are you?" --config my_agent.toml

# With overrides
mixseek member "Be creative!" --agent plain

# JSON output for automation
mixseek member "Analyze data" --agent code-exec --output-format json

# Verbose debugging
mixseek member "Debug this issue" --config debug_agent.toml --verbose

# Workspace and relative config path
mixseek member "Question" --config configs/my_agent.toml --workspace /path/to/workspace

# Enable debug logging
mixseek member "Question" --agent plain --log-level debug --verbose

# Logfire observability
mixseek member "Question" --agent plain --logfire

# Logfire metadata mode (production recommended)
mixseek member "Question" --agent plain --logfire-metadata
```

### `mixseek list-agents` (Future Feature)

List available predefined agent configurations.

```bash
# List all agents
mixseek list-agents

# Show detailed information
mixseek list-agents --show-details

# Custom config directory
mixseek list-agents --config-dir ./my-agents/
```

### `mixseek validate-config` (Future Feature)

Validate agent configuration files.

```bash
# Validate single config
mixseek validate-config my_agent.toml

# Strict validation
mixseek validate-config my_agent.toml --strict
```

---

## Configuration Guide

### TOML Configuration Structure

All Member Agents use TOML configuration files with this structure:

```toml
[agent]
# Required fields
name = "agent-identifier"           # Unique agent name
type = "plain|web_search|code_execution"  # Agent type

# Model configuration
model = "google-gla:gemini-2.5-flash-lite"  # Pydantic AI model identifier
temperature = 0.2                       # Response randomness (0.0-1.0)
max_tokens = 2048                      # Maximum response tokens

# Optional fields
description = "Human-readable agent description"
capabilities = ["list", "of", "capabilities"]  # Auto-generated for typed agents

# Required instructions
[agent.instructions]
text = """
Multi-line instructions for the agent.
Define role, behavior, and specific guidelines.
"""

# Retry configuration (optional - uses defaults if not specified)
[agent.retry_config]
max_retries = 1          # Maximum retry attempts (0-10)
initial_delay = 1.0      # Initial delay in seconds (0.1-60.0)
backoff_factor = 2.0     # Exponential backoff factor (1.0-10.0)

# Usage limits (optional - no limits if not specified)
[agent.usage_limits]
request_limit = 10       # Maximum requests per run
total_tokens_limit = 10000  # Maximum tokens per run
tool_calls_limit = 5     # Maximum tool calls per run

# Tool-specific settings (only for agents with tools)
[agent.tool_settings.web_search]      # For web_search type agents
max_results = 10         # Maximum search results (1-50)
timeout = 30            # Search timeout in seconds (1-120)

[agent.tool_settings.code_execution]  # For code_execution type agents
timeout = 60            # Code execution timeout (1-300)
allowed_modules = ["math", "statistics", "datetime"]  # Allowed Python modules
max_output_length = 10000  # Maximum output length

# Optional metadata
[agent.metadata]
version = "1.0.0"
author = "Your Name"
created = "2025-01-01"
```

### Environment Variables

Configure the Member Agent system using TOML files or environment variables:

#### TOML Configuration (Primary)
Create `~/.mixseek/environment.toml`:
```toml
[environment]
google_api_key = "your-api-key"
development_mode = true
log_level = "INFO"

# For production, uncomment these:
# google_application_credentials = "/path/to/service-account.json"
# google_genai_use_vertexai = true
# google_location = "us-central1"
# development_mode = false
```

#### Environment Variable Overrides
```bash
# Provider API keys (Pydantic AI standard)
GOOGLE_API_KEY="your-api-key"  # NO MIXSEEK_ prefix
ANTHROPIC_API_KEY="sk-ant-..."

# MixSeek-specific settings (these use MIXSEEK_ prefix)
MIXSEEK_DEVELOPMENT_MODE=true
MIXSEEK_GOOGLE_GENAI_USE_VERTEXAI=false

# For Vertex AI:
GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
```

#### Additional Configuration Options
```bash
# These can be set in TOML or as environment variables
MIXSEEK_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
MIXSEEK_CLI_OUTPUT_FORMAT="structured"  # json, text, structured
```

**Configuration Priority**: TOML file → Environment variables → Default values

---

## Integration with MixSeek-Core Framework

### Leader Agent Integration

Member Agents integrate with Leader Agents through the TUMIX framework:

```python
# Example Leader Agent tool integration (future)
from mixseek_core.agents import get_member_agent

@leader_agent.tool
async def delegate_analysis(
    ctx: RunContext[LeaderDeps],
    data: str,
    analysis_type: str
) -> str:
    """Delegate analysis to specialized Member Agent."""
    member_agent = get_member_agent(f"analysis-{analysis_type}")

    result = await member_agent.run(
        f"Analyze this data: {data}",
        deps=ctx.deps.member_deps,
        usage=ctx.usage
    )

    return result.output
```

### TOML Configuration in MixSeek-Core

Define team configurations that include Member Agents:

```toml
# team_config.toml (MixSeek-Core team configuration)
[team]
name = "analysis-team"
max_rounds = 5

[team.leader]
model = "google-gla:gemini-2.0-flash"
instructions = "Coordinate analysis tasks with member agents"

[[team.members]]
name = "data-analyst"
type = "code_execution"
model = "google-gla:gemini-2.5-flash-lite"
# ... member agent configuration

[[team.members]]
name = "researcher"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"
# ... member agent configuration
```

---

## Testing and Validation

### Unit Testing

Test individual Member Agent configurations:

```bash
# Basic functionality test
mixseek member "Test prompt" --config your_agent.toml --verbose

# Validate configuration
python -c "
from mixseek_core.config import load_member_config
config = load_member_config('your_agent.toml')
print('✅ Configuration is valid')
"
```

### Integration Testing

Test with actual API calls:

```bash
# Quick integration test
for agent in plain web_search code_execution; do
    echo "Testing ${agent} agent..."
    mixseek member "Simple test for ${agent}" --agent "${agent}" --timeout 60
done
```

### Performance Testing

Monitor usage and response times:

```bash
# Verbose output shows timing and usage
mixseek member "Performance test" --config your_agent.toml --verbose --output-format json > results.json
```

---

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```bash
# Error: "Authentication failed"
# Solution: Check API credentials
echo $GOOGLE_API_KEY  # Should not be empty
# Or for Vertex AI:
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -la $GOOGLE_APPLICATION_CREDENTIALS  # Should exist
```

#### 2. Configuration Errors
```bash
# Error: "Invalid configuration"
# Solution: Validate TOML syntax and required fields
python -c "
import tomllib
with open('your_agent.toml', 'rb') as f:
    data = tomllib.load(f)
    print('TOML syntax is valid')
    print('Required fields:', data.get('agent', {}).keys())
"
```

#### 3. Model Access Issues
```bash
# Error: "Model not found" or "Permission denied"
# Solution: Check model name and permissions
mixseek member "test" --config your_agent.toml --verbose
# Look for detailed error messages in verbose output
```

#### 4. Timeout Issues
```bash
# Error: "Execution timed out"
# Solution: Increase timeout or check prompt complexity
mixseek member "complex prompt" --config your_agent.toml --timeout 120
```

### Getting Help

1. **Verbose Output**: Always use `--verbose` for debugging
2. **JSON Output**: Use `--output-format json` for programmatic analysis
3. **Log Files**: Check application logs for detailed error information
4. **Configuration Validation**: Validate TOML files before use

---

## Best Practices

### 1. Configuration Management
- Keep configuration files in version control
- Use descriptive agent names and clear instructions
- Set appropriate temperature values for your use case
- Document agent capabilities and intended use

### 2. Prompt Engineering
- Be specific about expected output format
- Provide clear context and constraints
- Test prompts with different complexity levels
- Use examples in instructions when helpful

### 3. Development Workflow
1. Start with plain agents for basic testing
2. Add tools (web search, code execution) as needed
3. Test with various prompt types and complexity levels
4. Monitor usage and performance metrics
5. Integrate with full MixSeek-Core framework when ready

### 4. Production Readiness
- Use Vertex AI for production deployments
- Set appropriate usage limits and timeouts
- Monitor API usage and costs
- Implement proper error handling and logging
- Set `MIXSEEK_DEVELOPMENT_MODE=false`

---

## Next Steps

1. **Create Your First Agent**: Start with a simple plain agent
2. **Test Different Prompts**: Experiment with various prompt types
3. **Try Tool-Enabled Agents**: Test web search and code execution
4. **Integrate with MixSeek-Core**: Connect to the full framework
5. **Deploy to Production**: Configure Vertex AI and disable development mode

For more advanced usage and integration patterns, see the full MixSeek-Core documentation.