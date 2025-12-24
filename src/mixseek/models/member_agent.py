"""Member Agent configuration and data models.

This module contains the data models for the MixSeek-Core Member Agent bundle,
including configuration models, result types, and environment settings.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from pydantic_ai.messages import ModelMessage
from pydantic_settings import BaseSettings, SettingsConfigDict

# Model configuration constants
MAX_TOKENS_LOWER_BOUND = 1
MAX_TOKENS_UPPER_BOUND = 65536
MAX_TOKENS_DEFAULT = 2048


class AgentType(str, Enum):
    """Supported Member Agent types."""

    PLAIN = "plain"
    WEB_SEARCH = "web_search"
    WEB_FETCH = "web_fetch"
    CODE_EXECUTION = "code_execution"
    CUSTOM = "custom"

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value


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
    agent_type: str = Field(..., description="Type of agent")

    # Timing and performance
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Result generation timestamp")
    execution_time_ms: int | None = Field(default=None, description="Execution time in milliseconds")

    # Usage tracking
    usage_info: dict[str, Any] | None = Field(default=None, description="Model usage information (tokens, requests)")

    # Error information
    error_message: str | None = Field(default=None, description="Error message if status is ERROR")
    error_code: str | None = Field(default=None, description="Error code for programmatic handling")

    # Warning information (separate from error)
    warning_message: str | None = Field(default=None, description="Warning message if status is WARNING")

    # Retry information for strict error handling
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted before this result")
    max_retries_exceeded: bool = Field(default=False, description="Whether maximum retry limit was exceeded")

    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional result metadata")

    # Message history (FR-016: Complete message history from Pydantic AI)
    all_messages: list[ModelMessage] | None = Field(
        default=None,
        description="Complete message history from Pydantic AI including tool calls and intermediate reasoning",
    )

    @classmethod
    def success(
        cls,
        content: str,
        agent_name: str,
        agent_type: str,
        execution_time_ms: int | None = None,
        usage_info: dict[str, Any] | None = None,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
        all_messages: list[ModelMessage] | None = None,
    ) -> "MemberAgentResult":
        """Create a successful result."""
        return cls(
            status=ResultStatus.SUCCESS,
            content=content,
            agent_name=agent_name,
            agent_type=agent_type,
            execution_time_ms=execution_time_ms,
            usage_info=usage_info,
            retry_count=retry_count,
            metadata=metadata or {},
            all_messages=all_messages,
        )

    @classmethod
    def error(
        cls,
        error_message: str,
        agent_name: str,
        agent_type: str,
        error_code: str | None = None,
        execution_time_ms: int | None = None,
        retry_count: int = 0,
        max_retries_exceeded: bool = False,
        metadata: dict[str, Any] | None = None,
        all_messages: list[ModelMessage] | None = None,
    ) -> "MemberAgentResult":
        """Create an error result."""
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
            metadata=metadata or {},
            all_messages=all_messages,
        )

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == ResultStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if result is an error."""
        return self.status == ResultStatus.ERROR


class WebSearchToolConfig(BaseModel):
    """Configuration for web search tools."""

    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of search results")
    timeout: int = Field(default=30, gt=0, le=120, description="Web search timeout in seconds")


class WebFetchToolConfig(BaseModel):
    """Configuration for web fetch tools (Anthropic parameters).

    Note: These parameters are only supported by Anthropic models.
    Google models will ignore these settings.
    OpenAI and Grok models do not support WebFetchTool.
    """

    max_uses: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of tool invocations",
    )
    allowed_domains: list[str] | None = Field(
        default=None,
        description="Whitelist of allowed domains (mutually exclusive with blocked_domains)",
    )
    blocked_domains: list[str] | None = Field(
        default=None,
        description="Blacklist of blocked domains (mutually exclusive with allowed_domains)",
    )
    enable_citations: bool = Field(
        default=False,
        description="Enable source citation in responses",
    )
    max_content_tokens: int | None = Field(
        default=None,
        ge=1,
        le=50000,
        description="Maximum content size in tokens (max 50000)",
    )

    @model_validator(mode="after")
    def validate_domain_exclusivity(self) -> Self:
        """Validate that allowed_domains and blocked_domains are mutually exclusive."""
        if self.allowed_domains and self.blocked_domains:
            raise ValueError("allowed_domains and blocked_domains are mutually exclusive. Use only one of them.")
        return self


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
    provider_controlled: Literal[True] = Field(
        default=True, description="All security settings are provider-controlled (non-configurable)"
    )

    # Expected provider behavior (Anthropic Claude specific)
    expected_min_timeout_seconds: int = Field(
        default=300,  # Anthropic: 5 minutes minimum
        description="Expected minimum timeout enforced by provider (documentation only)",
    )
    expected_available_modules: list[str] = Field(
        default_factory=lambda: [
            "pandas",
            "numpy",
            "matplotlib",
            "scikit-learn",
            "scipy",
            "seaborn",
            "Pillow",
            "openpyxl",
        ],
        description="Expected pre-installed modules (Anthropic Claude, documentation only)",
    )
    expected_network_access: Literal[False] = Field(
        default=False, description="Expected network access (Anthropic: completely disabled)"
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class ToolSettings(BaseModel):
    """Tool-specific configuration settings."""

    web_search: WebSearchToolConfig | None = Field(default=None, description="Web search tool configuration")
    web_fetch: WebFetchToolConfig | None = Field(default=None, description="Web fetch tool configuration")
    code_execution: CodeExecutionToolConfig | None = Field(
        default=None, description="Code execution tool configuration"
    )

    # Issue #146: Allow custom tool settings for custom agents (e.g., bitbank_api)
    model_config = ConfigDict(extra="allow")


class PluginMetadata(BaseModel):
    """Plugin configuration for custom Member Agents (FR-020).

    Supports two loading methods:
    - agent_module (recommended): Python module path for pip-installable packages
    - path (alternative): File path for standalone development files

    Priority (FR-021):
    1. agent_module is tried first if specified
    2. path is used as fallback if agent_module fails or is not specified
    """

    agent_module: str | None = Field(
        default=None,
        description="Python module path (e.g., 'my_package.agents.custom'). Recommended for production.",
    )
    path: str | None = Field(
        default=None, description="File path (e.g., '/path/to/custom_agent.py'). Alternative for development."
    )
    agent_class: str = Field(..., description="Agent class name (e.g., 'MyCustomAgent'). Required.")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class MemberAgentConfig(BaseModel):
    """Configuration for a Member Agent loaded from TOML file."""

    # Required fields
    name: str = Field(..., description="Unique agent identifier")
    type: str = Field(..., description="Agent type/capabilities")

    # Model configuration
    model: str = Field(default="google-gla:gemini-2.5-flash-lite", description="Pydantic AI model identifier")
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Model temperature for response randomness (None uses model default)"
    )
    max_tokens: int | None = Field(
        default=None, gt=0, description="Maximum tokens in model response (None uses model default)"
    )
    stop_sequences: list[str] | None = Field(
        default=None, description="List of sequences where generation should stop"
    )
    top_p: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Top-p sampling parameter (None uses model default)"
    )
    seed: int | None = Field(
        default=None, description="Random seed (supported by OpenAI/Gemini, not supported by Anthropic)"
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="HTTP request timeout in seconds for model API calls (None uses default timeout)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for LLM API calls (passed to Agent's retries parameter, 0 means no retries)",
    )

    # Instructions and behavior
    system_instruction: str | None = Field(default=None, description="Agent system instruction (str or None)")
    system_prompt: str | None = Field(
        default=None,
        description="System prompt (Pydantic AI system_prompt, optional, can be used with system_instruction)",
    )
    description: str = Field(default="", description="Human-readable agent description")

    # Tool-specific configuration
    tool_settings: ToolSettings | None = Field(default=None, description="Tool-specific configuration settings")

    # Plugin configuration for custom agents (FR-020)
    plugin: PluginMetadata | None = Field(default=None, description="Plugin configuration for custom agent loading")

    # Additional configuration
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional configuration metadata")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info: ValidationInfo) -> str:
        """Validate model identifier format.

        Note: Custom agents (type="custom") skip prefix validation and can use
        any model prefix. Builtin agents require standard prefixes.

        IMPORTANT: This validator depends on field definition order.
        The 'type' field MUST be defined before 'model' field (Pydantic v2
        validates fields in definition order). If field order changes,
        info.data.get("type") may return None.
        """
        # Skip prefix validation for custom agents - they can use any model prefix
        # but still require basic format: non-empty string with colon separator
        if info.data.get("type") == AgentType.CUSTOM.value:
            if not v or ":" not in v:
                raise ValueError(
                    f"Invalid model format '{v}'. Custom agents require "
                    f"'prefix:model' format (e.g., 'my-provider:my-model')."
                )
            return v

        # Existing validation logic for builtin agents
        # Support Google AI, Vertex AI, OpenAI, Anthropic, and Grok models
        if v.startswith("google-gla:"):
            return v
        elif v.startswith("google-vertex:"):
            return v
        elif v.startswith("openai:"):
            return v
        elif v.startswith("anthropic:"):
            return v
        elif v.startswith("grok:"):
            return v
        elif v.startswith("grok-responses:"):
            return v
        else:
            raise ValueError(
                f"Unsupported model '{v}'. Supported models: "
                f"Google AI (e.g., 'google-gla:gemini-2.5-flash-lite'), "
                f"Google Vertex AI (e.g., 'google-vertex:gemini-2.5-flash-lite'), "
                f"OpenAI (e.g., 'openai:gpt-4o'), "
                f"Anthropic Claude (e.g., 'anthropic:claude-3-5-sonnet-20241022'), "
                f"Grok (e.g., 'grok:grok-2-1212'), or "
                f"Grok with tools (e.g., 'grok-responses:grok-4-fast'). "
                f"Model identifier must start with 'google-gla:', 'google-vertex:', "
                f"'openai:', 'anthropic:', 'grok:', or 'grok-responses:'"
            )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name format."""
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                f"Invalid agent name '{v}'. Agent name must be alphanumeric "
                f"with only hyphens (-), underscores (_), or dots (.) as separators. "
                f"Examples: 'my-agent', 'data_analyst', 'agent.v1'"
            )
        return v

    @field_validator("system_instruction", mode="before")
    @classmethod
    def normalize_system_instruction(cls, v: Any) -> str | None:
        """Normalize system_instruction for future extensibility.

        Supports:
        - str: Direct string value (recommended format)
        - dict with 'text': Extensible format for future features
          (e.g., {'text': '...', 'lang': 'ja', 'template': True})
        - None: No instruction

        This allows future extensions like multi-language support,
        template variables, or other metadata without changing the core API.
        """
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, dict) and "text" in v:
            # Future: could extract lang, template flags here
            text_value = v["text"]
            if not isinstance(text_value, str):
                raise ValueError(f"system_instruction.text must be str, got {type(text_value).__name__}")
            return text_value
        raise ValueError(f"system_instruction must be str or dict with 'text' key, got {type(v).__name__}")

    # Pydantic v2 configuration
    model_config = ConfigDict(
        extra="forbid",  # Strict field validation
        str_strip_whitespace=True,
        validate_assignment=True,
    )


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
        default=False, description="Enable development mode with verbose logging and test models"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level for the application"
    )

    cli_output_format: Literal["json", "text", "structured"] = Field(
        default="structured", description="Default output format for CLI commands"
    )

    # Google-specific settings (NOT API key)
    google_genai_use_vertexai: bool = Field(
        default=False, description="Use Google Vertex AI instead of Gemini Developer API"
    )

    # Configuration sources: TOML file first, then environment variables
    model_config = SettingsConfigDict(env_prefix="MIXSEEK_", case_sensitive=False, extra="ignore")

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        if isinstance(v, str):
            v_upper = v.upper()
            valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if v_upper in valid_levels:
                return v_upper
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v
