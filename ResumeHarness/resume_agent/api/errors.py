"""API 错误类型。"""

from __future__ import annotations


class ResumeAgentApiError(RuntimeError):
    """Base class for upstream API failures."""


class AuthenticationFailure(ResumeAgentApiError):
    """Raised when the upstream service rejects the provided credentials."""


class RateLimitFailure(ResumeAgentApiError):
    """Raised when the upstream service rejects the request due to rate limits."""


class RequestFailure(ResumeAgentApiError):
    """Raised for generic request or transport failures."""
