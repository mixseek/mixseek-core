# Data Model: MixSeek-Core Member Agent バンドル

**Date**: 2025-10-21
**Phase**: 1 - Data Model & Contracts

## Overview

This document defines the data models and entities for the MixSeek-Core Member Agent bundle implementation. All models use Pydantic for type safety and validation, following the established patterns from the existing mixseek codebase.

---

## Core Entities

### 1. MemberAgentConfig

**Purpose**: Configuration model for Member Agent definitions loaded from TOML files

```python
from pydantic import BaseModel, Field, field_validator, FieldValidationInfo, ConfigDict
from pydantic_ai import UsageLimits
from typing import Literal, Optional, Dict, Any
from enum import Enum

class AgentType(str, Enum):
    """Supported Member Agent types."""
    PLAIN = "plain"
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"

class AgentInstructions(BaseModel):
    """Agent instruction configuration."""
    text: str = Field(
        ...,
        min_length=10,
        description="System instructions for agent behavior"
    )

class CodeExecutionToolConfig(BaseModel):
    """Code execution tool information (documentation-only).

    CRITICAL: These settings are NOT enforced by Pydantic AI's CodeExecutionTool.
    Actual security constraints are controlled by the model provider
    (Anthropic/OpenAI/Google) and cannot be configured via Pydantic AI.

    This config serves as documentation of provider-specific behavior:
    - Anthropic Claude: 5 GiB RAM, 5 GiB Disk, 1 CPU, network completely disabled,
      minimum 5-minute timeout, pre-installed libraries only
    - OpenAI: Security details not publicly available
    - Google: Security details not publicly available

    For actual security constraints, refer to your model provider's documentation.
    """

    # Documentation-only fields (NOT enforced by Pydantic AI)
    provider_controlled: bool = Field(
        default=True,
        const=True,
        description="All security settings are provider-controlled (non-configurable)"
    )

    # Expected provider behavior (Anthropic Claude specific)
    expected_min_timeout_seconds: int = Field(
        default=300,  # Anthropic: 5 minutes minimum
        description="Expected minimum timeout enforced by provider (documentation only)"
    )
    expected_available_modules: list[str] = Field(
        default_factory=lambda: [
            "pandas", "numpy", "matplotlib", "scikit-learn",
            "scipy", "seaborn", "Pillow", "openpyxl"
        ],
        description="Expected pre-installed modules (Anthropic Claude, documentation only)"
    )
    expected_network_access: bool = Field(
        default=False,
        const=True,
        description="Expected network access (Anthropic: completely disabled)"
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True
    )

class WebSearchToolConfig(BaseModel):
    """Configuration for web search tools."""
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of search results"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        le=120,
        description="Web search timeout in seconds"
    )

class ToolSettings(BaseModel):
    """Tool-specific configuration settings."""
    code_execution: Optional[CodeExecutionToolConfig] = Field(
        default=None,
        description="Code execution tool configuration"
    )
    web_search: Optional[WebSearchToolConfig] = Field(
        default=None,
        description="Web search tool configuration"
    )

class MemberAgentConfig(BaseModel):
    """Configuration for a Member Agent loaded from TOML file."""

    # Required fields
    name: str = Field(..., description="Unique agent identifier")
    type: AgentType = Field(..., description="Agent type/capabilities")

    # Model configuration
    model: str = Field(
        default="google-gla:gemini-2.5-flash-lite",
        description="Pydantic AI model identifier"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Model temperature for response randomness (None uses model default)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens in model response (None uses model default)"
    )
    stop_sequences: Optional[list[str]] = Field(
        default=None,
        description="List of sequences where generation should stop"
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-p sampling parameter (None uses model default)"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed (supported by OpenAI/Gemini, not supported by Anthropic)"
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="HTTP request timeout in seconds for model API calls (None uses default timeout)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for LLM API calls (passed to Agent's retries parameter, 0 means no retries)"
    )

    # Instructions and behavior
    instructions: AgentInstructions = Field(
        ...,
        description="Agent instructions configuration"
    )
    description: str = Field(
        default="",
        description="Human-readable agent description"
    )

    # Capabilities and tools
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of agent capabilities"
    )

    # Tool-specific settings
    tool_settings: Optional[ToolSettings] = Field(
        default=None,
        description="Tool-specific configuration settings"
    )

    # Additional configuration
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for custom plugins and extensions"
    )

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model identifier format.

        Args:
            v: Model identifier to validate

        Returns:
            Validated model identifier

        Raises:
            ValueError: If model identifier is not a supported Google Gemini model
        """
        if not v.startswith('google-gla:'):
            raise ValueError(
                f"Unsupported model '{v}'. Only Google Gemini models are supported. "
                f"Model identifier must start with 'google-gla:', "
                f"e.g., 'google-gla:gemini-2.5-flash-lite' or 'anthropic:claude-haiku-4-5'"
            )
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name format.

        Args:
            v: Agent name to validate

        Returns:
            Validated agent name

        Raises:
            ValueError: If agent name contains invalid characters
        """
        if not v.replace('-', '').replace('_', '').replace('.', '').isalnum():
            raise ValueError(
                f"Invalid agent name '{v}'. Agent name must be alphanumeric "
                f"with only hyphens (-), underscores (_), or dots (.) as separators. "
                f"Examples: 'my-agent', 'data_analyst', 'agent.v1'"
            )
        return v

    @field_validator('capabilities')
    @classmethod
    def validate_capabilities(cls, v: list[str], info: FieldValidationInfo) -> list[str]:
        """Validate capabilities match agent type and auto-correct if needed.

        Args:
            v: List of capabilities to validate
            info: Field validation info containing other field values

        Returns:
            Validated and potentially corrected capabilities list

        Raises:
            ValueError: If capabilities are incompatible with agent type
        """
        agent_type = info.data.get('type')

        if agent_type == AgentType.PLAIN and v:
            raise ValueError(
                f"Plain agents should not declare capabilities, but got: {v}. "
                f"Plain agents perform general reasoning without external tools."
            )
        elif agent_type == AgentType.WEB_SEARCH:
            if 'web_search' not in v:
                # Note: In real implementation, this should log a warning
                # import logging; logging.warning(f"Agent with type 'WEB_SEARCH' missing 'web_search' capability. Auto-adding.")
                v.append('web_search')
        elif agent_type == AgentType.CODE_EXECUTION:
            if 'code_execution' not in v:
                # Note: In real implementation, this should log a warning
                # import logging; logging.warning(f"Agent with type 'CODE_EXECUTION' missing 'code_execution' capability. Auto-adding.")
                v.append('code_execution')

        return v

    @field_validator('tool_settings')
    @classmethod
    def validate_tool_settings(cls, v: Optional[ToolSettings], info: FieldValidationInfo) -> Optional[ToolSettings]:
        """Validate tool settings match agent capabilities.

        Args:
            v: Tool settings to validate
            info: Field validation info containing other field values

        Returns:
            Validated tool settings

        Raises:
            ValueError: If tool settings are incompatible with agent type
        """
        if v is None:
            return v

        agent_type = info.data.get('type')

        if agent_type == AgentType.PLAIN:
            if v.code_execution is not None or v.web_search is not None:
                # Note: In real implementation, this should log an error/warning
                # import logging; logging.error("Configuration error: Plain agents should not have tool settings.")
                raise ValueError(
                    f"Plain agents should not have tool settings, but got tool configurations. "
                    f"Plain agents perform reasoning without external tools."
                )
        elif agent_type == AgentType.WEB_SEARCH:
            if v.code_execution is not None:
                raise ValueError(
                    f"Web search agents should not have code execution tool settings. "
                    f"Use agent type 'code_execution' if code execution is needed."
                )
        elif agent_type == AgentType.CODE_EXECUTION:
            if v.web_search is not None:
                raise ValueError(
                    f"Code execution agents should not have web search tool settings. "
                    f"Use agent type 'web_search' if web search is needed."
                )

        return v

    # Pydantic v2 configuration
    model_config = ConfigDict(
        extra="forbid",  # Strict field validation
        str_strip_whitespace=True,
        validate_assignment=True
    )
```

**Relationships**:
- Loaded from TOML configuration files
- Used by `MemberAgent` class for initialization
- Validated by `ConfigLoader` service

**Validation Rules**:
- Model must be Google Gemini family
- Name must be alphanumeric with allowed separators
- Capabilities must match declared agent type
- Temperature constrained to [0.0, 1.0] range

---

### 2. MemberAgentResult

**Purpose**: Standardized result type for Member Agent operations

```python
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

class ResultStatus(str, Enum):
    """Member Agent operation result status."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

class MemberAgentResult(BaseModel):
    """Result of Member Agent operation."""

    # Status and outcome
    status: ResultStatus = Field(..., description="Operation result status")
    content: str = Field(..., description="Main result content")

    # Metadata
    agent_name: str = Field(..., description="Name of agent that produced result")
    agent_type: AgentType = Field(..., description="Type of agent")

    # Timing and performance
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Result generation timestamp"
    )
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Execution time in milliseconds"
    )

    # Usage tracking
    usage_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Model usage information (tokens, requests)"
    )

    # Error information
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is ERROR"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling"
    )

    # Warning information (separate from error)
    warning_message: Optional[str] = Field(
        default=None,
        description="Warning message if status is WARNING"
    )

    # Retry information for strict error handling
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries attempted before this result"
    )
    max_retries_exceeded: bool = Field(
        default=False,
        description="Whether maximum retry limit was exceeded"
    )

    # Additional context
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )

    # Class methods for easy construction
    @classmethod
    def success(
        cls,
        content: str,
        agent_name: str,
        agent_type: AgentType,
        execution_time_ms: Optional[int] = None,
        usage_info: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MemberAgentResult":
        """Create a successful result.

        Args:
            content: Main result content
            agent_name: Name of agent that produced result
            agent_type: Type of agent
            execution_time_ms: Execution time in milliseconds
            usage_info: Model usage information
            retry_count: Number of retries that were attempted
            metadata: Additional result metadata

        Returns:
            Successful MemberAgentResult instance
        """
        return cls(
            status=ResultStatus.SUCCESS,
            content=content,
            agent_name=agent_name,
            agent_type=agent_type,
            execution_time_ms=execution_time_ms,
            usage_info=usage_info,
            retry_count=retry_count,
            metadata=metadata or {}
        )

    @classmethod
    def error(
        cls,
        error_message: str,
        agent_name: str,
        agent_type: AgentType,
        error_code: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        retry_count: int = 0,
        max_retries_exceeded: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MemberAgentResult":
        """Create an error result.

        This method creates an error result for complete failures.
        No alternative processing or fallbacks should be attempted.

        Args:
            error_message: Detailed error message
            agent_name: Name of agent that produced result
            agent_type: Type of agent
            error_code: Error code for programmatic handling
            execution_time_ms: Execution time in milliseconds
            retry_count: Number of retries that were attempted
            max_retries_exceeded: Whether maximum retry limit was exceeded
            metadata: Additional result metadata

        Returns:
            Error MemberAgentResult instance
        """
        return cls(
            status=ResultStatus.ERROR,
            content="",  # No content on error - fail completely
            agent_name=agent_name,
            agent_type=agent_type,
            error_message=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            max_retries_exceeded=max_retries_exceeded,
            metadata=metadata or {}
        )

    @classmethod
    def warning(
        cls,
        content: str,
        warning_message: str,
        agent_name: str,
        agent_type: AgentType,
        execution_time_ms: Optional[int] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MemberAgentResult":
        """Create a warning result.

        Args:
            content: Main result content (partial or degraded)
            warning_message: Warning message describing the issue
            agent_name: Name of agent that produced result
            agent_type: Type of agent
            execution_time_ms: Execution time in milliseconds
            retry_count: Number of retries that were attempted
            metadata: Additional result metadata

        Returns:
            Warning MemberAgentResult instance
        """
        return cls(
            status=ResultStatus.WARNING,
            content=content,
            agent_name=agent_name,
            agent_type=agent_type,
            warning_message=warning_message,  # Use dedicated warning_message field
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            metadata=metadata or {}
        )

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == ResultStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if result is an error."""
        return self.status == ResultStatus.ERROR

    def is_warning(self) -> bool:
        """Check if result is a warning."""
        return self.status == ResultStatus.WARNING
```

**Relationships**:
- Returned by all Member Agent operations
- Used by CLI commands for output formatting
- Integrates with mixseek Result pattern

**Usage Tracking Integration**:
- Captures Pydantic AI RunUsage information
- Supports usage limits and monitoring
- Compatible with TUMIX framework requirements

---

### 3. EnvironmentConfig

**Purpose**: Environment-specific configuration with TOML file as primary source and environment variable overrides

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import tomli
import os

class GoogleAuthMode(str, Enum):
    """Google authentication modes."""
    API_KEY = "api_key"        # Gemini API with API key
    VERTEX_AI = "vertex_ai"    # Vertex AI with service account
    DEFAULT = "default"        # Application Default Credentials

class EnvironmentConfig(BaseSettings):
    """MixSeek-Core Member Agent environment configuration.

    Provider Authentication:
        API keys should be set using Pydantic AI standard environment variables
        WITHOUT the MIXSEEK_ prefix. They will be automatically read by
        Pydantic AI providers.

        Examples:
            export GOOGLE_API_KEY="AIzaSy..."           # Google Gemini
            export ANTHROPIC_API_KEY="sk-ant-..."       # Anthropic Claude
            export OPENAI_API_KEY="sk-..."              # OpenAI

    MixSeek-Specific Settings:
        Only MixSeek-specific configuration uses the MIXSEEK_ prefix.

        Examples:
            export MIXSEEK_DEVELOPMENT_MODE=true
            export MIXSEEK_LOG_LEVEL="DEBUG"
    """

    # MixSeek-specific settings only
    development_mode: bool = Field(
        default=False,
        description="Enable development mode with verbose logging and test models"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level for the application"
    )

    cli_output_format: Literal["json", "text", "structured"] = Field(
        default="structured",
        description="Default output format for CLI commands"
    )

    # Google-specific settings (NOT API key)
    google_genai_use_vertexai: bool = Field(
        default=False,
        description="Use Google Vertex AI instead of Gemini Developer API"
    )

    # Configuration sources: TOML file first, then environment variables
    model_config = SettingsConfigDict(
        env_prefix="MIXSEEK_",
        case_sensitive=False,
        extra="ignore"
    )

    @classmethod
    def from_toml_and_env(
        cls,
        toml_path: Optional[Path] = None,
        env_overrides: bool = True
    ) -> "EnvironmentConfig":
        """Load configuration from TOML file with optional environment overrides.

        Priority:
        1. TOML file values (if file exists)
        2. Environment variables (if env_overrides=True) - override TOML values
        3. Default values (from Field definitions)

        Args:
            toml_path: Path to environment.toml file (defaults to ~/.mixseek/environment.toml)
            env_overrides: Whether environment variables should override TOML values

        Returns:
            EnvironmentConfig instance with merged configuration

        Note:
            API keys are NOT managed by this config. Pydantic AI providers
            automatically read standard environment variables (GOOGLE_API_KEY,
            ANTHROPIC_API_KEY, etc.) without MIXSEEK_ prefix.
        """
        # Set default TOML path
        if toml_path is None:
            toml_path = Path.home() / ".mixseek" / "environment.toml"

        toml_data: Dict[str, Any] = {}

        # Load TOML file if it exists
        if toml_path.exists():
            with open(toml_path, "rb") as f:
                full_toml = tomli.load(f)
                # Extract environment section if it exists
                toml_data = full_toml.get("environment", {})

        # Create instance from TOML data first
        if env_overrides:
            # Environment variables will automatically override due to pydantic-settings
            return cls(**toml_data)
        else:
            # Disable environment variable loading for testing
            return cls.model_validate(toml_data)

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @classmethod
    def example_provider_creation(cls) -> None:
        """Example of creating providers with standard environment variables.

        This method demonstrates that API keys are NOT managed by EnvironmentConfig.
        Providers automatically read their standard environment variables.

        Raises:
            UserError: If required environment variables are not set
        """
        from pydantic_ai.providers import GoogleProvider, AnthropicProvider

        # Providers read environment variables automatically
        google = GoogleProvider()  # Reads GOOGLE_API_KEY
        anthropic = AnthropicProvider()  # Reads ANTHROPIC_API_KEY

        # For Vertex AI, additional environment variables may be needed
        # (GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, etc.)
```

**Relationships**:
- Loaded at application startup
- Used by Member Agent initialization
- Integrates with existing mixseek environment patterns

**Configuration Priority**:
1. **TOML file** (`~/.mixseek/environment.toml`) - Primary configuration source
2. **Environment variables** - Override TOML values if set
3. **Default values** - Fallback if neither TOML nor environment variables exist

**TOML Configuration Example** (`~/.mixseek/environment.toml`):
```toml
[environment]
# Google API Configuration
google_api_key = "your-gemini-api-key"
google_genai_use_vertexai = false
development_mode = true
log_level = "INFO"

# Optional: Vertex AI settings (uncomment to use)
# google_application_credentials = "/path/to/service-account.json"
# google_genai_use_vertexai = true
# google_project_id = "your-project-id"  # Optional: overrides auto-detected value
# google_location = "us-central1"
# development_mode = false
```

**Environment Variable Overrides**:

**Provider Authentication (Pydantic AI Standard - NO MIXSEEK_ prefix)**:
- `GOOGLE_API_KEY` → Automatically read by GoogleProvider
- `ANTHROPIC_API_KEY` → Automatically read by AnthropicProvider
- `OPENAI_API_KEY` → Automatically read by OpenAIProvider
- `GOOGLE_APPLICATION_CREDENTIALS` → Standard Google SDK environment variable
- `GOOGLE_CLOUD_PROJECT` → Standard Google Cloud environment variable
- `GOOGLE_CLOUD_LOCATION` → Standard Google Cloud environment variable

**MixSeek-Specific Settings (MIXSEEK_ prefix)**:
- `MIXSEEK_DEVELOPMENT_MODE` → overrides `development_mode`
- `MIXSEEK_LOG_LEVEL` → overrides `log_level`
- `MIXSEEK_CLI_OUTPUT_FORMAT` → overrides `cli_output_format`
- `MIXSEEK_GOOGLE_GENAI_USE_VERTEXAI` → overrides `google_genai_use_vertexai`

---

### 4. CLI Command Models

**Purpose**: CLI-specific data models for command processing

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from pathlib import Path

class TestMemberCommand(BaseModel):
    """Command model for 'mixseek member' CLI command."""

    # Required parameters
    prompt: str = Field(
        ...,
        min_length=1,
        description="User prompt to send to Member Agent"
    )

    # Agent specification (mutually exclusive)
    config_file: Optional[Path] = Field(
        default=None,
        description="Path to agent TOML configuration file"
    )
    agent_name: Optional[str] = Field(
        default=None,
        description="Name of predefined agent configuration"
    )

    # Output options
    output_format: Literal["json", "text", "structured"] = Field(
        default="structured",
        description="Output format for results"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output with debugging info"
    )

    # Execution options
    timeout: int = Field(
        default=30,
        gt=0,
        le=300,
        description="Execution timeout in seconds"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Override max tokens for this execution"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override temperature for this execution"
    )

    def validate_agent_specification(self) -> None:
        """Validate that exactly one agent specification is provided."""
        specs_provided = sum([
            self.config_file is not None,
            self.agent_name is not None
        ])

        if specs_provided != 1:
            raise ValueError(
                "Exactly one of --config or --agent must be specified"
            )

    def get_effective_config_path(self, base_config_dir: Path) -> Path:
        """Get effective configuration file path."""
        if self.config_file:
            return self.config_file
        elif self.agent_name:
            return base_config_dir / f"{self.agent_name}.toml"
        else:
            raise ValueError("No agent specification provided")

class CLIResult(BaseModel):
    """CLI command execution result."""

    success: bool = Field(..., description="Whether command succeeded")
    message: str = Field(..., description="Result message")

    # Member agent result (if applicable)
    agent_result: Optional[MemberAgentResult] = Field(
        default=None,
        description="Member agent execution result"
    )

    # CLI execution metadata
    command: str = Field(..., description="Command that was executed")
    execution_time_ms: int = Field(..., description="CLI execution time")

    # Additional context
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional CLI result metadata"
    )

    def format_output(self, format_type: Literal["json", "text", "structured"]) -> str:
        """Format result for CLI output."""
        if format_type == "json":
            return self.model_dump_json(indent=2)
        elif format_type == "text":
            return self.message
        else:  # structured
            lines = [
                f"Command: {self.command}",
                f"Status: {'SUCCESS' if self.success else 'ERROR'}",
                f"Message: {self.message}",
                f"Duration: {self.execution_time_ms}ms"
            ]

            if self.agent_result:
                lines.extend([
                    "",
                    "Agent Result:",
                    f"  Agent: {self.agent_result.agent_name}",
                    f"  Type: {self.agent_result.agent_type}",
                    f"  Status: {self.agent_result.status}",
                    f"  Content: {self.agent_result.content[:100]}{'...' if len(self.agent_result.content) > 100 else ''}"
                ])

            return "\n".join(lines)
```

**Relationships**:
- Used by CLI command handlers
- Integrates with existing mixseek CLI patterns
- Provides consistent command validation and result formatting

---

## Validation Rules Summary

### Configuration Validation
1. **Model Names**: Must start with `google-gla:`
2. **Agent Names**: Alphanumeric with hyphens, underscores, dots only
3. **Temperature**: Range [0.0, 1.0]
4. **Max Tokens**: Range (0, 8192]
5. **Capabilities**: Must match agent type

### Environment Validation
1. **Credentials**: Service account files must exist
2. **Auth Mode**: Consistent authentication configuration required
3. **Log Levels**: Must be valid Python logging levels

### CLI Validation
1. **Agent Specification**: Exactly one of config file or agent name
2. **Timeout**: Range (0, 300] seconds
3. **Output Format**: Must be supported format type

## Integration Points

### With Existing Mixseek Patterns

#### Result Models Integration
**Existing Pattern** (`mixseek.models.result.InitResult`):
```python
class InitResult(BaseModel):
    success: bool
    workspace_path: Path
    created_dirs: list[Path] = Field(default_factory=list)
    created_files: list[Path] = Field(default_factory=list)
    message: str = ""
    error: str | None = None

    @classmethod
    def success_result(cls, ...): ...
```

**MemberAgentResult Integration**:
- Extends existing result pattern with agent-specific fields
- Uses same `success: bool` and `error: str | None` pattern
- Adds `@classmethod` factory methods like existing `success_result()`
- Will be added to existing `mixseek.models.result` module

#### Configuration Integration
**Existing Pattern** (`mixseek.models.config.ProjectConfig`):
```python
class ProjectConfig(BaseModel):
    project_name: str
    workspace_path: str
    log_level: Literal["DEBUG", "INFO", ...]

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str: ...
```

**MemberAgentConfig Integration**:
- Follows same Pydantic validation pattern
- Uses `@field_validator` with `FieldValidationInfo`
- Will be added as `mixseek.models.member_agent.MemberAgentConfig`

#### CLI Integration
**Existing Pattern** (`mixseek.cli.commands.init`):
```python
import typer
from mixseek.models.result import InitResult

def init(workspace: Path | None = typer.Option(...)) -> None: ...
```

**Test-Member Command Integration**:
- Uses same `typer` framework
- Imports from `mixseek.models.result import MemberAgentResult`
- Will be added as `mixseek.cli.commands.test_member`

#### Environment Variables Integration
**Existing Pattern** (`mixseek.utils.env`):
- Extends existing environment variable handling
- Adds Google API credentials management
- Maintains same validation and error patterns

#### Exception Handling Integration
**Existing Pattern** (`mixseek.exceptions`):
- Extends existing exception hierarchy
- Adds `MemberAgentError`, `ConfigurationError`, etc.
- Maintains same error context patterns

### With Pydantic AI
- **Agent Configuration**: Direct mapping to Agent constructor parameters
- **Usage Tracking**: Captures RunUsage for monitoring
- **Error Handling**: Maps Pydantic AI exceptions to result models

### With MixSeek-Core Framework
- **TUMIX Integration**: Models support TUMIX client integration
- **Leader Communication**: Result models compatible with Leader Agent requirements
- **Submission Format**: Can be converted to MixSeek-Core Submission format

## Error Handling Patterns

All models implement comprehensive error handling:
- **Validation Errors**: Clear messages with field-specific feedback
- **Configuration Errors**: Early detection with actionable error messages
- **Runtime Errors**: Structured error results with debugging information
- **Type Safety**: Full Pydantic validation prevents runtime type errors

## Future Extensibility

Models are designed for future extension:
- **Additional Agent Types**: Easy to add new AgentType enum values
- **Tool Integration**: Capability system supports new tool types
- **Authentication Methods**: Environment config supports new auth modes
- **Output Formats**: CLI models support additional format types