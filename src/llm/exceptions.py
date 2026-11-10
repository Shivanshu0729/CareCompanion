class LLMError(Exception):
    """Raised when an LLM request cannot be completed."""


class LLMConfigurationError(LLMError):
    """Raised when the LLM provider is not configured."""


class LLMAuthenticationError(LLMError):
    """Raised when the API key is missing or rejected."""


class LLMRateLimitError(LLMError):
    """Raised when the provider rate-limits the request."""


class LLMTimeoutError(LLMError):
    """Raised when the provider request times out."""


class LLMConnectionError(LLMError):
    """Raised when the provider cannot be reached."""


class LLMModelUnavailableError(LLMError):
    """Raised when the configured model is unavailable."""


class LLMResponseError(LLMError):
    """Raised when the provider returns an unusable response."""
