"""Unit tests for authentication module.

This test suite validates the authentication module's compliance with
Article 9 (Data Accuracy Mandate) and Article 3 (Test-First Imperative).

Constitutional requirements tested:
- NO implicit fallbacks to mock responses
- Explicit error handling for all authentication failures
- Clear separation between test and production environments
- Proper credential validation for Google AI and Vertex AI
"""

import json
import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mixseek.core.auth import (
    AuthenticationError,
    AuthProvider,
    _create_google_model_cached,
    _managed_http_clients,
    clear_auth_caches,
    create_authenticated_model,
    detect_auth_provider,
    get_auth_info,
    validate_google_ai_credentials,
    validate_grok_credentials,
    validate_test_environment,
    validate_vertex_ai_credentials,
)


class TestAuthProvider:
    """Test authentication provider detection."""

    def test_detect_google_ai_provider(self) -> None:
        """Test detection of Google AI provider with google-gla: prefix."""
        provider = detect_auth_provider("google-gla:gemini-2.5-flash-lite")
        assert provider == AuthProvider.GOOGLE_AI

    def test_detect_vertex_ai_provider(self) -> None:
        """Test detection of Vertex AI provider with google-vertex: prefix."""
        provider = detect_auth_provider("google-vertex:gemini-2.5-flash-lite")
        assert provider == AuthProvider.VERTEX_AI

    def test_detect_openai_provider(self) -> None:
        """Test detection of OpenAI provider with openai: prefix."""
        provider = detect_auth_provider("openai:gpt-4o")
        assert provider == AuthProvider.OPENAI

    def test_detect_anthropic_provider(self) -> None:
        """Test detection of Anthropic provider with anthropic: prefix."""
        provider = detect_auth_provider("anthropic:claude-sonnet-4-5-20250929")
        assert provider == AuthProvider.ANTHROPIC

    def test_detect_grok_provider(self) -> None:
        """Test detection of Grok provider with grok: prefix."""
        provider = detect_auth_provider("grok:grok-2-1212")
        assert provider == AuthProvider.GROK

    def test_invalid_model_id_raises_error(self) -> None:
        """Test that invalid model ID raises authentication error."""
        with pytest.raises(AuthenticationError) as exc_info:
            detect_auth_provider("invalid-model-id")

        assert "Unsupported model ID format" in str(exc_info.value)
        assert exc_info.value.provider == AuthProvider.GOOGLE_AI


class TestEnvironmentDetection:
    """Test environment detection for Article 9 compliance."""

    def test_validate_test_environment_with_pytest(self) -> None:
        """Test that pytest environment is correctly detected."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_auth.py::test_function"}):
            assert validate_test_environment() is True

    def test_validate_test_environment_without_pytest(self) -> None:
        """Test that production environment is correctly detected."""
        # Ensure PYTEST_CURRENT_TEST is not set
        with patch.dict(os.environ, {}, clear=True):
            assert validate_test_environment() is False

    def test_validate_test_environment_empty_var(self) -> None:
        """Test that empty PYTEST_CURRENT_TEST is treated as production."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            assert validate_test_environment() is False


class TestGoogleAICredentials:
    """Test Google AI credential validation for Article 9 compliance."""

    def test_validate_google_ai_credentials_success(self) -> None:
        """Test successful Google AI credential validation."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza" + "x" * 35}):
            # Should not raise any exception
            validate_google_ai_credentials()

    def test_validate_google_ai_credentials_missing(self) -> None:
        """Test error when GOOGLE_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_google_ai_credentials()

            assert "GOOGLE_API_KEY environment variable not found" in str(exc_info.value)
            assert exc_info.value.provider == AuthProvider.GOOGLE_AI
            assert "export GOOGLE_API_KEY" in exc_info.value.suggestion

    def test_validate_google_ai_credentials_empty(self) -> None:
        """Test error when GOOGLE_API_KEY is empty."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "   "}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_google_ai_credentials()

            assert "GOOGLE_API_KEY environment variable is empty" in str(exc_info.value)

    def test_validate_google_ai_credentials_too_short(self) -> None:
        """Test error when GOOGLE_API_KEY appears invalid."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "short"}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_google_ai_credentials()

            assert "appears to be invalid" in str(exc_info.value)


class TestVertexAICredentials:
    """Test Vertex AI credential validation for Article 9 compliance."""

    def test_validate_vertex_ai_credentials_missing_env_var(self) -> None:
        """Test error when GOOGLE_APPLICATION_CREDENTIALS is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_vertex_ai_credentials()

            assert "GOOGLE_APPLICATION_CREDENTIALS environment variable not found" in str(exc_info.value)
            assert exc_info.value.provider == AuthProvider.VERTEX_AI

    def test_validate_vertex_ai_credentials_empty_env_var(self) -> None:
        """Test error when GOOGLE_APPLICATION_CREDENTIALS is empty."""
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "   "}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_vertex_ai_credentials()

            assert "GOOGLE_APPLICATION_CREDENTIALS environment variable is empty" in str(exc_info.value)

    def test_validate_vertex_ai_credentials_file_not_found(self) -> None:
        """Test error when credentials file doesn't exist."""
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/path.json"}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_vertex_ai_credentials()

            assert "Credentials file not found" in str(exc_info.value)

    def test_validate_vertex_ai_credentials_not_a_file(self) -> None:
        """Test error when credentials path is not a file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": tmp_dir}):
                with pytest.raises(AuthenticationError) as exc_info:
                    validate_vertex_ai_credentials()

                assert "Credentials path is not a file" in str(exc_info.value)

    def test_validate_vertex_ai_credentials_invalid_json(self) -> None:
        """Test error when credentials file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            tmp_file.write("invalid json content")
            tmp_file.flush()

            try:
                with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": tmp_file.name}):
                    with pytest.raises(AuthenticationError) as exc_info:
                        validate_vertex_ai_credentials()

                    assert "Invalid JSON in credentials file" in str(exc_info.value)
            finally:
                os.unlink(tmp_file.name)

    def test_validate_vertex_ai_credentials_missing_fields(self) -> None:
        """Test error when credentials file is missing required fields."""
        invalid_creds = {"type": "service_account"}  # Missing other required fields

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            json.dump(invalid_creds, tmp_file)
            tmp_file.flush()

            try:
                with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": tmp_file.name}):
                    with pytest.raises(AuthenticationError) as exc_info:
                        validate_vertex_ai_credentials()

                    assert "missing fields" in str(exc_info.value)
                    assert "project_id" in str(exc_info.value)
            finally:
                os.unlink(tmp_file.name)

    def test_validate_vertex_ai_credentials_success(self) -> None:
        """Test successful Vertex AI credential validation."""
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            json.dump(valid_creds, tmp_file)
            tmp_file.flush()

            try:
                with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": tmp_file.name}):
                    # Should not raise any exception
                    validate_vertex_ai_credentials()
            finally:
                os.unlink(tmp_file.name)


class TestGrokCredentials:
    """Test Grok (xAI) credential validation for Article 9 compliance."""

    def test_validate_grok_credentials_success(self) -> None:
        """Test successful Grok credential validation."""
        with patch.dict(os.environ, {"GROK_API_KEY": "xai-" + "x" * 40}):
            # Should not raise any exception
            validate_grok_credentials()

    def test_validate_grok_credentials_missing(self) -> None:
        """Test error when GROK_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_grok_credentials()

            assert "GROK_API_KEY environment variable not found" in str(exc_info.value)
            assert exc_info.value.provider == AuthProvider.GROK
            assert "export GROK_API_KEY" in exc_info.value.suggestion

    def test_validate_grok_credentials_empty(self) -> None:
        """Test error when GROK_API_KEY is empty."""
        with patch.dict(os.environ, {"GROK_API_KEY": "   "}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_grok_credentials()

            assert "GROK_API_KEY environment variable is empty" in str(exc_info.value)

    def test_validate_grok_credentials_invalid_format(self) -> None:
        """Test error when GROK_API_KEY has invalid format."""
        with patch.dict(os.environ, {"GROK_API_KEY": "invalid-key-format"}):
            with pytest.raises(AuthenticationError) as exc_info:
                validate_grok_credentials()

            assert "appears to be invalid" in str(exc_info.value)
            assert "should start with 'xai-'" in str(exc_info.value)


class TestAuthenticatedModelCreation:
    """Test authenticated model creation with Article 9 compliance."""

    @patch("mixseek.core.auth.validate_test_environment")
    @patch("mixseek.core.auth.TestModel")
    def test_create_authenticated_model_in_test_environment(
        self, mock_test_model: Any, mock_validate_test: Any
    ) -> None:
        """Test TestModel creation in legitimate test environment."""
        mock_validate_test.return_value = True
        mock_test_instance = MagicMock()
        mock_test_model.return_value = mock_test_instance

        model = create_authenticated_model("google-gla:gemini-2.5-flash-lite")

        assert model == mock_test_instance
        mock_test_model.assert_called_once()

    @patch("mixseek.core.auth.validate_test_environment")
    @patch("mixseek.core.auth.validate_google_ai_credentials")
    @patch("mixseek.core.auth._create_google_model_cached")
    def test_create_authenticated_model_google_ai_success(
        self, mock_cached_model: Any, mock_validate_creds: Any, mock_validate_test: Any
    ) -> None:
        """Test successful Google AI model creation."""
        mock_validate_test.return_value = False
        mock_validate_creds.return_value = None  # Success
        mock_model_instance = MagicMock()
        mock_cached_model.return_value = mock_model_instance

        with patch.dict(os.environ, {"GOOGLE_GENAI_USE_VERTEXAI": "false"}, clear=True):
            model = create_authenticated_model("google-gla:gemini-2.5-flash-lite")

            assert model == mock_model_instance
            mock_validate_creds.assert_called_once()
            mock_cached_model.assert_called_once_with("gemini-2.5-flash-lite", "google-gla")

    @patch("mixseek.core.auth.validate_test_environment")
    def test_create_authenticated_model_google_ai_failure(self, mock_validate_test: Any) -> None:
        """Test Google AI authentication failure propagation."""
        mock_validate_test.return_value = False

        # Test with missing credentials to trigger actual authentication error
        with patch.dict(os.environ, {"GOOGLE_GENAI_USE_VERTEXAI": "false"}, clear=True):
            with pytest.raises(AuthenticationError) as exc_info:
                create_authenticated_model("google-gla:gemini-2.5-flash-lite")

            assert "GOOGLE_API_KEY environment variable not found" in str(exc_info.value)
            assert exc_info.value.provider == AuthProvider.GOOGLE_AI

    @patch("mixseek.core.auth.validate_test_environment")
    @patch("mixseek.core.auth.validate_vertex_ai_credentials")
    @patch("mixseek.core.auth._create_google_model_cached")
    def test_create_authenticated_model_vertex_ai_success(
        self, mock_cached_model: Any, mock_validate_creds: Any, mock_validate_test: Any
    ) -> None:
        """Test successful Vertex AI model creation with google-vertex: prefix."""
        mock_validate_test.return_value = False
        mock_validate_creds.return_value = None  # Success
        mock_model_instance = MagicMock()
        mock_cached_model.return_value = mock_model_instance

        model = create_authenticated_model("google-vertex:gemini-2.5-flash-lite")

        assert model == mock_model_instance
        mock_validate_creds.assert_called_once()
        mock_cached_model.assert_called_once_with("gemini-2.5-flash-lite", "google-vertex")

    @patch("mixseek.core.auth.validate_test_environment")
    @patch("mixseek.core.auth.validate_grok_credentials")
    @patch("mixseek.core.auth.GrokProvider")
    @patch("mixseek.core.auth.OpenAIChatModel")
    def test_create_authenticated_model_grok_success(
        self,
        mock_openai_model: Any,
        mock_grok_provider: Any,
        mock_validate_creds: Any,
        mock_validate_test: Any,
    ) -> None:
        """Test successful Grok model creation with grok: prefix."""
        mock_validate_test.return_value = False
        mock_validate_creds.return_value = None  # Success
        mock_provider_instance = MagicMock()
        mock_grok_provider.return_value = mock_provider_instance
        mock_model_instance = MagicMock()
        mock_openai_model.return_value = mock_model_instance

        with patch.dict(os.environ, {"GROK_API_KEY": "xai-test-key"}, clear=True):
            model = create_authenticated_model("grok:grok-2-1212")

            assert model == mock_model_instance
            mock_validate_creds.assert_called_once()
            mock_grok_provider.assert_called_once_with(api_key="xai-test-key")
            mock_openai_model.assert_called_once_with("grok-2-1212", provider=mock_provider_instance)


class TestAuthInfo:
    """Test authentication information retrieval."""

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_test_environment(self, mock_validate_test: Any) -> None:
        """Test auth info in test environment."""
        mock_validate_test.return_value = True

        info = get_auth_info("google-gla:gemini-2.5-flash-lite")

        assert info["provider"] == "test_model"
        assert info["environment"] == "test"
        assert info["credentials_status"] == "test_mode"

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_google_ai_with_credentials(self, mock_validate_test: Any) -> None:
        """Test auth info for Google AI with credentials."""
        mock_validate_test.return_value = False

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=True):
            info = get_auth_info("google-gla:gemini-2.5-flash-lite")

            assert info["provider"] == "google_ai"
            assert info["environment"] == "production"
            assert info["credentials_status"] == "present"

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_google_ai_without_credentials(self, mock_validate_test: Any) -> None:
        """Test auth info for Google AI without credentials."""
        mock_validate_test.return_value = False

        with patch.dict(os.environ, {}, clear=True):
            info = get_auth_info("google-gla:gemini-2.5-flash-lite")

            assert info["provider"] == "google_ai"
            assert info["environment"] == "production"
            assert info["credentials_status"] == "missing"

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_vertex_ai_with_credentials(self, mock_validate_test: Any) -> None:
        """Test auth info for Vertex AI with credentials."""
        mock_validate_test.return_value = False

        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"}, clear=True):
            info = get_auth_info("google-vertex:gemini-2.5-flash-lite")

            assert info["provider"] == "vertex_ai"
            assert info["environment"] == "production"
            assert info["credentials_status"] == "present"
            assert info["credentials_file"] == "/path/to/creds.json"

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_grok_with_credentials(self, mock_validate_test: Any) -> None:
        """Test auth info for Grok with credentials."""
        mock_validate_test.return_value = False

        with patch.dict(os.environ, {"GROK_API_KEY": "xai-test-key"}, clear=True):
            info = get_auth_info("grok:grok-2-1212")

            assert info["provider"] == "grok"
            assert info["environment"] == "production"
            assert info["credentials_status"] == "present"

    @patch("mixseek.core.auth.validate_test_environment")
    def test_get_auth_info_grok_without_credentials(self, mock_validate_test: Any) -> None:
        """Test auth info for Grok without credentials."""
        mock_validate_test.return_value = False

        with patch.dict(os.environ, {}, clear=True):
            info = get_auth_info("grok:grok-2-1212")

            assert info["provider"] == "grok"
            assert info["environment"] == "production"
            assert info["credentials_status"] == "missing"


class TestConstitutionalCompliance:
    """Test Article 9 constitutional compliance requirements."""

    def test_no_implicit_fallbacks_on_missing_google_api_key(self) -> None:
        """Test that missing GOOGLE_API_KEY does NOT fall back to TestModel."""
        with patch.dict(os.environ, {}, clear=True):
            # This should raise an authentication error, NOT silently use TestModel
            with pytest.raises(AuthenticationError) as exc_info:
                create_authenticated_model("google-gla:gemini-2.5-flash-lite")

            assert "GOOGLE_API_KEY environment variable not found" in str(exc_info.value)

    def test_no_implicit_fallbacks_on_missing_vertex_credentials(self) -> None:
        """Test that missing Vertex AI credentials do NOT fall back to TestModel."""
        with patch.dict(os.environ, {}, clear=True):
            # This should raise an authentication error, NOT silently use TestModel
            with pytest.raises(AuthenticationError) as exc_info:
                create_authenticated_model("google-vertex:gemini-2.5-flash-lite")

            assert "GOOGLE_APPLICATION_CREDENTIALS environment variable not found" in str(exc_info.value)

    def test_explicit_error_propagation(self) -> None:
        """Test that authentication errors are explicitly propagated."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError) as exc_info:
                create_authenticated_model("google-gla:gemini-2.5-flash-lite")

            # Verify proper error type and message
            assert isinstance(exc_info.value, AuthenticationError)
            assert "GOOGLE_API_KEY environment variable not found" in str(exc_info.value)

    @patch("mixseek.core.auth.validate_test_environment")
    def test_test_model_only_in_legitimate_test_environment(self, mock_validate_test: Any) -> None:
        """Test that TestModel is ONLY used when PYTEST_CURRENT_TEST is set."""
        # First test: TestModel allowed in test environment
        mock_validate_test.return_value = True
        # Should create TestModel instance (mocked)
        create_authenticated_model("google-gla:gemini-2.5-flash-lite")

        # Second test: TestModel forbidden in production
        mock_validate_test.return_value = False
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError):
                create_authenticated_model("google-gla:gemini-2.5-flash-lite")

    def test_no_silent_error_handling(self) -> None:
        """Test that all authentication errors are raised, not silently handled."""
        error_scenarios: list[tuple[dict[str, str], str]] = [
            # Missing Google API key
            ({}, "google-gla:gemini-2.5-flash-lite"),
            # Missing Vertex AI credentials
            ({}, "google-vertex:gemini-2.5-flash-lite"),
        ]

        for env_vars, model_id in error_scenarios:
            with patch.dict(os.environ, env_vars, clear=True):
                with pytest.raises(AuthenticationError):
                    create_authenticated_model(model_id)


class TestClearAuthCaches:
    """Test clear_auth_caches function for Issue #197 fix.

    This test suite validates the cache clearing functionality that prevents
    'Event loop is closed' errors when using asyncio.run() multiple times
    in Streamlit UI or similar contexts.
    """

    def test_clear_auth_caches_clears_model_cache(self) -> None:
        """Test that clear_auth_caches clears the GoogleModel LRU cache."""
        # Populate the cache with some entries (using mock to avoid actual model creation)
        with patch("mixseek.core.auth.httpx.AsyncClient"):
            with patch("mixseek.core.auth.GoogleProvider"):
                with patch("mixseek.core.auth.GoogleModel"):
                    # Call the cached function to populate cache
                    _create_google_model_cached("gemini-2.5-flash", "google-gla")
                    _create_google_model_cached("gemini-2.5-flash-lite", "google-gla")

                    # Verify cache has entries
                    cache_info = _create_google_model_cached.cache_info()
                    assert cache_info.currsize > 0, "Cache should have entries before clearing"

                    # Clear the caches
                    clear_auth_caches()

                    # Verify cache is cleared
                    cache_info_after = _create_google_model_cached.cache_info()
                    assert cache_info_after.currsize == 0, "Cache should be empty after clearing"

    def test_clear_auth_caches_clears_http_clients_list(self) -> None:
        """Test that clear_auth_caches clears the _managed_http_clients list."""
        # Add some mock clients to the list
        mock_client_1 = MagicMock()
        mock_client_2 = MagicMock()
        _managed_http_clients.append(mock_client_1)
        _managed_http_clients.append(mock_client_2)

        # Verify list has entries
        assert len(_managed_http_clients) > 0, "List should have entries before clearing"

        # Clear the caches
        clear_auth_caches()

        # Verify list is cleared
        assert len(_managed_http_clients) == 0, "List should be empty after clearing"

    def test_clear_auth_caches_is_idempotent(self) -> None:
        """Test that clear_auth_caches can be called multiple times safely."""
        # Call multiple times - should not raise any errors
        clear_auth_caches()
        clear_auth_caches()
        clear_auth_caches()

        # Verify caches are empty
        cache_info = _create_google_model_cached.cache_info()
        assert cache_info.currsize == 0
        assert len(_managed_http_clients) == 0
