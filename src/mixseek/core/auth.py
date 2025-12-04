"""Authentication module for MixSeek-Core Member Agents.

This module implements Article 9 (Data Accuracy Mandate) compliant authentication
handling for Google AI and Vertex AI providers. It enforces explicit error handling
and prohibits implicit fallbacks to ensure constitutional compliance.

Constitutional Requirements:
- Article 9: NO implicit fallbacks, explicit data source specification
- Article 3: Test-first development with comprehensive test coverage
"""

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

import httpx
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.grok import GrokProvider

# Managed HTTP clients for cleanup
_managed_http_clients: list[httpx.AsyncClient] = []


class AuthProvider(Enum):
    """Supported authentication providers."""

    GOOGLE_AI = "google_ai"
    VERTEX_AI = "vertex_ai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROK = "grok"
    GROK_RESPONSES = "grok_responses"
    TEST_MODEL = "test_model"


class AuthenticationError(Exception):
    """Raised when authentication validation fails.

    This exception enforces Article 9 compliance by providing explicit
    error messages instead of silent fallbacks.
    """

    def __init__(self, message: str, provider: AuthProvider, suggestion: str = ""):
        self.provider = provider
        self.suggestion = suggestion
        super().__init__(f"[{provider.value}] {message}")


def detect_auth_provider(model_id: str) -> AuthProvider:
    """Detect the required authentication provider from model ID.

    Args:
        model_id: Model identifier (e.g., "google-gla:gemini-2.5-flash-lite", "google-vertex:gemini-2.5-flash-lite")

    Returns:
        AuthProvider: Required authentication provider

    Raises:
        AuthenticationError: If model ID format is invalid
    """
    if model_id.startswith("google-gla:"):
        return AuthProvider.GOOGLE_AI

    elif model_id.startswith("google-vertex:"):
        return AuthProvider.VERTEX_AI

    elif model_id.startswith("openai:"):
        return AuthProvider.OPENAI

    elif model_id.startswith("anthropic:"):
        return AuthProvider.ANTHROPIC

    elif model_id.startswith("grok:"):
        return AuthProvider.GROK

    elif model_id.startswith("grok-responses:"):
        return AuthProvider.GROK_RESPONSES

    raise AuthenticationError(
        f"Unsupported model ID format: {model_id}",
        AuthProvider.GOOGLE_AI,
        "Use format 'google-gla:model-name' for Google AI models, "
        "'google-vertex:model-name' for Vertex AI models, "
        "'openai:model-name' for OpenAI models, "
        "'anthropic:model-name' for Anthropic Claude models, "
        "'grok:model-name' for Grok models, or "
        "'grok-responses:model-name' for Grok with web search tools",
    )


def validate_test_environment() -> bool:
    """Check if we're running in a legitimate test environment.

    Returns:
        bool: True if running under pytest, False otherwise

    Note:
        This is the ONLY condition under which TestModel usage is allowed.
        Article 9 compliance: Explicit test environment detection.
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def validate_google_ai_credentials() -> None:
    """Validate Google AI API credentials.

    Raises:
        AuthenticationError: If GOOGLE_API_KEY is missing or invalid format
    """
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise AuthenticationError(
            "GOOGLE_API_KEY environment variable not found",
            AuthProvider.GOOGLE_AI,
            "Set your Google AI API key: export GOOGLE_API_KEY=your_key_here",
        )

    if not api_key.strip():
        raise AuthenticationError(
            "GOOGLE_API_KEY environment variable is empty",
            AuthProvider.GOOGLE_AI,
            "Ensure GOOGLE_API_KEY contains a valid API key",
        )

    # Basic format validation (Google AI keys typically start with 'AIza')
    if len(api_key.strip()) < 20:
        raise AuthenticationError(
            "GOOGLE_API_KEY appears to be invalid (too short)",
            AuthProvider.GOOGLE_AI,
            "Verify your Google AI API key is correctly set",
        )


def validate_vertex_ai_credentials() -> None:
    """Validate Vertex AI credentials.

    Raises:
        AuthenticationError: If GOOGLE_APPLICATION_CREDENTIALS is missing or invalid
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not creds_path:
        raise AuthenticationError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable not found",
            AuthProvider.VERTEX_AI,
            "Set path to GCP service account JSON: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json",
        )

    if not creds_path.strip():
        raise AuthenticationError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable is empty",
            AuthProvider.VERTEX_AI,
            "Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid JSON file",
        )

    # Validate file exists and is readable
    creds_file = Path(creds_path.strip())

    if not creds_file.exists():
        raise AuthenticationError(
            f"Credentials file not found: {creds_path}",
            AuthProvider.VERTEX_AI,
            "Verify the file path in GOOGLE_APPLICATION_CREDENTIALS exists",
        )

    if not creds_file.is_file():
        raise AuthenticationError(
            f"Credentials path is not a file: {creds_path}",
            AuthProvider.VERTEX_AI,
            "GOOGLE_APPLICATION_CREDENTIALS must point to a JSON file",
        )

    try:
        # Basic JSON format validation
        import json

        with open(creds_file) as f:
            cred_data = json.load(f)

        # Check for required GCP service account fields
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        missing_fields = [field for field in required_fields if field not in cred_data]

        if missing_fields:
            raise AuthenticationError(
                f"Invalid GCP credentials file, missing fields: {', '.join(missing_fields)}",
                AuthProvider.VERTEX_AI,
                "Ensure you're using a valid GCP service account JSON file",
            )

    except json.JSONDecodeError as e:
        raise AuthenticationError(
            f"Invalid JSON in credentials file: {str(e)}",
            AuthProvider.VERTEX_AI,
            "Verify the credentials file contains valid JSON",
        )
    except PermissionError:
        raise AuthenticationError(
            f"Cannot read credentials file: {creds_path}",
            AuthProvider.VERTEX_AI,
            "Check file permissions for GOOGLE_APPLICATION_CREDENTIALS",
        )


@lru_cache(maxsize=32)
def _create_google_model_cached(model_name: str, provider_type: Literal["google-gla", "google-vertex"]) -> GoogleModel:
    """Create a cached GoogleModel instance with dedicated HTTP client.

    This function solves the HTTPClient sharing issue when multiple GoogleModel
    instances are created with the same model name. By caching the model instance
    and providing a dedicated HTTP client, we prevent premature client closure
    that can occur in concurrent async operations.

    Args:
        model_name: Base model name (e.g., "gemini-2.0-flash-lite", "gemini-2.5-flash")
        provider_type: Provider type ("google-gla" for Google AI, "google-vertex" for Vertex AI)

    Returns:
        GoogleModel: Cached model instance with dedicated HTTP client

    Note:
        This caching strategy is essential for RoundController where multiple agents
        (Evaluator, JudgmentClient) may be instantiated in the same round.
        Without caching, each agent would create a new GoogleModel instance, leading
        to HTTPClient conflicts in async execution.
    """
    # Create dedicated HTTP client with appropriate timeouts
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=600, connect=5),
        headers={"User-Agent": "mixseek-core/1.0"},
    )

    # Add to managed clients for cleanup
    _managed_http_clients.append(http_client)

    # Create GoogleProvider with dedicated HTTP client
    google_provider = GoogleProvider(
        vertexai=(provider_type == "google-vertex"),
        http_client=http_client,
    )

    # Create GoogleModel with dedicated provider
    return GoogleModel(model_name, provider=google_provider)


def validate_anthropic_credentials() -> None:
    """Validate Anthropic API credentials.

    Raises:
        AuthenticationError: If ANTHROPIC_API_KEY is missing or invalid format
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise AuthenticationError(
            "ANTHROPIC_API_KEY environment variable not found",
            AuthProvider.ANTHROPIC,
            "Set your Anthropic API key: export ANTHROPIC_API_KEY=your_key_here",
        )

    if not api_key.strip():
        raise AuthenticationError(
            "ANTHROPIC_API_KEY environment variable is empty",
            AuthProvider.ANTHROPIC,
            "Ensure ANTHROPIC_API_KEY contains a valid API key",
        )

    # Basic format validation (Anthropic keys typically start with 'sk-ant-')
    if not api_key.strip().startswith("sk-ant-"):
        raise AuthenticationError(
            "ANTHROPIC_API_KEY appears to be invalid (should start with 'sk-ant-')",
            AuthProvider.ANTHROPIC,
            "Verify your Anthropic API key format",
        )


def validate_openai_credentials() -> None:
    """Validate OpenAI API credentials.

    Raises:
        AuthenticationError: If OPENAI_API_KEY is missing or invalid format
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise AuthenticationError(
            "OPENAI_API_KEY environment variable not found",
            AuthProvider.OPENAI,
            "Set your OpenAI API key: export OPENAI_API_KEY=your_key_here",
        )

    if not api_key.strip():
        raise AuthenticationError(
            "OPENAI_API_KEY environment variable is empty",
            AuthProvider.OPENAI,
            "Ensure OPENAI_API_KEY contains a valid API key",
        )

    # Basic format validation (OpenAI keys typically start with 'sk-')
    if not api_key.strip().startswith(("sk-", "sk-proj-")):
        raise AuthenticationError(
            "OPENAI_API_KEY appears to be invalid (should start with 'sk-' or 'sk-proj-')",
            AuthProvider.OPENAI,
            "Verify your OpenAI API key format",
        )


def validate_grok_credentials() -> None:
    """Validate Grok (xAI) API credentials.

    Raises:
        AuthenticationError: If GROK_API_KEY is missing or invalid format
    """
    api_key = os.getenv("GROK_API_KEY")

    if not api_key:
        raise AuthenticationError(
            "GROK_API_KEY environment variable not found",
            AuthProvider.GROK,
            "Set your Grok API key: export GROK_API_KEY=your_key_here",
        )

    if not api_key.strip():
        raise AuthenticationError(
            "GROK_API_KEY environment variable is empty",
            AuthProvider.GROK,
            "Ensure GROK_API_KEY contains a valid API key",
        )

    # Basic format validation (Grok keys typically start with 'xai-')
    if not api_key.strip().startswith("xai-"):
        raise AuthenticationError(
            "GROK_API_KEY appears to be invalid (should start with 'xai-')",
            AuthProvider.GROK,
            "Verify your Grok API key format",
        )


def create_authenticated_model(
    model_id: str,
) -> GoogleModel | OpenAIChatModel | OpenAIResponsesModel | AnthropicModel | TestModel:
    """Create an authenticated model instance with Article 9 compliance.

    This function enforces constitutional requirements:
    - NO implicit fallbacks to TestModel
    - Explicit error handling for all authentication failures
    - Clear separation between test and production environments

    Args:
        model_id: Model identifier (e.g., "google-gla:gemini-2.5-flash-lite",
                  "google-vertex:gemini-2.5-flash-lite", "openai:gpt-4o", "anthropic:claude-sonnet-4-5-20250929")

    Returns:
        Union[GoogleModel, OpenAIModel, AnthropicModel, TestModel]: Authenticated model instance

    Raises:
        AuthenticationError: If authentication validation fails
    """
    # CRITICAL: Article 9 compliance - only use TestModel in legitimate test environment
    if validate_test_environment():
        return TestModel()

    # Detect required authentication provider
    auth_provider = detect_auth_provider(model_id)

    # Validate credentials based on provider
    if auth_provider == AuthProvider.GOOGLE_AI:
        validate_google_ai_credentials()
        # Extract base model name (remove 'google-gla:' prefix)
        base_model_name = model_id.replace("google-gla:", "")
        # Use cached GoogleModel to prevent HTTPClient sharing issues
        return _create_google_model_cached(base_model_name, "google-gla")

    elif auth_provider == AuthProvider.VERTEX_AI:
        validate_vertex_ai_credentials()
        # T098: Use explicit provider parameter instead of environment variable
        # pydantic-ai's GoogleModel handles Vertex AI mode via provider="google-vertex"
        # No need to set GOOGLE_GENAI_USE_VERTEXAI environment variable
        base_model_name = model_id.replace("google-vertex:", "")
        # Use cached GoogleModel to prevent HTTPClient sharing issues
        return _create_google_model_cached(base_model_name, "google-vertex")

    elif auth_provider == AuthProvider.OPENAI:
        validate_openai_credentials()
        # Extract base model name (remove 'openai:' prefix)
        base_model_name = model_id.replace("openai:", "")
        return OpenAIChatModel(base_model_name)

    elif auth_provider == AuthProvider.ANTHROPIC:
        validate_anthropic_credentials()
        # Extract base model name (remove 'anthropic:' prefix)
        base_model_name = model_id.replace("anthropic:", "")
        return AnthropicModel(base_model_name)

    elif auth_provider == AuthProvider.GROK:
        validate_grok_credentials()
        # Extract base model name (remove 'grok:' prefix)
        base_model_name = model_id.replace("grok:", "")
        # Grok uses OpenAI-compatible API via GrokProvider
        # validate_grok_credentials() ensures GROK_API_KEY is set
        grok_api_key = os.getenv("GROK_API_KEY")
        assert grok_api_key is not None  # Guaranteed by validate_grok_credentials()
        grok_provider = GrokProvider(api_key=grok_api_key)
        return OpenAIChatModel(base_model_name, provider=grok_provider)

    elif auth_provider == AuthProvider.GROK_RESPONSES:
        validate_grok_credentials()
        # Extract base model name (remove 'grok-responses:' prefix)
        base_model_name = model_id.replace("grok-responses:", "")
        # Grok Responses API supports web_search and x_search tools
        # Uses OpenAIResponsesModel with provider='grok'
        return OpenAIResponsesModel(base_model_name, provider="grok")

    else:
        # This should never be reached due to detect_auth_provider validation
        raise AuthenticationError(
            f"Unsupported authentication provider: {auth_provider}",
            auth_provider,
            "Contact support if you see this error",
        )


def get_auth_info(model_id: str) -> dict[str, str]:
    """Get authentication information for debugging and logging.

    Args:
        model_id: Model identifier

    Returns:
        dict: Authentication info without sensitive data
    """
    if validate_test_environment():
        return {
            "provider": "test_model",
            "environment": "test",
            "model_id": model_id,
            "credentials_status": "test_mode",
        }

    try:
        auth_provider = detect_auth_provider(model_id)

        if auth_provider == AuthProvider.GOOGLE_AI:
            api_key = os.getenv("GOOGLE_API_KEY", "")
            return {
                "provider": "google_ai",
                "environment": "production",
                "model_id": model_id,
                "credentials_status": "present" if api_key else "missing",
            }

        elif auth_provider == AuthProvider.VERTEX_AI:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
            return {
                "provider": "vertex_ai",
                "environment": "production",
                "model_id": model_id,
                "credentials_status": "present" if creds_path else "missing",
                "credentials_file": creds_path if creds_path else "not_set",
            }

        elif auth_provider == AuthProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY", "")
            return {
                "provider": "openai",
                "environment": "production",
                "model_id": model_id,
                "credentials_status": "present" if api_key else "missing",
            }

        elif auth_provider == AuthProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            return {
                "provider": "anthropic",
                "environment": "production",
                "model_id": model_id,
                "credentials_status": "present" if api_key else "missing",
            }

        elif auth_provider in (AuthProvider.GROK, AuthProvider.GROK_RESPONSES):
            api_key = os.getenv("GROK_API_KEY", "")
            return {
                "provider": auth_provider.value,
                "environment": "production",
                "model_id": model_id,
                "credentials_status": "present" if api_key else "missing",
            }

    except AuthenticationError:
        return {
            "provider": "unknown",
            "environment": "production",
            "model_id": model_id,
            "credentials_status": "error",
        }

    return {"provider": "unknown", "environment": "unknown", "model_id": model_id, "credentials_status": "unknown"}


async def close_all_auth_clients() -> None:
    """Close all managed HTTP clients created by the auth module.

    This should be called during application shutdown to prevent resource leaks.
    Closes all httpx.AsyncClient instances that were created by _create_google_model_cached
    and clears the management list.

    Note:
        This function is idempotent - it's safe to call multiple times.
        Already closed clients will be skipped.

    Example:
        ```python
        import asyncio
        from mixseek.core.auth import close_all_auth_clients

        # At application shutdown
        asyncio.run(close_all_auth_clients())
        ```
    """
    for client in _managed_http_clients:
        if not client.is_closed:
            await client.aclose()
    _managed_http_clients.clear()


def clear_auth_caches() -> None:
    """Clear all cached models and HTTP clients for event loop reset.

    This function should be called before asyncio.run() in contexts where
    the event loop may be recreated (e.g., Streamlit UI). It prevents
    'Event loop is closed' errors caused by cached httpx clients holding
    references to closed event loops.

    The function clears:
    - _create_google_model_cached LRU cache (GoogleModel instances)
    - _managed_http_clients list (httpx.AsyncClient references)
    - pydantic_ai's internal _cached_async_http_client

    Note:
        This is a synchronous function and can be called safely before
        asyncio.run(). For async cleanup with proper client closure,
        use close_all_auth_clients() instead.

    Example:
        ```python
        from mixseek.core.auth import clear_auth_caches

        # Before asyncio.run() in Streamlit or similar contexts
        clear_auth_caches()
        result = asyncio.run(async_operation())
        ```
    """
    # Clear this repository's caches
    _create_google_model_cached.cache_clear()
    _managed_http_clients.clear()

    # Clear pydantic_ai's cached HTTP client (also holds event loop references)
    try:
        from pydantic_ai.models import _cached_async_http_client

        _cached_async_http_client.cache_clear()
    except (ImportError, AttributeError):
        # pydantic_ai API may change; gracefully handle missing cache
        pass
