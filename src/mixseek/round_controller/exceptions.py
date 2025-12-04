"""Round controller component custom exceptions."""


class JudgmentAPIError(Exception):
    """Base exception for LLM API errors during judgment.

    Raised when LLM API calls fail after all retries have been attempted.
    Contains information about provider, retry attempts.

    Attributes:
        message: Error message describing the failure
        provider: LLM provider that failed (e.g., "anthropic", "openai", "google-gla")
        retry_count: Number of retry attempts made

    Example:
        ```python
        raise JudgmentAPIError(
            "Failed to judge improvement prospects after 3 retries: API key invalid",
            provider="google-gla",
            retry_count=3
        )
        ```
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        """Initialize JudgmentAPIError.

        Args:
            message: Error message describing the failure
            provider: LLM provider that failed (e.g., "anthropic", "openai", "google-gla")
            retry_count: Number of retry attempts made
        """
        super().__init__(message)
        self.provider = provider
        self.retry_count = retry_count

    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [super().__str__()]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.retry_count is not None:
            parts.append(f"Retries: {self.retry_count}")
        return " | ".join(parts)
