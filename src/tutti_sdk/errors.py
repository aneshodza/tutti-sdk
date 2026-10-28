import json
from typing import Any


class TuttiError(Exception):
    pass


class TuttiHttpError(TuttiError):
    """Non-2xx HTTP response."""

    def __init__(self, status: int, status_text: str, body: str) -> None:
        self.status = status
        self.status_text = status_text
        self.body = body
        super().__init__(f"HTTP {status} {status_text}: {body[:500]}")


class TuttiGraphQLError(TuttiError):
    """GraphQL response carried an ``errors`` array."""

    def __init__(self, operation: str, errors: list[Any]) -> None:
        self.operation = operation
        self.errors = errors
        super().__init__(f"GraphQL operation {operation} failed: {json.dumps(errors)[:500]}")


class TuttiNetworkError(TuttiError):
    """The underlying transport raised (DNS, connection, timeout, …)."""

    def __init__(self, cause: BaseException) -> None:
        self.cause = cause
        super().__init__(f"Network request failed: {cause}")


class TuttiValidationError(TuttiError):
    """Invalid arguments supplied to the search builder."""


class TuttiAuthError(TuttiError):
    """A step in the Auth0/login flow failed (bad credentials, captcha, redirect)."""
