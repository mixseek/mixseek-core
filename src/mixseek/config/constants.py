"""Constants for MixSeek configuration."""

from typing import Literal

# Default project name placeholder for sample configuration
DEFAULT_PROJECT_NAME: str = "mixseek-project"

# Environment variable name for workspace path
WORKSPACE_ENV_VAR: str = "MIXSEEK_WORKSPACE"

# Log format default
DEFAULT_LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log level default
DEFAULT_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

# Maximum recursion depth for config file loading (Phase 13 T107, FR-043)
# Prevents infinite loops and stack overflow in nested configuration references
MAX_CONFIG_RECURSION_DEPTH: int = 10

# Sensitive field patterns for security masking (Article 9: Data Accuracy Mandate)
# Field names containing these patterns will be masked in output
# Article 9 Compliance: Explicit list (no implicit assumptions)
SENSITIVE_FIELD_PATTERNS: tuple[str, ...] = (
    "api_key",
    "password",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
)

# Non-sensitive field exceptions (Article 9: Data Accuracy Mandate)
# Field names that should NOT be masked even if they match sensitive patterns
# Article 9 Compliance: Explicit list (no implicit assumptions)
NON_SENSITIVE_FIELD_EXCEPTIONS: tuple[str, ...] = (
    "max_tokens",  # LLM parameter, not a security token
)

# Pre-computed lowercase set for efficient O(1) membership testing
# This avoids repeated list comprehensions in _is_sensitive_field()
_NON_SENSITIVE_FIELD_EXCEPTIONS_LOWER: frozenset[str] = frozenset(
    exc.lower() for exc in NON_SENSITIVE_FIELD_EXCEPTIONS
)

# Masked value displayed for sensitive fields
MASKED_VALUE: str = "[REDACTED]"
