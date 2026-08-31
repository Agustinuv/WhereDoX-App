"""Domain exceptions, mapped to HTTP by a single handler in app.main.

Services raise these and never import fastapi: that is what keeps the service layer
reusable behind a Telegram bot or a CLI instead of only behind HTTP.
"""


class DomainError(Exception):
    """Base for every expected failure. status_code is what the handler returns."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    """The request is well formed but the current state does not allow it."""

    status_code = 409


class ValidationError(DomainError):
    status_code = 422
