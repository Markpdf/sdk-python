from __future__ import annotations

from typing import Any


class MarkpdfError(Exception):
    """Base class for every error raised by the markpdf SDK."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class BadRequestError(MarkpdfError):
    """HTTP 400 — malformed body or URL."""


class AuthenticationError(MarkpdfError):
    """HTTP 401 — missing or invalid API key."""


class ForbiddenError(MarkpdfError):
    """HTTP 403 — unauthorized access or disallowed URL host."""


class PayloadTooLargeError(MarkpdfError):
    """HTTP 413 — document too large, too many pages, or ZIP out of bounds."""


class UnsupportedFormatError(MarkpdfError):
    """HTTP 415 — unsupported input format or Content-Encoding."""


class UnprocessableEntityError(MarkpdfError):
    """HTTP 422 — missing required parameters."""


class RateLimitError(MarkpdfError):
    """HTTP 429 — too many requests. Retry with backoff."""


class ConversionError(MarkpdfError):
    """HTTP 500 — conversion failed. Try another `mode` or check the document."""


class JobFailedError(MarkpdfError):
    """A queued job (202 -> /jobs/{id}) finished with status=failed."""


class JobExpiredError(MarkpdfError):
    """A queued job could not be found (expired after ~1h or invalid id)."""


_STATUS_TO_ERROR: dict[int, type[MarkpdfError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    413: PayloadTooLargeError,
    415: UnsupportedFormatError,
    422: UnprocessableEntityError,
    429: RateLimitError,
    500: ConversionError,
}


def error_for_status(status_code: int, detail: Any) -> MarkpdfError:
    error_cls = _STATUS_TO_ERROR.get(status_code, MarkpdfError)
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    return error_cls(message or f"HTTP {status_code}", status_code=status_code, detail=detail)
