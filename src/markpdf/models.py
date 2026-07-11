from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JsonResult:
    """Parsed body of a conversion response when ``response_format="json"``."""

    filename: str
    input_format: str
    markdown: str
    engine: str
    size_bytes: int
    markdown_bytes: int
    token_saved_estimate: int | None = None
    timings: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonResult":
        return cls(
            filename=data.get("filename", ""),
            input_format=data.get("input_format", ""),
            markdown=data.get("markdown", ""),
            engine=data.get("engine", ""),
            size_bytes=data.get("size_bytes", 0),
            markdown_bytes=data.get("markdown_bytes", 0),
            token_saved_estimate=data.get("token_saved_estimate"),
            timings=data.get("timings", {}),
            raw=data,
        )


@dataclass
class Job:
    """State of a conversion that was auto-queued (HTTP 202)."""

    job_id: str
    status: str
    body: str | dict[str, Any] | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            job_id=data.get("job_id", ""),
            status=data.get("status", ""),
            body=data.get("body"),
            error=data.get("error"),
            raw=data,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed")
